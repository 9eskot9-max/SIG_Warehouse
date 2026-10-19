"""Reapply the canonical stage rule and remove stale unsupported Handover labels."""

import frappe

from sig_warehouse.sig_warehouse.patches.v1_0.align_operations_cycle_evidence import (
    reconcile_open_cycles,
    rewrite_daily_flags,
    rewrite_evidence_writer,
)


def execute():
    """Update the embedded writer and reconcile stages without changing evidence."""
    updates = {}
    for name, rewrite in (("register_evidence_event", rewrite_evidence_writer),
                          ("sig_field_ops_daily", rewrite_daily_flags)):
        if not frappe.db.exists("Server Script", name):
            frappe.throw("Handover reconciliation stopped: required Server Script is missing.")
        source = frappe.db.get_value("Server Script", name, "script") or ""
        updates[name] = rewrite(source)
    for name, source in updates.items():
        if (frappe.db.get_value("Server Script", name, "script") or "") != source:
            frappe.db.set_value("Server Script", name, "script", source)
    changed = reconcile_open_cycles()
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.logger("sig_warehouse").info(
        "Reconciled evidence-gated Handover stage; open cycles updated=%s", changed)

