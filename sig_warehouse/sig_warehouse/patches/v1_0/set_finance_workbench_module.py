import frappe


def execute():
    """Keep the finance workbench classified with accounting, not warehouse."""
    if frappe.db.exists("Page", "finance-workbench"):
        frappe.db.set_value(
            "Page",
            "finance-workbench",
            "module",
            "Accounts",
            update_modified=False,
        )
