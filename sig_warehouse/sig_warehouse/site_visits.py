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
from sig_warehouse.sig_warehouse.project_family import normalize_family, resolve_project_family

from sig_warehouse.sig_warehouse import field_feed, field_sessions as fs

# stream -> the PM who owns that WhatsApp group (owner decision, 2026-09-22).
# Generic role-based access for now; this only drives the default saved-view
# label and the "PM" column, not row-level permissions.
STREAM_PM = {
    'tiinc': 'Abdulraheem Mohammed',             # Incident Recovery
    'ticpx': 'Mohammed Sohail Mohammed Ilyas',   # Capex-DG/DC/HVAC Update
    'ticpx2': 'Mohammed Sohail Mohammed Ilyas',  # Live load transfer/SIG (Capex2)
    'ti5g': 'Mohammed Imran Ansary',             # SIG_5G_Collocation
}
STREAM_LABEL = {'ti5g': 'CO1', 'tiinc': 'INC1', 'ticpx': 'CPX1', 'ticpx2': 'CPX2'}
SITE_VISIT_ROLES = {"System Manager", "Operations Manager", "Operations User", "Projects Manager", "Projects User", "SIG Field Ops"}


def text_value(value):
    return '' if value is None else str(value)


@frappe.whitelist()
def get_movement_map(period='week', anchor=None):
    """Return dated visit points and the Planner roster for a week or month."""
    from datetime import timedelta
    from sig_warehouse.sig_warehouse.field_planner_api import _team_setup

    if not set(frappe.get_roles()).intersection(SITE_VISIT_ROLES):
        frappe.throw('You need an Operations role to view field visits.', frappe.PermissionError)
    if period not in ('week', 'month'):
        frappe.throw('Choose week or month.')
    day = frappe.utils.getdate(anchor or frappe.utils.nowdate())
    start = day - timedelta(days=day.weekday()) if period == 'week' else day.replace(day=1)
    end = start + timedelta(days=7) if period == 'week' else frappe.utils.add_months(start, 1)
    rows = frappe.db.sql(
        "SELECT name, site_key, employee, start_at, status, posted FROM `tabSIG Field Session` "
        "WHERE start_at >= %s AND start_at < %s AND disposition NOT IN ('IN_ERP_WINDOW','VOID') "
        "ORDER BY start_at ASC, name ASC LIMIT 10001", (start, end), as_dict=True)
    truncated = len(rows) > 10000
    rows = rows[:10000]
    codes = list({r.site_key for r in rows if r.site_key})
    employees = list({r.employee for r in rows if r.employee})
    sites = frappe.get_list('SIG Site', filters={'name': ['in', codes]}, fields=['name', 'site_latitude', 'site_longitude'], limit_page_length=0) if codes else []
    coordinates = {s.name: (s.site_latitude, s.site_longitude) for s in sites if s.site_latitude and s.site_longitude}
    names = frappe.db.get_values('Employee', {'name': ['in', employees]}, ['name', 'employee_name'], as_dict=True) if employees else []
    names = {e.name: e.employee_name for e in names}
    roster = _team_setup()
    leader_ids = list({t['leader'] for t in roster if t.get('leader')})
    leader_rows = frappe.db.get_values('Employee', {'name': ['in', leader_ids]}, ['name', 'employee_name'], as_dict=True) if leader_ids else []
    leader_names = {e.name: e.employee_name for e in leader_rows}
    teams = [{'id': str(t['team_id']), 'leader': t['leader'], 'label': leader_names.get(t['leader']) or t['leader'],
              'periods': t.get('leader_periods') or [{'employee': t['leader'], 'from': '', 'to': ''}]} for t in roster]
    points = []
    for r in rows:
        date = str(r.start_at)[:10]
        matches = [t for t in teams if any(p.get('employee') == r.employee and (not p.get('from') or p['from'] <= date)
                   and (not p.get('to') or date <= p['to']) for p in t['periods'])]
        xy = coordinates.get(r.site_key)
        points.append({'name': r.name, 'site': r.site_key, 'employee': r.employee, 'person': names.get(r.employee) or r.employee or '',
                       'team': matches[0]['id'] if len(matches) == 1 else '', 'at': str(r.start_at), 'status': r.status,
                       'lat': float(xy[0]) if xy else None, 'lon': float(xy[1]) if xy else None})
    return {'start': str(start), 'end': str(end - timedelta(days=1)), 'teams': teams, 'visits': points, 'truncated': truncated}


@frappe.whitelist()
def get_visits(stream='', site='', person='', status='', view='current', search='', date_from='', date_to=''):
    user = frappe.session.user
    roles = set(frappe.get_roles(user)) if user != "Guest" else set()
    if not roles.intersection(SITE_VISIT_ROLES):
        frappe.throw("You need an Operations role to view field visits.", frappe.PermissionError)
    stream = text_value(stream)
    site = text_value(site)
    person = text_value(person)
    status = text_value(status)
    view = text_value(view) or 'current'
    search = text_value(search).strip().lower()

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
    if date_from:
        where.append('s.start_at >= %s')
        values.append(frappe.utils.getdate(date_from))
    if date_to:
        where.append('s.start_at < %s')
        values.append(frappe.utils.add_days(frappe.utils.getdate(date_to), 1))
    if search:
        like = '%' + search + '%'
        where.append("(LOWER(IFNULL(s.site_key,'')) LIKE %s OR EXISTS "
                     "(SELECT 1 FROM `tabEmployee` e WHERE e.name = s.employee "
                     "AND LOWER(IFNULL(e.employee_name,'')) LIKE %s))")
        values.extend([like, like])
    if view != 'history':
        where.append("s.disposition NOT IN ('IN_ERP_WINDOW', 'VOID')")

    rows = frappe.db.sql(
        "SELECT s.name, s.stream, s.site_key, s.site, s.reporter, s.reporter_name, s.employee, "
        "s.start_at, s.end_at, s.status, s.hours, s.activity_code, s.photo_count, s.diagnostics, "
        "s.disposition, s.posted, s.visit "
        "FROM `tabSIG Field Session` s WHERE " + ' AND '.join(where) +
        " ORDER BY s.start_at DESC LIMIT 501", tuple(values), as_dict=True,
    )
    truncated = len(rows) > 500
    rows = rows[:500]
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
        # A site may have several scopes. Never imply an arbitrary one is the
        # session's cycle; the detail view uses the actual posted visit link.
        if len(cs) != 1:
            return None
        c = cs[0]
        return {'project': text_value(c.erp_project) or text_value(c.project) or 'Basic / unallocated work',
                'stage': text_value(c.stage), 'wo': text_value(c.wo), 'po': text_value(c.po),
                'is_temporary': int(c.is_temporary or 0)}

    result = []
    now_open_count = today_count = review_count = unclassified_count = 0
    today = frappe.utils.nowdate()
    sites_this_week = set()
    sites_in_period = set()
    week_ago = frappe.utils.add_days(today, -7)
    for r in rows:
        diags = [d for d in (r.diagnostics or '').split(',') if d]
        is_review = r.disposition == 'REVIEW' or bool({'AMBIGUOUS_SESSION_OWNER', 'END_REPORTER_DIFFERENT',
                                                        'NO_EMPLOYEE_FOR_PHONE', 'UNRESOLVED_SITE',
                                                        'CYCLE_ATTRIBUTION_EXCEPTION', 'UNALLOCATED'} & set(diags))
        record = {
            'name': r.name, 'stream': r.stream, 'stream_label': STREAM_LABEL.get(r.stream, r.stream),
            'pm': STREAM_PM.get(r.stream, ''), 'site': r.site_key, 'site_linked': bool(r.site),
            'reporter': r.reporter, 'reporter_name': display_name(r), 'whatsapp_name': r.reporter_name, 'employee': r.employee,
            'start_at': str(r.start_at or ''), 'end_at': str(r.end_at or ''), 'status': r.status,
            'hours': r.hours, 'activity_code': r.activity_code, 'photo_count': r.photo_count or 0,
            'diagnostics': diags, 'is_review': is_review, 'disposition': r.disposition,
            'posted': int(r.posted or 0), 'visit': r.visit, 'cycle': cycle_context(r.site_key),
        }
        # Summary tile counts reflect every row that passed the base/search/stream/etc.
        # filters above, independent of which view is currently selected - otherwise
        # switching to a view with few/no matches (e.g. "Open now" when nothing is
        # currently open) zeroes out the OTHER tiles too, since they'd only be counted
        # from the same already-view-filtered subset (found live 2026-09-22).
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
        if r.site_key:
            sites_in_period.add(r.site_key)

        if view == 'open' and r.status != 'OPEN':
            continue
        if view == 'review' and not is_review:
            continue
        if view == 'today' and str(r.start_at or '')[:10] != today:
            continue
        if view == 'unclassified' and (r.activity_code or 'UNSPECIFIED') != 'UNSPECIFIED':
            continue
        if view == 'thisweek' and str(r.start_at or '')[:10] < week_ago:
            continue
        result.append(record)

    return {
        'result': 'ok', 'rows': result, 'truncated': truncated,
        'streams': [{'value': k, 'label': v, 'pm': STREAM_PM.get(k, '')} for k, v in STREAM_LABEL.items()],
        'summary': {'open_now': now_open_count, 'visits_today': today_count, 'needs_review': review_count,
                    'unclassified': unclassified_count, 'sites_this_week': len(sites_this_week),
                    'sites_in_period': len(sites_in_period)},
    }


@frappe.whitelist()
def get_my_visit_schedule():
    """Return only the signed-in user's own visit sessions for the employee schedule page."""
    allowed_roles = {'Employee', 'Employee Self Service', 'SIG PM', 'SIG Coordinator',
                     'Projects Manager', 'System Manager'}
    if not allowed_roles.intersection(frappe.get_roles()):
        frappe.throw(frappe._('Not permitted'), frappe.PermissionError)
    employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user, 'status': 'Active'}, 'name')
    if not employee:
        return {'result': 'ok', 'employee': None, 'rows': []}
    rows = frappe.db.sql(
        "SELECT name, site_key, start_at, end_at, status, hours, activity_code, photo_count "
        "FROM `tabSIG Field Session` WHERE employee = %s AND disposition NOT IN ('IN_ERP_WINDOW', 'VOID') "
        "ORDER BY start_at DESC LIMIT 500", (employee,), as_dict=True)
    return {
        'result': 'ok', 'employee': employee,
        'rows': [{'name': r.name, 'site': r.site_key, 'start_at': str(r.start_at or ''),
                  'end_at': str(r.end_at or ''), 'status': r.status, 'hours': r.hours,
                  'activity_code': r.activity_code or 'UNSPECIFIED', 'photo_count': r.photo_count or 0}
                 for r in rows],
    }


@frappe.whitelist()
def get_visit(session_key):
    session_key = text_value(session_key)
    s = frappe.db.get_value('SIG Field Session', session_key,
                            ['stream', 'group', 'site_key', 'site', 'start_msg', 'end_msg', 'visit', 'start_at'], as_dict=True)
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
    cycle_name = frappe.db.get_value('SIG Field Visit', s.visit, 'cycle') if s.visit else None
    cycle = frappe.db.get_value('SIG Site Cycle', cycle_name,
                                ['name', 'project', 'erp_project', 'wo', 'stage', 'first_visit_at', 'last_visit_at',
                                 'sessions_completed'], as_dict=True) if cycle_name else None
    cycle_candidates = []
    if ({'System Manager', 'Projects Manager'} & set(frappe.get_roles()) and
            frappe.has_permission('SIG Site Cycle', 'read')):
        cycle_candidates = frappe.get_list('SIG Site Cycle',
            filters={'site_key': s.site_key, 'terminal': 0},
            fields=['name', 'project', 'erp_project', 'po', 'wo', 'stage'],
            order_by='creation asc, name asc', limit_page_length=100)
    prior = frappe.db.sql(
        "SELECT name, start_at, reporter_name, employee, status FROM `tabSIG Field Session` "
        "WHERE site_key = %s AND name != %s ORDER BY start_at DESC LIMIT 5", (s.site_key, session_key), as_dict=True)
    prior_emp_ids = list({p.employee for p in prior if p.employee})
    prior_emp_names = {e.name: e.employee_name for e in frappe.db.get_values(
        'Employee', {'name': ['in', prior_emp_ids]}, ['name', 'employee_name'], as_dict=True)} if prior_emp_ids else {}
    for p in prior:
        p['reporter_name'] = prior_emp_names.get(p.employee) or p.reporter_name
    previous_count = frappe.db.count('SIG Field Visit', filters={'site_key': s.site_key, 'start_at': ['<', s.start_at]}) if s.site_key and s.start_at else None
    comments = frappe.get_all('Comment', filters={'reference_doctype': 'SIG Field Session', 'reference_name': session_key,
                                                   'comment_type': 'Comment'},
                              fields=['content', 'owner', 'creation'], order_by='creation desc', limit_page_length=20)
    # The WhatsApp timeline stays verbatim (design doc: "the original messages, verbatim") -
    # it shows exactly what the sender's phone displayed, not an ERP-resolved identity.
    return {'result': 'ok', 'timeline': [{'at': str(m.occurred_at), 'who': m.reporter_name, 'kind': m.kind,
                                          'text': m.text} for m in timeline],
            'cycle': cycle, 'cycle_candidates': cycle_candidates, 'prior_visits': prior, 'previous_visit_count': previous_count,
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


def _family_key(value):
    text = text_value(value).strip().lower()
    if "incident" in text:
        return "incident"
    if "capex" in text:
        return "capex"
    if "5g" in text or "colo" in text:
        return "5g"
    return {"Incident": "incident", "Capex": "capex", "Colocation": "5g"}.get(normalize_family(value), "")


def _cycle_family_error(stream, cycle):
    """None when the cycle's project family matches the visit group; otherwise the reason."""
    expected = _family_key(field_feed.STREAM_PROJECT.get(stream, stream))
    actual = _family_key(cycle.project)
    if cycle.erp_project:
        project_meta = frappe.get_meta('Project')
        family_fields = [field for field in ('custom_project_family', 'custom_family')
                         if project_meta.has_field(field)]
        if family_fields:
            project = frappe.db.get_value('Project', cycle.erp_project, family_fields, as_dict=True)
            resolution = resolve_project_family(project)
            if resolution['conflict']:
                return 'PROJECT_FAMILY_FIELDS_CONFLICT_NEEDS_RECONCILIATION'
            # A linked Project with no family is unresolved; do not infer it from
            # the legacy cycle label when a canonical Project exists.
            actual = _family_key(resolution['family'])
    if expected and not actual:
        return 'PROJECT_FAMILY_UNRESOLVED_NEEDS_RECONCILIATION'
    if expected and actual and expected != actual:
        return 'CYCLE_FAMILY_DOES_NOT_MATCH_VISIT_GROUP'
    return None


ALLOCATE_WINDOW_DAYS = 30   # a cycle opened this long after a visit is a different work episode


def allocate_unallocated(limit=50):
    """Attach visits recorded without a cycle once the site has exactly one compatible open cycle.

    Runs after each feed run. Several open cycles, a family mismatch or a visit older than
    ALLOCATE_WINDOW_DAYS before the cycle was created leave the visit unallocated.
    """
    # Bounded keyset pages prevent old ineligible rows from starving later rows.
    # The cache cursor is only a scheduling hint; losing it restarts safely.
    if limit <= 0:
        return 0
    cache = frappe.cache()
    cache_key = 'sig_field_unallocated_scan_cursor'
    cursor = cache.get_value(cache_key)
    filters = {'posted': 1, 'diagnostics': ['like', '%UNALLOCATED%']}
    if cursor:
        filters['name'] = ['>', cursor]
    rows = frappe.get_all('SIG Field Session', filters=filters,
                          fields=['name', 'site_key', 'stream', 'start_at'], order_by='name asc',
                          limit_page_length=limit)
    allocated = sum(1 for row in rows if _allocate_unallocated_row(row))
    if len(rows) < limit:
        cache.delete_value(cache_key)
    else:
        cache.set_value(cache_key, rows[-1].name)
    return allocated


def _allocate_unallocated_row(row):
    """Try one already-posted session without inventing a cycle."""
    cycles = frappe.get_all('SIG Site Cycle', filters={'site_key': row.site_key, 'terminal': 0},
                            fields=['name', 'project', 'erp_project', 'creation'], limit_page_length=2)
    if len(cycles) != 1 or _cycle_family_error(row.stream, cycles[0]):
        return False
    floor = frappe.utils.add_days(frappe.utils.get_datetime(cycles[0].creation), -ALLOCATE_WINDOW_DAYS)
    if frappe.utils.get_datetime(row.start_at) < floor:
        return False
    try:
        result = field_feed.post_session(row.name, cycle_hint=cycles[0].name)
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title='SIG visit allocation failed', message='Session: ' + row.name + '\n' + frappe.get_traceback())
        return False
    if result.get('result') in ('created', 'duplicate'):
        frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Comment',
                        'reference_doctype': 'SIG Field Session', 'reference_name': row.name,
                        'content': 'Cycle allocated automatically: %s' % cycles[0].name}).insert(ignore_permissions=True)
        return True
    return False


@frappe.whitelist()
def post_to_cycle(session_key, cycle_name):
    """Attach a visit recorded without a cycle (or a legacy held session) to one open cycle."""
    _require_pm()
    doc = frappe.get_doc('SIG Field Session', text_value(session_key))
    diags = (doc.diagnostics or '').split(',')
    held = (not doc.posted and doc.status == 'COMPLETED' and doc.disposition == 'REVIEW'
            and 'CYCLE_ATTRIBUTION_EXCEPTION' in diags)
    unallocated = bool(doc.posted and 'UNALLOCATED' in diags and doc.visit
                       and not frappe.db.get_value('SIG Field Visit', doc.visit, 'cycle'))
    if not (held or unallocated):
        return {'result': 'exception', 'reason': 'SESSION_NOT_WAITING_FOR_CYCLE_SELECTION'}
    allowed_cycles = frappe.get_list('SIG Site Cycle',
        filters={'name': text_value(cycle_name), 'site_key': doc.site_key, 'terminal': 0},
        fields=['name', 'site_key', 'project', 'erp_project', 'wo', 'terminal'], limit_page_length=1)
    cycle = allowed_cycles[0] if allowed_cycles else None
    if not cycle:
        return {'result': 'exception', 'reason': 'SELECT_AN_OPEN_CYCLE_FOR_THIS_SITE'}
    family_error = _cycle_family_error(doc.stream, cycle)
    if family_error:
        return {'result': 'exception', 'reason': family_error}
    result = field_feed.post_session(doc.name, cycle_hint=cycle.name)
    if result.get('result') not in ('created', 'duplicate'):
        return {'result': result.get('result'), 'reason': result.get('detail') or result.get('reason'), 'post': result}
    frappe.db.set_value('SIG Field Session', doc.name, 'corrected_by', frappe.session.user, update_modified=False)
    frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Comment',
                    'reference_doctype': 'SIG Field Session', 'reference_name': doc.name,
                    'content': 'Cycle attribution selected: %s' % cycle.name}).insert(ignore_permissions=True)
    return {'result': result.get('result'), 'cycle': cycle.name, 'post': result}


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
def list_unpaired_ends(site_key=''):
    """Candidates for 'Pair a lonely End': recent End messages the assembler could not attach
    to any session (END_WITHOUT_START / AMBIGUOUS_END_TARGET), newest first. Filtered to the
    row's own site by default so a PM sees the End that actually belongs to it."""
    _require_pm()
    site_key = text_value(site_key).strip().upper()
    where = ["diagnostic IN ('END_WITHOUT_START', 'AMBIGUOUS_END_TARGET')"]
    values = []
    if site_key:
        where.append('site_key = %s')
        values.append(site_key)
    rows = frappe.db.sql(
        "SELECT msg_key, occurred_at, reporter_name, site_key, diagnostic FROM `tabSIG Field Message` "
        "WHERE " + ' AND '.join(where) + " ORDER BY occurred_at DESC LIMIT 30", tuple(values), as_dict=True)
    return [{'msg_key': r.msg_key, 'at': str(r.occurred_at), 'who': r.reporter_name, 'site': r.site_key,
             'diagnostic': r.diagnostic} for r in rows]


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
def confirm(session_key, note=''):
    """Acknowledge a REVIEW session as-is: no data changes, just a PM sign-off that the
    auto-closed/duplicate-start/etc. estimate is good enough to stand (owner decision
    2026-09-22: HARD_CAP_24H, NEW_START_MISSING_END, DUPLICATE_START and
    INVALID_NEGATIVE_DURATION are judgment calls an operator makes, never an automated
    guess - see white paper cp.md SS11.2/11.6 on that boundary). Clearing the flag must
    never make an already-represented historical session eligible for live (re)posting,
    so it lands on IN_ERP_WINDOW below the feed's own cutover point and PENDING only
    at/after it - the same split field_feed._upsert_sessions uses when it first files a
    session, so a confirmed session always ends up where the feed itself would have put
    it once its diagnostics/disposition stopped saying REVIEW.
    """
    _require_pm()
    doc = _session(session_key)
    if doc.disposition != 'REVIEW':
        return {'result': 'exception', 'reason': 'NOT_IN_REVIEW'}
    note = text_value(note).strip()
    if note:
        frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Comment', 'reference_doctype': 'SIG Field Session',
                        'reference_name': session_key, 'content': note}).insert(ignore_permissions=True)
    doc.disposition = ('IN_ERP_WINDOW' if str(doc.start_at) <= field_feed.ERP_LAST_VISIT
                       else ('PENDING' if doc.status == 'COMPLETED' else doc.disposition))
    doc.corrected_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {'result': 'ok', 'disposition': doc.disposition}


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
