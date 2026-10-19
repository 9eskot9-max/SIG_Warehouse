"""Install the receipt->JE contract; preserve all existing accounting documents and grants."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


ORIGIN_FIELDS = [
    {"fieldname": "custom_pc_receipt", "label": "Petty Cash Receipt", "fieldtype": "Link",
     "options": "SIG PC Transaction", "insert_after": "user_remark", "read_only": 1,
     "unique": 1, "no_copy": 1},
    {"fieldname": "custom_pc_source_key", "label": "PC Source Fingerprint", "fieldtype": "Data",
     "insert_after": "custom_pc_receipt", "read_only": 1, "hidden": 1,
     "unique": 1, "no_copy": 1, "length": 64},
    {"fieldname": "custom_pc_request_digest", "label": "PC Review Request Fingerprint", "fieldtype": "Data",
     "insert_after": "custom_pc_source_key", "read_only": 1, "hidden": 1,
     "no_copy": 1, "length": 64},
]
OLD_ENDPOINTS = ("sig_pc_close_transaction", "sig_pc_create_pc_journal_draft", "sig_pc_reject_transaction")


def execute():
    if not frappe.db.exists("DocType", "SIG PC Transaction"):
        frappe.throw("SIG PC Transaction is required before enabling Journal Entry clearance.")
    for field in ORIGIN_FIELDS:
        name = "Journal Entry-" + field["fieldname"]
        if frappe.db.exists("Custom Field", name):
            old = frappe.get_doc("Custom Field", name)
            for key in ("fieldtype", "options", "unique", "no_copy", "read_only", "hidden"):
                default = 0 if key in ("unique", "no_copy", "read_only", "hidden") else ""
                if (old.get(key) or default) != (field.get(key) or default):
                    frappe.throw("PC journal field contract differs; review before migration: " + name)
    scripts = []
    for name in OLD_ENDPOINTS:
        if frappe.db.exists("Server Script", name):
            script = frappe.get_doc("Server Script", name)
            if script.script_type != "API" or script.api_method != name:
                frappe.throw("Unexpected legacy PC Server Script definition: " + name)
            scripts.append(script)
    client = None
    if frappe.db.exists("Client Script", "SIG PC Transaction Review"):
        script = frappe.get_doc("Client Script", "SIG PC Transaction Review")
        if script.dt != "SIG PC Transaction":
            frappe.throw("Unexpected PC Client Script DocType; refusing to disable it.")
        client = script
    # Finish contract discovery before the first DDL or persisted change.
    create_custom_fields({"Journal Entry": ORIGIN_FIELDS}, update=True)
    for script in scripts:
        if not script.disabled:
            script.disabled = 1
            script.save(ignore_permissions=True)
    if client and client.enabled:
        client.enabled = 0
        client.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Journal Entry")
    frappe.clear_cache(doctype="SIG PC Transaction")
    frappe.cache().delete_value("server_script_map")
