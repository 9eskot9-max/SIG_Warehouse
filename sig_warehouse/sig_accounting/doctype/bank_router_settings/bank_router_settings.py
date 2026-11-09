import frappe
from frappe.model.document import Document

from sig_warehouse.sig_accounting.bank_router.text import account_scope


class BankRouterSettings(Document):
    def validate(self):
        seen = set()
        for row in self.bank_accounts or []:
            row.account_scope_hash = account_scope(row.account_number)
            if not row.account_scope_hash or row.account_scope_hash in seen:
                frappe.throw("Each bank account needs a distinct, valid account number.")
            seen.add(row.account_scope_hash)
        codes = [str(row.code or "").strip().upper() for row in self.categories or []]
        if len(codes) != len(set(codes)):
            frappe.throw("Category codes must be unique.")
        for row in self.categories or []:
            row.code = str(row.code or "").strip().upper()
