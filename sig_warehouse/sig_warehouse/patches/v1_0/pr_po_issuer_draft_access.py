"""Give PO issuers draft-only Purchase Receipt access without replacing other grants."""
import frappe

DOCTYPE = "Purchase Receipt"
ROLES = ("Purchase Manager", "SIG PO Limited 100k", "SIG PO Limited 300k")
PTYPES = ("read", "write", "create", "submit", "cancel", "delete", "amend", "report", "export", "import", "print", "email", "share", "select")
EXPECTED = {key: int(key in ("read", "write", "create")) for key in PTYPES}


def execute():
    rows = frappe.get_all("Custom DocPerm", filters={"parent": DOCTYPE},
                          fields=["name", "role", "permlevel", "if_owner"] + list(PTYPES), limit_page_length=0)
    if not rows:
        frappe.throw("Purchase Receipt has no Custom DocPerm baseline; review before adding draft access.")
    missing = []
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.throw("Missing role: " + role)
        matches = [r for r in rows if r.role == role and int(r.permlevel or 0) == 0]
        if len(matches) > 1:
            frappe.throw("Duplicate Purchase Receipt permission rows for " + role)
        if matches:
            row = matches[0]
            if int(row.if_owner or 0) or any(int(row.get(k) or 0) != v for k, v in EXPECTED.items()):
                frappe.throw("Existing Purchase Receipt permission for " + role + " needs review.")
            continue
        missing.append(role)
    for role in missing:
        frappe.get_doc({"doctype": "Custom DocPerm", "parent": DOCTYPE, "parenttype": "DocType",
                        "parentfield": "permissions", "role": role, "permlevel": 0, "if_owner": 0,
                        **EXPECTED}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=DOCTYPE)
