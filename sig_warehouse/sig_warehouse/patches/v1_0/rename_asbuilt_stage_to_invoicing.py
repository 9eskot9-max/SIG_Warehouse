"""Rename the fourth Operations stage consistently in metadata and open cycles."""

import frappe


DOCTYPE = "SIG Site Cycle"
OLD_STAGE = "4 - As-Built"
NEW_STAGE = "4 - Invoicing"
STAGE_OPTIONS = "1 - Initial\n2 - Plan\n3 - Handover\n4 - Invoicing\n5 - Closed"
SERVER_SCRIPT = "register_evidence_event"


def _update_evidence_writer():
    if not frappe.db.exists("Server Script", SERVER_SCRIPT):
        frappe.throw("Cannot rename Operations Stage 4: register_evidence_event is missing.")

    script = frappe.db.get_value("Server Script", SERVER_SCRIPT, "script") or ""
    old = "stage = '4 - As-Built'"
    new = "stage = '4 - Invoicing'"
    old_count, new_count = script.count(old), script.count(new)
    if old_count == 1 and new_count == 0:
        frappe.db.set_value("Server Script", SERVER_SCRIPT, "script", script.replace(old, new, 1))
    elif old_count == 0 and new_count == 1:
        return
    else:
        frappe.throw("Evidence stage logic changed; refusing an unreviewed Server Script rewrite.")


def execute():
    """Rename Stage 4 while retaining explicit closure and overdue state."""
    _update_evidence_writer()

    if not frappe.db.exists("DocType", DOCTYPE):
        frappe.throw("Cannot rename Operations Stage 4: SIG Site Cycle is missing.")

    doctype = frappe.get_doc("DocType", DOCTYPE)
    stage_field = next((field for field in doctype.fields if field.fieldname == "stage"), None)
    if not stage_field or stage_field.fieldtype != "Select":
        frappe.throw("Cannot rename Operations Stage 4: SIG Site Cycle.stage is not a Select field.")

    metadata_changed = stage_field.options != STAGE_OPTIONS
    if metadata_changed:
        stage_field.options = STAGE_OPTIONS
        doctype.save(ignore_permissions=True)

    updated = frappe.db.sql(
        """SELECT name FROM `tabSIG Site Cycle`
           WHERE IFNULL(terminal, 0) = 0 AND stage = %s
             AND (ho_at IS NOT NULL OR invoice_at IS NOT NULL)""",
        (OLD_STAGE,),
        as_dict=True,
    )
    for row in updated:
        frappe.db.set_value(DOCTYPE, row.name, "stage", NEW_STAGE, update_modified=False)

    board_updated = False
    board_name = "SIG Cycle Board"
    if frappe.db.exists("Kanban Board", board_name):
        board = frappe.get_doc("Kanban Board", board_name)
        renamed_columns = 0
        for column in board.columns:
            if column.column_name == OLD_STAGE:
                column.column_name = NEW_STAGE
                renamed_columns += 1
        if renamed_columns:
            board.save(ignore_permissions=True)
            board_updated = True

    frappe.clear_cache(doctype=DOCTYPE)
    frappe.logger("sig_warehouse").info(
        "Operations Stage 4 renamed to Invoicing; updated %s open evidence-backed cycles, "
        "metadata_changed=%s, kanban_updated=%s",
        len(updated), metadata_changed, board_updated,
    )
