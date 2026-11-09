import frappe
from frappe.model.document import Document


class BankCounterpartyIdentifier(Document):
    def validate(self):
        if not getattr(self.flags, "bank_router_write", False):
            frappe.throw("Use the Bank Router to change counterparty identifiers.", frappe.PermissionError)
