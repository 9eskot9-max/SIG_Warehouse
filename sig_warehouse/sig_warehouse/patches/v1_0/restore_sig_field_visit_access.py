"""Restore the complete, least-privilege SIG Field Visit role matrix.

Frappe v15 treats any Custom DocPerm rows as the effective permission list.
The live SIG Field Ops-only row was therefore hiding the four standard
audiences declared for this DocType. Keep the full intended matrix in one
repeatable patch and stop if an unknown custom audience is present.
"""

import frappe


PTYPES = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)

EXPECTED = {
    "System Manager": {"read": 1, "write": 1, "create": 1, "delete": 1,
                       "print": 1, "email": 1, "export": 1, "report": 1, "share": 1},
    "Projects Manager": {"read": 1, "report": 1, "export": 1},
    "Projects User": {"read": 1, "report": 1, "export": 1},
    "Warehouse Manager": {"read": 1, "report": 1, "export": 1},
    "SIG Field Ops": {"read": 1, "export": 1},
}


def _rows():
    return frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "SIG Field Visit"},
        fields=["name", "role", "permlevel", "if_owner"] + list(PTYPES),
        order_by="idx asc",
    )


def execute():
    """Set every approved ptype exactly; refuse to erase unreviewed roles."""
    rows = _rows()
    unexpected = [row.role for row in rows
                  if int(row.permlevel or 0) != 0 or int(row.if_owner or 0)
                  or row.role not in EXPECTED]
    if unexpected:
        frappe.throw(
            "SIG Field Visit access repair stopped: unreviewed custom permission rows exist."
        )

    by_role = {}
    for row in rows:
        if row.role in by_role:
            frappe.throw("SIG Field Visit access repair stopped: duplicate role rows exist.")
        by_role[row.role] = row

    for role, grants in EXPECTED.items():
        values = {ptype: int(bool(grants.get(ptype))) for ptype in PTYPES}
        row = by_role.get(role)
        if row:
            doc = frappe.get_doc("Custom DocPerm", row.name)
            changed = any(int(doc.get(ptype) or 0) != values[ptype] for ptype in PTYPES)
            if changed:
                for ptype, value in values.items():
                    doc.set(ptype, value)
                doc.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": "SIG Field Visit",
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": 0,
                "if_owner": 0,
                **values,
            }).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="SIG Field Visit")
    frappe.logger("sig_warehouse").info(
        "SIG Field Visit full role permission matrix restored for %s",
        ",".join(EXPECTED),
    )
