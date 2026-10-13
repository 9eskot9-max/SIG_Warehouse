import frappe


def execute():
    """Reload the standard Page's app-owned script after an app deployment."""
    if frappe.db.exists("Page", "operations-workbench"):
        frappe.clear_cache(doctype="Page")
