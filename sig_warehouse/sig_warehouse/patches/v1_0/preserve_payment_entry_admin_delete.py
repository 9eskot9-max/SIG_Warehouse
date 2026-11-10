"""Preserve the owner-authorized ERP Admin Payment Entry read/delete grant.

Custom rows replace standard permissions; never create a sparse replacement.
"""
import frappe

FIELDS = ("role", "permlevel", "if_owner", "select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "share", "print", "email", "mask")


def row(role, **flags):
    return {field: role if field == "role" else int(flags.get(field, 0)) for field in FIELDS}


BASELINE = [
    row("Accounts User", read=1, write=1, create=1, submit=1, cancel=1, export=1, print=1),
    row("Accounts Manager", read=1, write=1, create=1, submit=1, cancel=1, export=1, print=1),
    row("SIG Finance Viewer", read=1, export=1, print=1),
    row("Operations Manager", create=1), row("Operations User", create=1),
]
GRANT = row("ERP Admin", read=1, delete=1)


def normalized(rows):
    return sorted([row(r.get("role"), **{f: r.get(f) or 0 for f in FIELDS if f != "role"}) for r in rows], key=lambda r: (r["role"], r["permlevel"], r["if_owner"]))


def execute():
    current = frappe.get_all("Custom DocPerm", filters={"parent": "Payment Entry"}, fields=list(FIELDS), limit_page_length=0)
    if normalized(current) == normalized(BASELINE + [GRANT]):
        return
    if normalized(current) != normalized(BASELINE):
        frappe.throw("Payment Entry permission matrix differs from the reviewed baseline; grant not applied.")
    frappe.get_doc({"doctype": "Custom DocPerm", "parent": "Payment Entry", "parenttype": "DocType", "parentfield": "permissions", **GRANT}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Payment Entry")
    after = frappe.get_all("Custom DocPerm", filters={"parent": "Payment Entry"}, fields=list(FIELDS), limit_page_length=0)
    if normalized(after) != normalized(BASELINE + [GRANT]):
        frappe.throw("Payment Entry permission readback differs from the reviewed target.")
