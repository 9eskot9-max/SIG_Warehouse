"""Declared change: give Projects User read on SIG Site.

SIG Site's permissions come only from Custom DocPerm rows (Frappe v15 ignores the DocType's own list
once any custom row exists), so this adds exactly one row and leaves every other row untouched. It
grants `read` and nothing else; it refuses to run when SIG Site has no custom rows, because adding
the first one would shadow the standard list. No User, Role Profile or Page setting changes.
"""
import frappe

DOCTYPE = "SIG Site"
ROLE = "Projects User"
PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend",
          "report", "export", "import", "print", "email", "share", "select")


def execute():
    existing = frappe.get_all("Custom DocPerm", filters={"parent": DOCTYPE}, fields=["name", "role", "permlevel"])
    if not existing:
        frappe.throw("SIG Site has no Custom DocPerm rows; adding one would replace its standard permissions. "
                     "Review the baseline before running this patch.")
    row = next((r for r in existing if r["role"] == ROLE and not (r["permlevel"] or 0)), None)
    if row:
        frappe.db.set_value("Custom DocPerm", row["name"], "read", 1, update_modified=False)
    else:
        frappe.get_doc({"doctype": "Custom DocPerm", "parent": DOCTYPE, "parenttype": "DocType",
                        "parentfield": "permissions", "role": ROLE, "permlevel": 0, "if_owner": 0,
                        **{ptype: 1 if ptype == "read" else 0 for ptype in PTYPES}}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=DOCTYPE)
