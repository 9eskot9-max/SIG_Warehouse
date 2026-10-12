import frappe


def execute():
    """Keep the Page module aligned with its app-owned source directory."""
    module_name = "SIG Operations"

    if not frappe.db.exists("Module Def", module_name):
        frappe.get_doc(
            {
                "doctype": "Module Def",
                "module_name": module_name,
                "app_name": "sig_warehouse",
            }
        ).insert(ignore_permissions=True)

    if frappe.db.exists("Page", "operations-workbench"):
        frappe.db.set_value(
            "Page",
            "operations-workbench",
            "module",
            module_name,
            update_modified=False,
        )
