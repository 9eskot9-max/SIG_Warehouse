import frappe
from frappe.model.document import Document


class BankCounterparty(Document):
    def validate(self):
        if not getattr(self.flags, "bank_router_write", False):
            frappe.throw("Use the Bank Router to change counterparties.", frappe.PermissionError)
        if self.is_company and (self.customer or self.supplier):
            frappe.throw("Our own company cannot also be a Customer or Supplier counterparty.")
