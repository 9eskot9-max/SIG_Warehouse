"""Ignore Employee User Permissions on the finance-only funded-Employee field."""

import frappe


FIELDNAME = "Journal Entry-custom_pc_employee"


def execute():
    if not frappe.db.exists("Custom Field", FIELDNAME):
        frappe.throw("Journal Entry Funded Employee field is missing; no permissions were changed.")

    field = frappe.get_doc("Custom Field", FIELDNAME)
    if field.fieldtype != "Link" or field.options != "Employee":
        frappe.throw("Journal Entry Funded Employee field contract changed; review before migration.")

    if int(field.get("ignore_user_permissions") or 0) == 1:
        return

    field.ignore_user_permissions = 1
    field.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Journal Entry")
