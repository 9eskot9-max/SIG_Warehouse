"""v16: realign the stale `project-progress` Page record with the app definition.

Frappe v16's Page.load_assets lists the module's page folder without checking that it exists.
The database record (created 2026-09-20) points at ERPNext's Projects module with standard = No,
so opening /desk/project-progress raised FileNotFoundError. The app ships the page under the
SIG Warehouse module; Frappe's file sync skipped it because the database record is newer.
"""
import frappe

PAGE = "project-progress"
MODULE = "SIG Warehouse"


def execute():
    if not frappe.db.exists("Page", PAGE):
        return
    current = frappe.db.get_value("Page", PAGE, ["module", "standard"], as_dict=True)
    if current.module == MODULE and current.standard == "Yes":
        return
    frappe.db.set_value("Page", PAGE, {"module": MODULE, "standard": "Yes"}, update_modified=False)
    frappe.clear_cache()
