"""Repair the embedded stage writer without rewriting cycle history or permissions."""

import frappe

from sig_warehouse.sig_warehouse.patches.v1_0.align_operations_cycle_evidence import rewrite_evidence_writer


def execute():
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Evidence repair stopped: register_evidence_event is missing.")
    source = frappe.db.get_value("Server Script", name, "script") or ""
    repaired = rewrite_evidence_writer(source)
    if source != repaired:
        frappe.db.set_value("Server Script", name, "script", repaired)
    # No backfill, replay, permission reset or stored-stage reconciliation.
    frappe.clear_cache(doctype="Server Script")
