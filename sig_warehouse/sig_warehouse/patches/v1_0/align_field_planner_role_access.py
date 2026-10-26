"""Add the least privileges required by the Field Planner's published roles.

The Page/API admits Projects Manager and Projects User, but the live v15 custom
permission matrices previously omitted those roles from planner dependencies.
Custom DocPerm rows replace the full standard matrix, so validate the captured
baseline and add only read-only rows. Planner decisions are created through the
role-gated API and have a separate read/create grant for Projects Manager.
"""

import frappe


PTYPES = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)

MATRICES = {
    "SIG Site Cycle": {
        "preserve": {
            "System Manager": {"read": 1, "write": 1},
            "Projects User": {"read": 1, "write": 1, "export": 1, "select": 1},
            "SIG Field Ops": {"read": 1, "write": 1, "export": 1},
        },
        "add_read": ("Projects Manager",),
    },
    "SIG Evidence Event": {
        "preserve": {
            "SIG Field Ops": {"read": 1, "write": 1, "create": 1, "export": 1},
            "System Manager": {"read": 1, "create": 1},
        },
        "add_read": ("Projects Manager", "Projects User"),
    },
}


def _values(row):
    return {ptype: int(bool(row.get(ptype))) for ptype in PTYPES}


def _expected(grants):
    return {ptype: int(ptype in grants) for ptype in PTYPES}


def _align(doctype, spec):
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": doctype},
        fields=["name", "role", "permlevel", "if_owner"] + list(PTYPES),
        order_by="idx asc",
    )
    expected_roles = set(spec["preserve"]) | set(spec["add_read"])
    by_role = {}
    for row in rows:
        if int(row.permlevel or 0) != 0 or int(row.if_owner or 0) or row.role not in expected_roles:
            frappe.throw(doctype + " planner access stopped: unreviewed Custom DocPerm row exists.")
        if row.role in by_role:
            frappe.throw(doctype + " planner access stopped: duplicate role rows exist.")
        by_role[row.role] = row

    for role, grants in spec["preserve"].items():
        row = by_role.get(role)
        if not row or _values(row) != _expected(grants):
            frappe.throw(doctype + " planner access stopped: the captured permission baseline changed for " + role + ".")

    read_only = _expected({"read"})
    for role in spec["add_read"]:
        row = by_role.get(role)
        if row:
            if _values(row) != read_only:
                frappe.throw(doctype + " planner access stopped: existing " + role + " row is not read-only.")
            continue
        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": role,
            "permlevel": 0,
            "if_owner": 0,
            **read_only,
        }).insert(ignore_permissions=True)


def execute():
    for doctype, spec in MATRICES.items():
        _align(doctype, spec)
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.clear_cache(doctype="SIG Evidence Event")
    frappe.logger("sig_warehouse").info(
        "Field Planner roles aligned: Projects Manager cycle/evidence read; Projects User evidence read"
    )
