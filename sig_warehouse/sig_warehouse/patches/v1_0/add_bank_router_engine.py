"""Seed Bank Router Settings and the holding Customer. Idempotent: never overwrites a value that is already set."""
import frappe

COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"
HOLDING_CUSTOMER = "Unidentified Receipts"
# Statement account number -> chart account number, as the SNB importer already maps them.
SNB_ACCOUNTS = (("23659568000109", "13121", "SNB 109"), ("01400010326605", "13123", "SNB 26605"))
CATEGORIES = (("PROJECT_OPERATING_COST", "5130"), ("CONTRACTING", "5130"), ("MAINTENANCE", "51312"), ("MATERIAL_SUPPLY", "5121"),
              ("EQUIPMENT_RENTAL", "51210"), ("LOGISTICS", "51311"), ("IT_TELECOM", "5141"))


def _account(number):
    return frappe.db.get_value("Account", {"account_number": number, "company": COMPANY, "is_group": 0}, "name") or ""


def execute():
    if not frappe.db.exists("Customer", HOLDING_CUSTOMER):
        frappe.get_doc({"doctype": "Customer", "customer_name": HOLDING_CUSTOMER, "customer_type": "Company",
                        "customer_group": "Commercial", "territory": "Saudi Arabia",
                        "custom_country": "Saudi Arabia"}).insert(ignore_permissions=True)
    settings = frappe.get_doc("Bank Router Settings")
    known = {row.account_number for row in settings.bank_accounts or []}
    for number, gl, label in SNB_ACCOUNTS:
        account = _account(gl)
        if account and number not in known:
            settings.append("bank_accounts", {"bank": "SNB", "label": label, "account_number": number, "gl_account": account})
    have = {str(row.code).upper() for row in settings.categories or []}
    for code, number in CATEGORIES:
        if code not in have and _account(number):
            settings.append("categories", {"code": code, "label": code.replace("_", " ").title(), "expense_account": _account(number)})
    for field, value in (("holding_customer", HOLDING_CUSTOMER if frappe.db.exists("Customer", HOLDING_CUSTOMER) else ""),
                         ("holding_supplier", "Collective" if frappe.db.exists("Supplier", "Collective") else ""),
                         ("default_expense_account", _account("5130")), ("fee_account", _account("538"))):
        if value and not settings.get(field):
            settings.set(field, value)
    settings.auto_draft_enabled = settings.auto_draft_enabled or 0
    settings.save(ignore_permissions=True)
    frappe.db.commit()
