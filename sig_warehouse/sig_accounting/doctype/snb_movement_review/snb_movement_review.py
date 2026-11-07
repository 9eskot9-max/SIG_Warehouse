import frappe
from frappe.model.document import Document


class SNBMovementReview(Document):
    def validate(self):
        if not getattr(self.flags, "snb_router_write", False):
            frappe.throw("Use the SNB movement router to create or change this record.", frappe.PermissionError)
        if not self.is_new():
            before = self.get_doc_before_save()
            for field in ("source_hash", "source_key", "event_date", "source_account_tail", "direction", "amount", "currency", "source_json"):
                if before and self.get(field) != before.get(field):
                    frappe.throw("Bank source evidence is immutable: " + field)
