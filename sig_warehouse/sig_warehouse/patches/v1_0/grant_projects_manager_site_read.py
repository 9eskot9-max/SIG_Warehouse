"""Grant Projects Manager read-only access to SIG Site for planner site selection.

SIG Site permissions are maintained through Custom DocPerm rows. Add only this role's
read permission; preserve every existing row and refuse to create the first custom row.
"""
import frappe

DOCTYPE = "SIG Site"
ROLE = "Projects Manager"
PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend",
          "report", "export", "import", "print", "email", "share", "select")


def execute():
    existing = frappe.get_all("Custom DocPerm", filters={"parent": DOCTYPE}, fields=["name", "role", "permlevel"])
    if not existing:
        frappe.throw("SIG Site has no Custom DocPerm rows; review the full permission matrix before adding access.")
    row = next((r for r in existing if r["role"] == ROLE and not (r["permlevel"] or 0)), None)
    if row:
        frappe.db.set_value("Custom DocPerm", row["name"], "read", 1, update_modified=False)
    else:
        frappe.get_doc({"doctype": "Custom DocPerm", "parent": DOCTYPE, "parenttype": "DocType",
                        "parentfield": "permissions", "role": ROLE, "permlevel": 0, "if_owner": 0,
                        **{ptype: 1 if ptype == "read" else 0 for ptype in PTYPES}}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=DOCTYPE)
