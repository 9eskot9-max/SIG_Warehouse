import frappe
from frappe.model.document import Document


class SigTawalPayment(Document):
    def validate(self):
        # Staged portal evidence is written only by the Tawal endpoints (tawal_router.stage_rows / process).
        if not getattr(self.flags, "tawal_router_write", False):
            frappe.throw("Use the bank router Tawal tab to create or change this record.", frappe.PermissionError)
