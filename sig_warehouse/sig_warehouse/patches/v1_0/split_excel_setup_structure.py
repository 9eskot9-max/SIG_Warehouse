"""Quarantine the v1 false joins in revision history; publish independent v2 lists.

No permission writers, directory changes, guessed links or business-record edits.
The first v2 publication deliberately leaves profiles/contacts/assignments empty.
An incomplete RV80 bundle preserves the existing workbook until a genuine seed
of its independent Builder lists is imported. Running this patch twice is a no-op.
"""
import frappe


def execute():
    from sig_warehouse.sig_operations.excel_setup import _state, _publish
    from sig_warehouse.sig_operations.excel_setup_contract import is_legacy, upgrade_legacy

    if not frappe.db.exists("DocType", "SIG Excel Setup"):
        return
    doc, datasets = _state(lock=True)
    if not is_legacy(datasets):
        return
    _publish(upgrade_legacy(datasets), int(doc.revision or 0))
