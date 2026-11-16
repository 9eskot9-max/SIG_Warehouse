"""Update the evidence writer and restore missing dated visit checkpoints."""
import frappe

from sig_warehouse.sig_warehouse.patches.v1_0.align_operations_cycle_evidence import rewrite_evidence_writer


SECOND_VISIT_LOOKUP = """    if int(cycdoc.get('sessions_completed') or 0) + int(cycdoc.get('sessions_auto_closed') or 0) >= 2:
        sig_rule_visits = frappe.get_all('SIG Field Visit',
            filters={'cycle': cyc, 'status': ['in', ['COMPLETED', 'AUTO_CLOSED']]},
            fields=['start_at'], order_by='start_at asc, name asc', limit_page_length=2)
        if len(sig_rule_visits) == 2:
            sig_rule_row['second_visit_at'] = sig_rule_visits[1].start_at
"""


LAST_EVENT_UPDATE = """    cycdoc.set('last_event_at', occurred)
    cycdoc.set('last_event_code', event_code)
"""
LATEST_EVENT_UPDATE = """    # SIG_MONOTONIC_LAST_EVENT_V1
    if occurred >= str(cycdoc.get('last_event_at') or '')[:19]:
        cycdoc.set('last_event_at', occurred)
        cycdoc.set('last_event_code', event_code)
"""


def rewrite(source):
    updated = rewrite_evidence_writer(source)
    if updated.count(SECOND_VISIT_LOOKUP) != 1:
        frappe.throw("Cycle stage update stopped: legacy visit lookup is not recognized.")
    updated = updated.replace(SECOND_VISIT_LOOKUP, "", 1)
    if updated.count(LATEST_EVENT_UPDATE) == 1:
        return updated
    if updated.count(LAST_EVENT_UPDATE) != 1:
        frappe.throw("Cycle stage update stopped: last-event block is not recognized.")
    return updated.replace(LAST_EVENT_UPDATE, LATEST_EVENT_UPDATE, 1)


def fill_estimated_visit_dates():
    cycles = frappe.get_all("SIG Site Cycle", filters={
        "terminal": 0, "sessions_auto_closed": [">", 0], "first_visit_at": ["is", "not set"],
    }, fields=["name", "last_visit_at"], limit_page_length=0)
    for cycle in cycles:
        visits = frappe.get_all("SIG Field Visit", filters={
            "cycle": cycle.name, "status": ["in", ["COMPLETED", "AUTO_CLOSED"]],
            "start_at": ["is", "set"],
        }, pluck="start_at", order_by="start_at asc", limit_page_length=0)
        if visits:
            updates = {"first_visit_at": visits[0]}
            if not cycle.last_visit_at:
                updates["last_visit_at"] = visits[-1]
            frappe.db.set_value("SIG Site Cycle", cycle.name, updates, update_modified=False)


def execute():
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Cycle stage update stopped: evidence writer is missing.")
    original = frappe.db.get_value("Server Script", name, "script") or ""
    old_rule = "    if sig_tcn and sig_mir and sig_visits >= 1 and sig_tags:\n"
    new_rule = "    if sig_tcn and sig_mir and sig_visits >= 1 and sig_visit:\n"
    if original.count(old_rule) != 1 and original.count(new_rule) != 1:
        frappe.throw("Cycle stage update stopped: existing rule is not recognized.")
    updated = rewrite(original)
    if updated != original:
        frappe.db.set_value("Server Script", name, "script", updated)
    fill_estimated_visit_dates()
