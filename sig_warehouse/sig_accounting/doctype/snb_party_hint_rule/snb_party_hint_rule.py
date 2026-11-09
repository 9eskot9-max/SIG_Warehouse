import frappe
from frappe.model.document import Document


class SNBPartyHintRule(Document):
    def validate(self):
        if not getattr(self.flags, "snb_router_write", False):
            frappe.throw("Use the SNB movement router to manage party hint rules.", frappe.PermissionError)

