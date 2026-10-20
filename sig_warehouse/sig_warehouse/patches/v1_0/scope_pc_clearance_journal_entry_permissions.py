"""Limit the PC-only role to scoped JE read/create; preserve the full matrix."""

import frappe


PERM_FIELDS = ("read", "write", "create", "submit", "cancel", "delete", "amend",
               "report", "export", "import", "print", "email", "share", "select")

# Live v15 baseline captured before this patch. Custom DocPerm rows replace the
# standard matrix, so fail closed if any role or ptype has drifted.
CUSTOM_BASELINE = {
    "Accounts User": (1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0),
    "Accounts Manager": (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0),
    "Auditor": (1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0),
    "Employee Self Service": (0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1),
    "SIG Finance Viewer": (1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0),
    "SIG PC Clearance": (1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
}

# The target row after migration. Create is retained for the native, scoped
# confirm_receipt insert; submit and cancel remain off.
TARGET = (1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _signature(row):
    return tuple(int(row.get(field) or 0) for field in PERM_FIELDS)


def execute():
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "Journal Entry"},
        fields=["name", "role", *PERM_FIELDS],
        limit_page_length=0,
    )
    actual = {row.role: _signature(row) for row in rows}
    expected = dict(CUSTOM_BASELINE)
    expected["SIG PC Clearance"] = TARGET
    if len(actual) != len(rows) or actual not in (CUSTOM_BASELINE, expected):
        frappe.throw(
            "Journal Entry custom permission matrix changed since review. "
            "No permissions were modified; compare the complete matrix first."
        )

    target = next(row for row in rows if row.role == "SIG PC Clearance")
    if _signature(target) != TARGET:
        doc = frappe.get_doc("Custom DocPerm", target.name)
        doc.set("write", 0)
        doc.set("export", 0)
        doc.save(ignore_permissions=True)
        frappe.clear_cache(doctype="Journal Entry")
