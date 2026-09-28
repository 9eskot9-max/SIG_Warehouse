import frappe


def execute():
    """Register the app-owned Accounting module before assigning its Desk Page."""
    module_name = "SIG Accounting"

    if not frappe.db.exists("Module Def", module_name):
        frappe.get_doc(
            {
                "doctype": "Module Def",
                "module_name": module_name,
                "app_name": "sig_warehouse",
            }
        ).insert(ignore_permissions=True)

    if frappe.db.exists("Page", "finance-workbench"):
        frappe.db.set_value(
            "Page",
            "finance-workbench",
            "module",
            module_name,
            update_modified=False,
        )
