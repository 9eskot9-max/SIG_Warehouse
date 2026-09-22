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
        where.append("s.disposition != 'IN_ERP_WINDOW'")

    rows = frappe.db.sql(
        "SELECT s.name, s.stream, s.group, s.site_key, s.site, s.reporter, s.reporter_name, s.employee, "
        "s.start_at, s.end_at, s.status, s.hours, s.activity_code, s.photo_count, s.diagnostics, "
        "s.disposition, s.posted, s.visit "
        "FROM `tabSIG Field Session` s WHERE " + ' AND '.join(where) +
        " ORDER BY s.start_at DESC LIMIT 500", tuple(values), as_dict=True,
    )
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
            'reporter': r.reporter, 'reporter_name': r.reporter_name, 'employee': r.employee,
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
        "SELECT name, start_at, reporter_name, status FROM `tabSIG Field Session` "
        "WHERE site_key = %s AND name != %s ORDER BY start_at DESC LIMIT 5", (s.site_key, session_key), as_dict=True)
    comments = frappe.get_all('Comment', filters={'reference_doctype': 'SIG Field Session', 'reference_name': session_key,
                                                   'comment_type': 'Comment'},
                              fields=['content', 'owner', 'creation'], order_by='creation desc', limit_page_length=20)
    return {'result': 'ok', 'timeline': [{'at': str(m.occurred_at), 'who': m.reporter_name, 'kind': m.kind,
                                          'text': m.text} for m in timeline],
            'cycle': cycle, 'prior_visits': prior,
            'comments': [{'content': c.content, 'by': c.owner, 'at': str(c.creation)} for c in comments]}
