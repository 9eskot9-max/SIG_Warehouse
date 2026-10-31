"""v16: file the SIG HR workspace under the SIG HR module so its dock entry shows on ERPNext's rail.

A dock pin takes its shell from the module of the workspace it opens. SIG HR sat in ERPNext/HRMS's
"HR" module (owned by hrms, which does not mount on ERPNext's rail), so the pin was dropped.
"""
import frappe


def execute():
    if frappe.db.exists("Workspace", "SIG HR") and frappe.db.exists("Module Def", "SIG HR"):
        frappe.db.set_value("Workspace", "SIG HR", "module", "SIG HR", update_modified=False)
        frappe.clear_cache()
