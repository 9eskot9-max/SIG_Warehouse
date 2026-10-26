"""Allow PC reviewers to resolve their assigned Company Link value only.

Company is governed by Custom DocPerm rows on this site. In Frappe v15, those
rows replace the standard permission matrix, so preserve and validate the
complete existing set before adding the one select-only role row.
"""

import frappe


PERM_FIELDS = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)

# Production Company Custom DocPerm baseline captured 2026-10-26. Each row is
# (permlevel, if_owner, *PERM_FIELDS). Failing closed prevents a one-row patch
# from silently replacing or accepting an unrelated permission change.
BASELINE = {
    "Accounts Manager": (0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0),
    "Accounts User": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0),
    "Auditor": (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    "Desk User": (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    "Employee": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Employee Self Service": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0),
    "Projects User": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Purchase User": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Sales Manager": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Sales User": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Stock User": (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "System Manager": (0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0),
}
TARGET = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)


def _signature(row):
    return (
        int(row.get("permlevel") or 0),
        int(row.get("if_owner") or 0),
        *(int(row.get(field) or 0) for field in PERM_FIELDS),
    )


def execute():
    fields = ["name", "role", "permlevel", "if_owner", *PERM_FIELDS]
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "Company"},
        fields=fields,
        limit_page_length=0,
    )
    actual = {row.role: _signature(row) for row in rows}
    expected = dict(BASELINE)
    expected["SIG PC Clearance"] = TARGET

    if len(actual) != len(rows) or actual not in (BASELINE, expected):
        frappe.throw(
            "Company custom permission matrix changed since review. "
            "No permissions were modified; compare the complete matrix first."
        )

    if actual == BASELINE:
        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": "Company",
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": "SIG PC Clearance",
            "permlevel": 0,
            "if_owner": 0,
            **{field: int(field == "select") for field in PERM_FIELDS},
        }).insert(ignore_permissions=True)
        frappe.clear_cache(doctype="Company")
