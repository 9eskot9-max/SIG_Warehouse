import re

import frappe
from frappe import _
from frappe.model.document import Document


class BankRouterBiller(Document):
    def validate(self):
        code = str(self.biller_code or "").strip()
        if not re.fullmatch(r"\d{2,8}", code):
            frappe.throw(_("Enter the numeric SADAD biller code."))
        account = frappe.db.get_value("Account", self.expense_account, ["root_type", "is_group", "disabled", "company"], as_dict=True)
        if not account or account.root_type != "Expense" or account.is_group or account.disabled or account.company != "Salah Ibrahim Algain Contracting Company Ltd":
            frappe.throw(_("Select an active expense account for the company."))
        duplicate = frappe.db.exists("Bank Router Biller", {"parent": self.parent, "biller_code": code, "name": ["!=", self.name]})
        if duplicate:
            frappe.throw(_("That SADAD biller code is already mapped in these settings."))
