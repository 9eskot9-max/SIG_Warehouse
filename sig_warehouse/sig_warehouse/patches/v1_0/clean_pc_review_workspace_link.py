"""Remove the retired duplicate invoice-review shortcut and its layout block."""

import json

import frappe


WORKSPACE = "SIG Petty Cash"
PAGE = "pc-invoice-review"
SHORTCUT_LABEL = "Invoice Review Board"


def execute():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return

    workspace = frappe.get_doc("Workspace", WORKSPACE)
    changed = False

    shortcut_rows = [row for row in workspace.shortcuts if row.label == SHORTCUT_LABEL]
    if shortcut_rows:
        if (
            len(shortcut_rows) != 1
            or shortcut_rows[0].type != "Page"
            or shortcut_rows[0].link_to != PAGE
        ):
            frappe.throw(
                "SIG Petty Cash Invoice Review Board shortcut changed; "
                "refusing to remove an unexpected link."
            )
        workspace.set(
            "shortcuts",
            [row for row in workspace.shortcuts if row.name != shortcut_rows[0].name],
        )
        changed = True

    content = workspace.content or "[]"
    try:
        blocks = json.loads(content) if isinstance(content, str) else content
    except (TypeError, ValueError):
        frappe.throw("SIG Petty Cash Workspace content is not valid JSON.")

    if not isinstance(blocks, list):
        frappe.throw("SIG Petty Cash Workspace content is not a block list.")

    duplicate_blocks = [
        block
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") == "shortcut"
        and isinstance(block.get("data"), dict)
        and block["data"].get("shortcut_name") == SHORTCUT_LABEL
    ]
    if len(duplicate_blocks) > 1:
        frappe.throw(
            "SIG Petty Cash Workspace has multiple Invoice Review Board blocks; "
            "review the layout before cleanup."
        )
    if duplicate_blocks:
        blocks = [block for block in blocks if block not in duplicate_blocks]
        workspace.content = json.dumps(blocks, ensure_ascii=False, separators=(",", ":"))
        changed = True

    if changed:
        workspace.save(ignore_permissions=True)

    if any(row.label == SHORTCUT_LABEL for row in workspace.shortcuts):
        frappe.throw("Invoice Review Board shortcut row remains on SIG Petty Cash.")
    if any(
        isinstance(block, dict)
        and block.get("type") == "shortcut"
        and isinstance(block.get("data"), dict)
        and block["data"].get("shortcut_name") == SHORTCUT_LABEL
        for block in blocks
    ):
        frappe.throw("Invoice Review Board layout block remains on SIG Petty Cash.")
