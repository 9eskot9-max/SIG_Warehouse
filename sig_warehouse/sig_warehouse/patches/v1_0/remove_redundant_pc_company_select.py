"""Restore the Company baseline after the misdiagnosed reviewer incident."""

import frappe

from .allow_pc_clearance_company_select import BASELINE, PERM_FIELDS, TARGET, _signature


def execute():
    rows = frappe.get_all(
        "Custom DocPerm", filters={"parent": "Company"},
        fields=["name", "role", "permlevel", "if_owner", *PERM_FIELDS],
        limit_page_length=0,
    )
    actual = {row.role: _signature(row) for row in rows}
    with_grant = {**BASELINE, "SIG PC Clearance": TARGET}
    if len(actual) != len(rows) or actual not in (BASELINE, with_grant):
        frappe.throw("Company permissions changed since review; no permissions were modified.")
    if actual == with_grant:
        row = next(row for row in rows if row.role == "SIG PC Clearance")
        frappe.delete_doc("Custom DocPerm", row.name, ignore_permissions=True)
        frappe.clear_cache(doctype="Company")
