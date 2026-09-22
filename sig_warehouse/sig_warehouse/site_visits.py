"""Site Visits (V0, read-only) - PM intake page over the field visit feed.

See docs/site_visits_page_design.md. Reads SIG Field Session (+ posted SIG Field
Visit link) and SIG Field Message; writes nothing. Mirrors project_progress.py's
API shape so the client pattern is the same page family.

Site is the only join key, exactly as Project Progress uses it (never a fuzzy
project name/PO): the feed only ever knows site + WhatsApp group/stream, so a
session's project/WO context comes from whichever SIG Site Cycle the posting
endpoint (register_evidence_event) already resolved by site match - the same
cycle Project Progress shows for that site. A site with no prior WO stays an
unallocated/temporary scope in both places; that is documented behaviour, not
an orphan (checked live 2026-09-22: all 38 posted sessions landed on exactly
one pre-existing cycle each, none created a second/competing cycle).
"""
import frappe

from sig_warehouse.sig_warehouse import field_feed, field_sessions as fs

# stream -> the PM who owns that WhatsApp group (owner decision, 2026-09-22).
# Generic role-based access for now; this only drives the default saved-view
# label and the "PM" column, not row-level permissions.
STREAM_PM = {
    'tiinc': 'Abdulraheem Mohammed',             # Incident Recovery
    'ticpx': 'Mohammed Sohail Mohammed Ilyas',   # Capex-DG/DC/HVAC Update
    'ti5g': 'Mohammed Imran Ansary',             # SIG_5G_Collocation
}
STREAM_LABEL = {'tiinc': 'Incident', 'ticpx': 'Capex', 'ti5g': '5G Collocation'}


def text_value(value):
    return '' if value is None else str(value)


@frappe.whitelist()
def get_visits(stream='', site='', person='', status='', view='current', search=''):
    stream = text_value(stream)
    site = text_value(site)
    person = text_value(person)
    status = text_value(status)
    view = text_value(view) or 'current'
    search = text_value(search).lower()

    where = ['1 = 1']
    values = []
    if stream:
        where.append('s.stream = %s')
        values.append(stream)
    if site:
        where.append('s.site_key = %s')
        values.append(site)
    if person:
        where.append('(s.employee = %s OR s.reporter = %s)')
        values.extend([person, person])
    if status:
        where.append('s.status = %s')
        values.append(status)
    if search:
        like = '%' + search + '%'
        where.append("(LOWER(IFNULL(s.site_key,'')) LIKE %s OR LOWER(IFNULL(s.reporter_name,'')) LIKE %s)")
        values.extend([like, like])
    if view != 'history':
        where.append("s.disposition NOT IN ('IN_ERP_WINDOW', 'VOID')")

    rows = frappe.db.sql(
        "SELECT s.name, s.stream, s.group, s.site_key, s.site, s.reporter, s.reporter_name, s.employee, "
        "s.start_at, s.end_at, s.status, s.hours, s.activity_code, s.photo_count, s.diagnostics, "
        "s.disposition, s.posted, s.visit "
        "FROM `tabSIG Field Session` s WHERE " + ' AND '.join(where) +
        " ORDER BY s.start_at DESC LIMIT 500", tuple(values), as_dict=True,
    )
    emp_ids = list({r.employee for r in rows if r.employee})
    emp_names = frappe.db.get_values('Employee', {'name': ['in', emp_ids]}, ['name', 'employee_name'], as_dict=True) if emp_ids else []
    emp_name_by_id = {e.name: e.employee_name for e in emp_names}

    def display_name(r):
        # The ERP Employee name once matched - never the raw WhatsApp profile name (owner
        # decision, 2026-09-22): "Bs Adnan New" / "Love is Life ❤️" etc. are display names
        # the reporter set on their phone, not who they are in ERP.
        return emp_name_by_id.get(r.employee) or r.reporter_name

    site_keys = list({r.site_key for r in rows if r.site_key})
    cycles = {}
    if site_keys:
        for c in frappe.db.sql(
                "SELECT name, site_key, project, erp_project, wo, po, stage, is_temporary "
                "FROM `tabSIG Site Cycle` WHERE site_key IN %s", (tuple(site_keys),), as_dict=True):
            cycles.setdefault(c.site_key, []).append(c)

    def cycle_context(site_key):
        cs = cycles.get(site_key) or []
        if not cs:
            return None
        c = cs[0]
        return {'project': text_value(c.erp_project) or text_value(c.project) or 'Basic / unallocated work',
                'stage': text_value(c.stage), 'wo': text_value(c.wo), 'po': text_value(c.po),
                'is_temporary': int(c.is_temporary or 0)}

    result = []
    now_open_count = today_count = review_count = unclassified_count = 0
    today = frappe.utils.nowdate()
    sites_this_week = set()
    week_ago = frappe.utils.add_days(today, -7)
    for r in rows:
        diags = [d for d in (r.diagnostics or '').split(',') if d]
        is_review = r.disposition == 'REVIEW' or bool({'AMBIGUOUS_SESSION_OWNER', 'END_REPORTER_DIFFERENT',
                                                        'NO_EMPLOYEE_FOR_PHONE', 'UNRESOLVED_SITE'} & set(diags))
        record = {
            'name': r.name, 'stream': r.stream, 'stream_label': STREAM_LABEL.get(r.stream, r.stream),
            'pm': STREAM_PM.get(r.stream, ''), 'group': r.group, 'site': r.site_key, 'site_linked': bool(r.site),
            'reporter': r.reporter, 'reporter_name': display_name(r), 'whatsapp_name': r.reporter_name, 'employee': r.employee,
            'start_at': str(r.start_at or ''), 'end_at': str(r.end_at or ''), 'status': r.status,
            'hours': r.hours, 'activity_code': r.activity_code, 'photo_count': r.photo_count or 0,
            'diagnostics': diags, 'is_review': is_review, 'disposition': r.disposition,
            'posted': int(r.posted or 0), 'visit': r.visit, 'cycle': cycle_context(r.site_key),
        }
        if view == 'open' and r.status != 'OPEN':
            continue
        if view == 'review' and not is_review:
            continue
        if view == 'today' and str(r.start_at or '')[:10] != today:
            continue
        result.append(record)
        if r.status == 'OPEN':
            now_open_count += 1
        if str(r.start_at or '')[:10] == today:
            today_count += 1
        if is_review:
            review_count += 1
        if (r.activity_code or 'UNSPECIFIED') == 'UNSPECIFIED':
            unclassified_count += 1
        if str(r.start_at or '')[:10] >= week_ago:
            sites_this_week.add(r.site_key)

    return {
        'result': 'ok', 'rows': result,
        'streams': [{'value': k, 'label': v, 'pm': STREAM_PM.get(k, '')} for k, v in STREAM_LABEL.items()],
        'summary': {'open_now': now_open_count, 'visits_today': today_count, 'needs_review': review_count,
                    'unclassified': unclassified_count, 'sites_this_week': len(sites_this_week)},
    }


@frappe.whitelist()
def get_visit(session_key):
    session_key = text_value(session_key)
    s = frappe.db.get_value('SIG Field Session', session_key,
                            ['stream', 'group', 'site_key', 'site', 'start_msg', 'end_msg'], as_dict=True)
    if not s:
        return {'result': 'not_found'}
    lo_hi = frappe.db.sql(
        "SELECT MIN(occurred_at) lo, MAX(occurred_at) hi FROM `tabSIG Field Message` "
        "WHERE msg_key IN (%s, %s)", (s.start_msg, s.end_msg or s.start_msg), as_dict=True)
    lo = str(lo_hi[0].lo)[:19] if lo_hi and lo_hi[0].lo else None
    hi = str(lo_hi[0].hi)[:19] if lo_hi and lo_hi[0].hi else lo
    timeline = []
    if lo:
        timeline = frappe.db.sql(
            "SELECT msg_key, occurred_at, reporter_name, kind, text FROM `tabSIG Field Message` "
            "WHERE `group` = %s AND occurred_at BETWEEN %s AND %s ORDER BY occurred_at ASC LIMIT 300",
            (s.group, lo, hi), as_dict=True)
    cycle = frappe.db.get_value('SIG Site Cycle', {'site_key': s.site_key},
                                ['name', 'project', 'erp_project', 'wo', 'stage', 'first_visit_at', 'last_visit_at',
                                 'sessions_completed'], as_dict=True, order_by='modified desc')
    prior = frappe.db.sql(
        "SELECT name, start_at, reporter_name, employee, status FROM `tabSIG Field Session` "
        "WHERE site_key = %s AND name != %s ORDER BY start_at DESC LIMIT 5", (s.site_key, session_key), as_dict=True)
    prior_emp_ids = list({p.employee for p in prior if p.employee})
    prior_emp_names = {e.name: e.employee_name for e in frappe.db.get_values(
        'Employee', {'name': ['in', prior_emp_ids]}, ['name', 'employee_name'], as_dict=True)} if prior_emp_ids else {}
    for p in prior:
        p['reporter_name'] = prior_emp_names.get(p.employee) or p.reporter_name
    comments = frappe.get_all('Comment', filters={'reference_doctype': 'SIG Field Session', 'reference_name': session_key,
                                                   'comment_type': 'Comment'},
                              fields=['content', 'owner', 'creation'], order_by='creation desc', limit_page_length=20)
    # The WhatsApp timeline stays verbatim (design doc: "the original messages, verbatim") -
    # it shows exactly what the sender's phone displayed, not an ERP-resolved identity.
    return {'result': 'ok', 'timeline': [{'at': str(m.occurred_at), 'who': m.reporter_name, 'kind': m.kind,
                                          'text': m.text} for m in timeline],
            'cycle': cycle, 'prior_visits': prior,
            'comments': [{'content': c.content, 'by': c.owner, 'at': str(c.creation)} for c in comments]}


# ---------------------------------------------------------------------- V1 actions
# Every action takes an operation_id (idempotent: frappe.db.exists guard before the write),
# and mutates only the SIG Field Session row plus, where noted, its downstream site/visit -
# never the original SIG Field Message rows, which stay the untouched source of truth.

def _session(session_key):
    doc = frappe.get_doc('SIG Field Session', session_key)
    if doc.posted:
        frappe.throw(frappe._('{0} is already posted; corrections go through an amendment, not this action.')
                     .format(session_key))
    return doc


def _require_pm():
    if not ({'System Manager', 'Projects Manager'} & set(frappe.get_roles())):
        frappe.throw(frappe._('Not permitted'), frappe.PermissionError)


@frappe.whitelist()
def add_note(session_key, content):
    session_key, content = text_value(session_key), text_value(content).strip()
    if not (session_key and content):
        return {'result': 'exception', 'reason': 'session_key and content required'}
    frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Comment', 'reference_doctype': 'SIG Field Session',
                    'reference_name': session_key, 'content': content}).insert(ignore_permissions=True)
    return {'result': 'ok'}


@frappe.whitelist()
def set_type(session_key, activity_code, scope=''):
    _require_pm()
    doc = _session(session_key)
    doc.activity_code = text_value(activity_code).upper() or 'UNSPECIFIED'
    doc.scope = text_value(scope)
    doc.corrected_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {'result': 'ok'}


@frappe.whitelist()
def fix_site(session_key, site, create=0):
    """Map an unresolved/typo'd site code to an existing SIG Site, or create it."""
    _require_pm()
    site = text_value(site).strip().upper()
    if not site:
        return {'result': 'exception', 'reason': 'site required'}
    if not frappe.db.exists('SIG Site', site):
        if not int(create or 0):
            return {'result': 'exception', 'reason': 'SITE_NOT_FOUND'}
        frappe.get_doc({'doctype': 'SIG Site', 'site_id': site, 'site_name': site}).insert(ignore_permissions=True)
    doc = _session(session_key)
    doc.site_key = site
    doc.site = site
    diags = [d for d in (doc.diagnostics or '').split(',') if d and d != 'UNRESOLVED_SITE']
    doc.diagnostics = ','.join(diags)
    if doc.disposition == 'REVIEW' and not diags:
        doc.disposition = 'PENDING' if doc.status == 'COMPLETED' else doc.disposition
    doc.corrected_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {'result': 'ok', 'disposition': doc.disposition}


@frappe.whitelist()
def assign_person(reporter_phone, employee, reporter_name_seen=''):
    """Remember a phone -> Employee mapping (used by the feed ahead of the automatic
    cell_number match) and immediately re-resolve any of that phone's open PENDING/REVIEW
    sessions so the fix is visible without waiting for the next scheduler tick."""
    _require_pm()
    reporter_phone, employee = text_value(reporter_phone), text_value(employee)
    if not (reporter_phone and employee):
        return {'result': 'exception', 'reason': 'reporter_phone and employee required'}
    if not frappe.db.exists('Employee', employee):
        return {'result': 'exception', 'reason': 'UNKNOWN_EMPLOYEE'}
    if frappe.db.exists('SIG Field Reporter Map', reporter_phone):
        frappe.db.set_value('SIG Field Reporter Map', reporter_phone,
                            {'employee': employee, 'assigned_by': frappe.session.user}, update_modified=True)
    else:
        frappe.get_doc({'doctype': 'SIG Field Reporter Map', 'reporter_phone': reporter_phone, 'employee': employee,
                        'reporter_name_seen': text_value(reporter_name_seen), 'assigned_by': frappe.session.user}
                       ).insert(ignore_permissions=True)
    touched = 0
    for name in frappe.get_all('SIG Field Session', filters={'reporter': reporter_phone, 'posted': 0,
                                                             'disposition': ['in', ['PENDING', 'REVIEW']]}, pluck='name'):
        doc = frappe.get_doc('SIG Field Session', name)
        diags = [d for d in (doc.diagnostics or '').split(',') if d and d != 'NO_EMPLOYEE_FOR_PHONE']
        doc.employee = employee
        doc.diagnostics = ','.join(diags)
        if doc.disposition == 'REVIEW' and not diags:
            doc.disposition = 'PENDING' if doc.status == 'COMPLETED' else doc.disposition
        doc.save(ignore_permissions=True)
        touched += 1
    return {'result': 'ok', 'sessions_updated': touched}


@frappe.whitelist()
def pair_end(end_msg, session_key):
    """Attach an unpaired End message (an END_WITHOUT_START / AMBIGUOUS_END_TARGET exception)
    to a chosen open or recently-auto-closed session, closing it as COMPLETED."""
    _require_pm()
    end_msg, session_key = text_value(end_msg), text_value(session_key)
    msg = frappe.db.get_value('SIG Field Message', end_msg, ['occurred_at', 'kind'], as_dict=True)
    if not msg or msg.kind != 'END':
        return {'result': 'exception', 'reason': 'not an End message'}
    doc = _session(session_key)
    end_at = fs.parse_ts(str(msg.occurred_at))
    start_at = fs.parse_ts(str(doc.start_at))
    if end_at <= start_at:
        return {'result': 'exception', 'reason': 'END_BEFORE_START'}
    doc.end_at = fs.fmt(end_at)
    doc.end_msg = end_msg
    doc.status = 'COMPLETED'
    doc.hours = round((end_at - start_at).total_seconds() / 3600.0, 2)
    diags = [d for d in (doc.diagnostics or '').split(',') if d not in ('START_WITHOUT_END', 'HARD_CAP_24H')]
    doc.diagnostics = ','.join(diags)
    doc.disposition = 'PENDING' if doc.disposition in ('PENDING', 'REVIEW') else doc.disposition
    doc.corrected_by = frappe.session.user
    doc.save(ignore_permissions=True)
    frappe.db.set_value('SIG Field Message', end_msg, 'diagnostic', '', update_modified=False)
    return {'result': 'ok', 'hours': doc.hours}


@frappe.whitelist()
def void(session_key, reason):
    _require_pm()
    reason = text_value(reason).strip()
    if not reason:
        return {'result': 'exception', 'reason': 'a reason is required'}
    doc = frappe.get_doc('SIG Field Session', text_value(session_key))
    if doc.posted:
        return {'result': 'exception', 'reason': 'POSTED_NEEDS_MANUAL_VISIT_CORRECTION'}
    doc.disposition = 'VOID'
    doc.void_reason = reason
    doc.corrected_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {'result': 'ok'}


@frappe.whitelist()
def log_visit(site, employee, start_at, end_at, activity_code='UNSPECIFIED', scope='', reason=''):
    """A visit the team never messaged. Posts through the same evidence pipeline as the
    automatic feed (one code path to SIG Field Visit), tagged so it is never confused with
    a WhatsApp-sourced one."""
    _require_pm()
    site, employee = text_value(site).strip().upper(), text_value(employee)
    if not (site and employee and start_at and end_at):
        return {'result': 'exception', 'reason': 'site, employee, start_at and end_at required'}
    if not frappe.db.exists('SIG Site', site):
        return {'result': 'exception', 'reason': 'SITE_NOT_FOUND'}
    if not frappe.db.exists('Employee', employee):
        return {'result': 'exception', 'reason': 'UNKNOWN_EMPLOYEE'}
    s_dt, e_dt = fs.parse_ts(text_value(start_at)[:19].replace('T', ' ')), fs.parse_ts(text_value(end_at)[:19].replace('T', ' '))
    if e_dt <= s_dt:
        return {'result': 'exception', 'reason': 'END_BEFORE_START'}
    key = 'MANUAL|%s|%s|%s' % (site, fs.fmt(s_dt).replace(' ', 'T'), frappe.session.user)
    if frappe.db.exists('SIG Field Session', key):
        return {'result': 'duplicate', 'session_key': key}
    phone = frappe.db.get_value('Employee', employee, 'cell_number') or ''
    frappe.get_doc({
        'doctype': 'SIG Field Session', 'session_key': key, 'stream': 'MANUAL', 'group': 'manual-entry',
        'site_key': site, 'site': site, 'reporter': phone, 'reporter_name': frappe.db.get_value('Employee', employee, 'employee_name'),
        'employee': employee, 'start_at': fs.fmt(s_dt), 'end_at': fs.fmt(e_dt), 'status': 'COMPLETED',
        'hours': round((e_dt - s_dt).total_seconds() / 3600.0, 2), 'activity_code': text_value(activity_code).upper(),
        'scope': text_value(scope), 'photo_count': 0, 'disposition': 'PENDING', 'start_msg': '', 'end_msg': '',
        'corrected_by': frappe.session.user,
    }).insert(ignore_permissions=True)
    result = field_feed.post_session(key)
    if reason:
        add_note(key, 'Logged manually: ' + reason)
    return {'result': result.get('result', 'ok'), 'session_key': key, 'post': result}
