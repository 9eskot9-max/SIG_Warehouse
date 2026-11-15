"""Stop creating a temporary cycle for a visit at a site with no open cycle.

Owner decision 2026-11-15: closure is for convenience, so a visit after closure is
recorded without a cycle (field_feed._record_unallocated) instead of starting a new
scope. This reverses the branch added by allow_visit_new_cycle, then re-queues the
sessions that were held for cycle attribution so the feed records them.
"""

import frappe


NEW = """                elif event_code != 'FIELD_VISIT_COMPLETED' or open_rows:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits'}
                    return
                # A completed visit at a site with no open scope starts a new
                # temporary cycle below. Never select a closed or unrelated scope.
        elif event_code not in"""

OLD = """                else:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits'}
                    return
        elif event_code not in"""


def rewrite(source):
    if source.count(OLD) == 1 and source.count(NEW) == 0:
        return source
    if source.count(NEW) != 1 or source.count(OLD):
        raise ValueError('Evidence resolver does not match the reviewed source; inspect before migration.')
    return source.replace(NEW, OLD, 1)


def requeue_held_sessions():
    names = frappe.get_all('SIG Field Session', filters={
        'posted': 0, 'disposition': 'REVIEW', 'status': 'COMPLETED',
        'diagnostics': ['like', '%CYCLE_ATTRIBUTION_EXCEPTION%']}, pluck='name', limit_page_length=0)
    for name in names:
        diagnostics = frappe.db.get_value('SIG Field Session', name, 'diagnostics') or ''
        # Held only for the cycle; anything else that needs a person keeps it in review.
        if 'UNRESOLVED_SITE' in diagnostics or 'NO_EMPLOYEE_FOR_PHONE' in diagnostics:
            continue
        frappe.db.set_value('SIG Field Session', name, 'disposition', 'PENDING', update_modified=False)
    return names


def execute():
    name = 'register_evidence_event'
    if not frappe.db.exists('Server Script', name):
        frappe.throw('Cannot update cycle attribution: register_evidence_event is missing.')
    try:
        source = rewrite(frappe.db.get_value('Server Script', name, 'script') or '')
    except ValueError as error:
        frappe.throw(str(error))
    frappe.db.set_value('Server Script', name, 'script', source)
    requeue_held_sessions()
