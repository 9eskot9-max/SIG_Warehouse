"""Disable the live-only daily onboarding refresh after app ownership is installed."""

import frappe


SCRIPT_NAME = "SIG HR Onboarding - Daily refresh"


def execute():
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        return

    script = frappe.get_doc("Server Script", SCRIPT_NAME)
    if script.script_type != "Scheduler Event":
        frappe.throw(
            "SIG HR daily refresh migration stopped: the named Server Script is not a Scheduler Event."
        )

    if not script.disabled:
        script.disabled = 1
        script.save(ignore_permissions=True)

    frappe.clear_cache(doctype="Server Script")
    disabled = frappe.db.get_value("Server Script", SCRIPT_NAME, "disabled")
    if int(disabled or 0) != 1:
        frappe.throw("SIG HR daily refresh migration failed its disabled-state readback.")
