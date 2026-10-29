"""Allow Finance to book final invoice prices against provisional receipts."""
import frappe
import erpnext


EXPECTED = {
    "maintain_same_rate": 1,
    "maintain_same_rate_action": "Stop",
    "role_to_override_stop_action": "",
    "set_landed_cost_based_on_purchase_invoice_rate": 0,
}
TARGET = {
    "maintain_same_rate": 1,
    "maintain_same_rate_action": "Stop",
    "role_to_override_stop_action": "Accounts Manager",
    "set_landed_cost_based_on_purchase_invoice_rate": 1,
}


def execute():
    version = tuple(int(part) for part in erpnext.__version__.split(".")[:3])
    if version < (15, 123, 0):
        frappe.throw("Purchase Invoice rate-based valuation requires ERPNext v15.123.0 or later for the partial-billing fixes.")
    settings = frappe.get_single("Buying Settings")
    current = {field: (settings.get(field) or "") for field in EXPECTED}
    expected = {field: (value or "") for field, value in EXPECTED.items()}
    target = {field: (value or "") for field, value in TARGET.items()}
    if current == target:
        return
    if current != expected:
        frappe.throw("Buying Settings rate policy changed; review before migration.")
    if not frappe.db.exists("Role", "Accounts Manager"):
        frappe.throw("Accounts Manager role is missing; review invoice price authority before migration.")
    for field, value in TARGET.items():
        settings.set(field, value)
    settings.save(ignore_permissions=True)
