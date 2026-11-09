"""Persist shortage deferral on invoice bridge rows across draft/submit retries."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
    if not frappe.db.exists("DocType", "SIG Tawal Invoice Link"):
        frappe.throw("Cannot add TAWAL cycle deferral state: SIG Tawal Invoice Link is missing.")
    field = {"fieldname": "defer_cycle_closure", "label": "Defer Cycle Closure",
             "fieldtype": "Check", "default": "0", "read_only": 1,
             "hidden": 1,
             "description": "Invoice allocation was short on open cycles; keep this site's reserved cycles open on retry."}
    existing = frappe.db.get_value("Custom Field",
        {"dt": "SIG Tawal Invoice Link", "fieldname": field["fieldname"]},
        ["name", "fieldtype"], as_dict=True)
    if existing:
        if existing.fieldtype != "Check":
            frappe.throw("Unexpected field type for SIG Tawal Invoice Link.defer_cycle_closure.")
    else:
        create_custom_field("SIG Tawal Invoice Link", field)
    frappe.clear_cache(doctype="SIG Tawal Invoice Link")
