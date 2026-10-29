"""Ensure PI-rate stock valuation is persisted in Buying Settings."""
import frappe


def execute():
    if not frappe.db.exists("Role", "Accounts Manager"):
        frappe.throw("Accounts Manager role is missing; review invoice price authority before migration.")
    settings = frappe.get_single("Buying Settings")
    if settings.maintain_same_rate != 1 or settings.maintain_same_rate_action != "Stop":
        frappe.throw("Buying Settings same-rate control changed; review before migration.")
    if settings.role_to_override_stop_action not in (None, "", "Accounts Manager"):
        frappe.throw("Buying Settings override role changed; review before migration.")
    if settings.get("set_landed_cost_based_on_purchase_invoice_rate") not in (None, 0, 1):
        frappe.throw("Buying Settings PI-rate valuation value is unexpected; review before migration.")

    frappe.db.set_single_value("Buying Settings", "role_to_override_stop_action", "Accounts Manager")
    frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 1)
    frappe.clear_cache(doctype="Buying Settings")

    saved_role = frappe.db.get_single_value("Buying Settings", "role_to_override_stop_action")
    saved_valuation = frappe.db.get_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate")
    if saved_role != "Accounts Manager" or int(saved_valuation or 0) != 1:
        frappe.throw("Buying Settings true-up policy failed its post-save read-back.")
