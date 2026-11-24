"""Clear the Employee that Frappe filled in by default on two router-created supplier payees (PERM-20261124-01).

Both payees were created on 2026-11-12 under one user's login; a single Employee User Permission became the new-document
default. Neither has a custody account, so the link never came from a petty-cash designation. Only these two named
payees are touched, and only while they still look like that.
"""

import frappe

CASES = {"4sbag2ksi6": "HR-EMP-00035", "5t8qj76n7l": "HR-EMP-00035"}


def execute():
    for name, employee in CASES.items():
        row = frappe.db.get_value("Bank Counterparty", name, ["employee", "custody_account", "supplier"], as_dict=True)
        if row and row.employee == employee and not row.custody_account and row.supplier:
            frappe.db.set_value("Bank Counterparty", name, "employee", None, update_modified=False)
