import frappe
from frappe.model.document import Document
from sig_warehouse.sig_accounting.bank_router.business_routes import ROUTES


class BankCounterparty(Document):
    def validate(self):
        if not getattr(self.flags, "bank_router_write", False):
            frappe.throw("Use the Bank Router to change counterparties.", frappe.PermissionError)
        if self.is_company and (self.customer or self.supplier):
            frappe.throw("Our own company cannot also be a Customer or Supplier counterparty.")
        seen = set()
        for route in self.get("confirmed_routes") or []:
            if ROUTES.get(route.route) != route.direction:
                frappe.throw("The confirmed route is not valid for this movement direction.")
            key = (route.direction, (route.purpose or "").strip().upper())
            if key in seen:
                frappe.throw("Only one confirmed route is allowed for each purpose and direction.")
            seen.add(key)
            if route.party_type and route.party_type not in ("Customer", "Supplier"):
                frappe.throw("A confirmed route party must be a Customer or Supplier.")
            if bool(route.party_type) != bool(route.party):
                frappe.throw("A confirmed party requires both its type and name.")
