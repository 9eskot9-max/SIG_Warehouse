"""Create the SIG Letters Module Def before the model sync imports the new DocTypes (pre_model_sync)."""
import frappe


def execute():
    if not frappe.db.exists("Module Def", "SIG Letters"):
        frappe.get_doc({"doctype": "Module Def", "module_name": "SIG Letters", "app_name": "sig_warehouse"}).insert(
            ignore_permissions=True
        )
