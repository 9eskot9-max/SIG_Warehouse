import frappe
from frappe import _
from frappe.model.document import Document


class SIGWarehouseReconciliation(Document):
    def validate(self):
        if self.is_new():
            return
        old = frappe.db.get_value(
            "SIG Warehouse Reconciliation", self.name,
            ["state", "wh_snapshot_sha256", "erp_line_count", "wh_line_count", "matched_line_count", "mismatch_line_count"],
            as_dict=True,
        )
        protected = any(str(old.get(field) or "") != str(self.get(field) or "") for field in (
            "state", "wh_snapshot_sha256", "erp_line_count", "wh_line_count", "matched_line_count", "mismatch_line_count",
        ))
        if protected and not frappe.flags.get("sig_warehouse_reconciliation_transition"):
            frappe.throw(_("Reconciliation state and measured totals can only be changed through the approved reconciliation actions."))
