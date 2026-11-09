import frappe
from frappe.model.document import Document


class SNBRouterPartyApproval(Document):
    def validate(self):
        if not getattr(self.flags, "snb_router_write", False):
            frappe.throw("Use the bank movement router to manage party approvals.", frappe.PermissionError)
