"""Add Must to the cycle's Planner Mark (Hold, Visited, Must) on sites that already have the field.

Options change only; no schema change, no permission change. Idempotent.
"""
import frappe

OPTIONS = "\nHold\nVisited\nMust"


def execute():
    name = frappe.db.get_value("Custom Field", {"dt": "SIG Site Cycle", "fieldname": "plan_hold"}, "name")
    if not name:
        return
    field = frappe.get_doc("Custom Field", name)
    if field.options == OPTIONS:
        return
    field.options = OPTIONS
    field.save(ignore_permissions=True)
    frappe.clear_cache(doctype="SIG Site Cycle")
