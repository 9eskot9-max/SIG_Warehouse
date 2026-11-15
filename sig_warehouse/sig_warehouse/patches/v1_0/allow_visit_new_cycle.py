"""Allow a completed visit to start a new scope when a site has no open cycle."""

import frappe


OLD = """                else:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits'}
                    return
        elif event_code not in"""

NEW = """                elif event_code != 'FIELD_VISIT_COMPLETED' or open_rows:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits'}
                    return
                # A completed visit at a site with no open scope starts a new
                # temporary cycle below. Never select a closed or unrelated scope.
        elif event_code not in"""


def rewrite(source):
    if source.count(NEW) == 1 and source.count(OLD) == 0:
        return source
    if source.count(OLD) != 1 or source.count(NEW):
        raise ValueError('Evidence resolver does not match the reviewed source; inspect before migration.')
    return source.replace(OLD, NEW, 1)


def execute():
    name = 'register_evidence_event'
    if not frappe.db.exists('Server Script', name):
        frappe.throw('Cannot update cycle attribution: register_evidence_event is missing.')
    try:
        source = rewrite(frappe.db.get_value('Server Script', name, 'script') or '')
    except ValueError as error:
        frappe.throw(str(error))
    frappe.db.set_value('Server Script', name, 'script', source)
