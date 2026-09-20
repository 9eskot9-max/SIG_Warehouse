"""Project Progress read model and native human update writer.

This is the app-backed version of the Project Progress page. Evidence remains
immutable in SIG Evidence Event; this module only projects it for monitoring and
adds permission-checked native Comments.
"""

import frappe


def text_value(value):
    return str(value or '').strip()


def project_options():
    rows = frappe.db.sql(
        "SELECT DISTINCT project FROM `tabSIG Site Cycle` "
        "WHERE IFNULL(project, '') <> '' ORDER BY project ASC LIMIT 500",
        as_dict=True,
    )
    return [text_value(row.project) for row in rows if text_value(row.project)]


def comments_for(names):
    if not names:
        return {}
    marks = ','.join(['%s'] * len(names))
    rows = frappe.db.sql(
        "SELECT reference_name, content, owner, creation FROM `tabComment` "
        "WHERE reference_doctype = 'SIG Site Cycle' AND comment_type = 'Comment' "
        "AND reference_name IN (" + marks + ") ORDER BY creation DESC LIMIT 2000",
        tuple(names), as_dict=True,
    )
    out = {}
    for row in rows:
        key = text_value(row.reference_name)
        out.setdefault(key, []).append({
            'content': text_value(row.content), 'owner': text_value(row.owner),
            'creation': str(row.creation or ''),
        })
    return out


def todos_for(names):
    if not names:
        return {}
    marks = ','.join(['%s'] * len(names))
    rows = frappe.db.sql(
        "SELECT reference_name, description, date, status, allocated_to "
        "FROM `tabToDo` WHERE reference_type = 'SIG Site Cycle' "
        "AND status NOT IN ('Closed', 'Cancelled') AND reference_name IN (" + marks + ") "
        "ORDER BY date ASC, creation ASC",
        tuple(names), as_dict=True,
    )
    out = {}
    for row in rows:
        key = text_value(row.reference_name)
        out.setdefault(key, []).append({
            'description': text_value(row.description) or 'Follow-up',
            'date': str(row.date or ''), 'status': text_value(row.status),
            'allocated_to': text_value(row.allocated_to),
        })
    return out


def activity_for(row):
    fields = (
        ('Mapping', 'mapping_at'), ('BOQ', 'boq_at'), ('Plan document', 'pimp_at'),
        ('TCN', 'tcn_at'), ('MIR', 'mir_at'), ('Visit', 'first_visit_at'),
        ('Tags', 'tags_at'), ('Photos', 'photos_at'), ('Warranty', 'warranty_at'),
        ('Handover document', 'ho_at'), ('As-built BOQ', 'asbuilt_at'),
    )
    out = []
    for item in fields:
        label = item[0]
        field = item[1]
        out.append({'label': label, 'state': 'Recorded' if row.get(field) else 'Not recorded',
                    'at': str(row.get(field) or '')})
    return out


def position_for(row):
    if row.get('terminal') and row.get('closed_on'):
        return 'Explicit closure', 'SITE_CLOSED'
    if row.get('asbuilt_at'):
        return 'As-built recorded', 'As-built evidence exists; closure remains separate'
    if row.get('ho_at'):
        return 'As-built preparation', 'Handover document recorded'
    if row.get('first_visit_at') and row.get('tcn_at') and row.get('mir_at'):
        return 'Handover evidence', 'Visit + TCN + MIR'
    if row.get('pimp_at') or row.get('tcn_at') or row.get('mir_at') or row.get('first_visit_at'):
        return 'Implementation', 'Implementation evidence is partial'
    return 'Preparation', 'Mapping / BOQ evidence'


def events_for(cycle):
    if not frappe.db.exists('SIG Site Cycle', cycle):
        frappe.throw('SIG Site Cycle was not found.')
    rows = frappe.db.sql(
        "SELECT event_code, occurred_at, recorded_at, artifact_ref, source_sub, event_id "
        "FROM `tabSIG Evidence Event` WHERE cycle = %s "
        "ORDER BY occurred_at DESC, recorded_at DESC LIMIT 80",
        (cycle,), as_dict=True,
    )
    return [{'code': text_value(row.event_code), 'occurred_at': str(row.occurred_at or ''),
             'recorded_at': str(row.recorded_at or ''), 'artifact_ref': text_value(row.artifact_ref),
             'source': text_value(row.source_sub), 'event_id': text_value(row.event_id)}
            for row in rows]


@frappe.whitelist()
def get_events(cycle):
    if not frappe.has_permission('SIG Site Cycle', 'read', cycle):
        frappe.throw('You do not have permission to read this cycle.')
    return events_for(text_value(cycle))


@frappe.whitelist()
def get_progress(project='', view='current', search=''):
    project = text_value(project)
    view = text_value(view) or 'current'
    search = text_value(search).lower()
    where = ['1 = 1']
    values = []
    if project:
        where.append("IFNULL(sc.project, '') = %s")
        values.append(project)
    if search:
        like = '%' + search + '%'
        where.append("(LOWER(IFNULL(sc.site_key, '')) LIKE %s OR LOWER(IFNULL(sc.project, '')) LIKE %s "
                     "OR LOWER(IFNULL(sc.po, '')) LIKE %s OR LOWER(IFNULL(sc.wo, '')) LIKE %s)")
        values.extend([like, like, like, like])
    rows = frappe.db.sql(
        "SELECT sc.name, sc.site_key, sc.site, sc.project, sc.po, sc.wo, sc.scope_id, "
        "sc.stage, sc.terminal, sc.closed_on, sc.gross_value, sc.mapping_at, sc.boq_at, "
        "sc.pimp_at, sc.tcn_at, sc.mir_at, sc.first_visit_at, sc.first_impl_visit_at, "
        "sc.tags_at, sc.photos_at, sc.warranty_at, sc.ho_at, sc.ho_doc_type, sc.asbuilt_at, "
        "sc.last_event_at, sc.last_event_code, sc.stage_anchor_at, sc.stage_due_on, "
        "sc.delay_reason, sc.delay_note, sc.cycle_flags, sc.resolution_state "
        "FROM `tabSIG Site Cycle` sc WHERE " + ' AND '.join(where) +
        " ORDER BY sc.terminal ASC, sc.stage_due_on ASC, sc.last_event_at DESC, sc.site_key ASC LIMIT 500",
        tuple(values), as_dict=True,
    )
    names = [text_value(row.name) for row in rows]
    comments = comments_for(names)
    todos = todos_for(names)
    result = []
    for row in rows:
        name = text_value(row.name)
        position_result = position_for(row)
        position = position_result[0]
        basis = position_result[1]
        task_rows = todos.get(name) or []
        latest = (comments.get(name) or [None])[0]
        record = {
            'name': name, 'site': text_value(row.site_key) or text_value(row.site),
            'project': text_value(row.project) or 'Basic / unallocated work',
            'po': text_value(row.po), 'wo': text_value(row.wo), 'scope_id': text_value(row.scope_id),
            'stage': text_value(row.stage), 'terminal': int(row.terminal or 0),
            'position': position, 'basis': basis, 'gross_value': row.gross_value,
            'activities': activity_for(row), 'last_event_at': str(row.last_event_at or ''),
            'last_event_code': text_value(row.last_event_code),
            'delay_reason': text_value(row.delay_reason), 'delay_note': text_value(row.delay_note),
            'cycle_flags': text_value(row.cycle_flags), 'resolution_state': text_value(row.resolution_state),
            'stage_due_on': str(row.stage_due_on or '')[:10],
            'todo': task_rows[0] if task_rows else None,
            'comments': comments.get(name) or [], 'comment_count': len(comments.get(name) or []),
            'latest_comment': latest,
        }
        if view == 'history' and not record['terminal']:
            continue
        if view != 'history' and view != 'current' and record['terminal']:
            continue
        if view == 'followup' and not record['todo']:
            continue
        if view == 'blockers' and not record['delay_reason']:
            continue
        if view == 'review' and record['resolution_state'] != 'AMBIGUOUS' and 'AMBIGUOUS' not in record['cycle_flags']:
            continue
        result.append(record)
    due = 0
    blockers = 0
    reviews = 0
    sites = []
    for item in result:
        if item.get('todo') and item['todo'].get('date') and item['todo']['date'] < frappe.utils.nowdate():
            due += 1
        if item.get('delay_reason'):
            blockers += 1
        if item.get('resolution_state') == 'AMBIGUOUS' or 'AMBIGUOUS' in item.get('cycle_flags', ''):
            reviews += 1
        if item.get('site') and item['site'] not in sites:
            sites.append(item['site'])
    return {'result': 'ok', 'rows': result, 'projects': project_options(),
            'summary': {'scopes': len(result), 'sites': len(sites), 'due': due,
                        'blockers': blockers, 'reviews': reviews}}


@frappe.whitelist()
def add_comment(cycle, content):
    cycle = text_value(cycle)
    content = text_value(content)
    if not cycle or not content:
        frappe.throw('Cycle and update text are required.')
    if len(content) > 4000:
        frappe.throw('Update text is limited to 4,000 characters.')
    if not frappe.db.exists('SIG Site Cycle', cycle):
        frappe.throw('SIG Site Cycle was not found.')
    if not frappe.has_permission('SIG Site Cycle', 'write', cycle):
        frappe.throw('You do not have permission to add an update to this cycle.')
    comment = frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Comment',
                              'reference_doctype': 'SIG Site Cycle',
                              'reference_name': cycle, 'content': content})
    comment.insert()
    return {'result': 'ok', 'comment': {'content': content, 'owner': frappe.session.user,
                                        'creation': str(comment.creation or '')}}

