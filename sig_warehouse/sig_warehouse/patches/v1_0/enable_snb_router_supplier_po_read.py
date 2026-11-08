"""Add read-only Purchase Order access needed by the SNB payment-reference picker.

The live site already has a Custom DocPerm matrix for Purchase Order. Since any
custom rows replace the standard matrix, validate and preserve every existing
row before adding Accounts User/Manager read-only rows.
"""
import frappe


PERMISSION_FIELDS = (
    "role", "permlevel", "if_owner", "select", "read", "write", "create",
    "delete", "submit", "cancel", "amend", "report", "export", "import",
    "share", "print", "email", "mask",
)


def _row(role, permlevel, **values):
    return {field: int(values.get(field, 0)) if field != "role" else role for field in PERMISSION_FIELDS} | {
        "permlevel": int(permlevel),
    }


BASELINE = [
    _row("Purchase User", 0, read=1, report=1, export=1, print=1),
    _row("Purchase Manager", 0, read=1, write=1, create=1, delete=1, submit=1, cancel=1, amend=1, report=1, export=1, share=1, print=1, email=1),
    _row("Stock User", 0, read=1, report=1, export=1),
    _row("Purchase Manager", 1, read=1, write=1, export=1),
    _row("SIG PO Limited 100k", 0, read=1, write=1, create=1, submit=1, delete=1, report=1, export=1, print=1, email=1),
    _row("SIG PO Limited 300k", 0, read=1, write=1, create=1, submit=1, delete=1, report=1, export=1, print=1, email=1),
]
ADDITIONS = [
    _row("Accounts User", 0, read=1),
    _row("Accounts Manager", 0, read=1),
]


def _normalized(rows):
    result = []
    for row in rows:
        item = {field: row.get(field, 0) for field in PERMISSION_FIELDS}
        item["permlevel"] = int(item["permlevel"] or 0)
        item["if_owner"] = int(item["if_owner"] or 0)
        for field in PERMISSION_FIELDS[3:]:
            item[field] = int(item[field] or 0)
        result.append(item)
    return sorted(result, key=lambda item: (item["role"], item["permlevel"]))


def execute():
    actual = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "Purchase Order"},
        fields=list(PERMISSION_FIELDS),
        order_by="role asc, permlevel asc",
    )
    current = _normalized(actual)
    baseline = _normalized(BASELINE)
    target = _normalized(BASELINE + ADDITIONS)

    if current == target:
        return
    if current != baseline:
        frappe.throw(
            "Purchase Order Custom DocPerm rows differ from the reviewed SNB Router baseline; "
            "no permission rows were changed."
        )

    for row in ADDITIONS:
        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": "Purchase Order",
            "parenttype": "DocType",
            "parentfield": "permissions",
            **row,
        }).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Purchase Order")
    refreshed = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "Purchase Order"},
        fields=list(PERMISSION_FIELDS),
        order_by="role asc, permlevel asc",
    )
    if _normalized(refreshed) != target:
        frappe.throw("Purchase Order Custom DocPerm rows do not match the reviewed target matrix.")
