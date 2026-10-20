"""Add Finance-owned Journal Entry fields for petty-cash funding cycles."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELDS = [
    {"fieldname": "custom_pc_funding_section", "label": "Petty Cash Funding",
     "fieldtype": "Section Break", "insert_after": "custom_pc_request_digest", "collapsible": 1},
    {"fieldname": "custom_pc_top_up", "label": "Petty Cash Top-up",
     "fieldtype": "Check", "insert_after": "custom_pc_funding_section",
     "description": "Finance designation only. A marked bank transfer starts an employee petty-cash cycle."},
    {"fieldname": "custom_pc_transfer_category", "label": "Transfer Category",
     "fieldtype": "Data", "insert_after": "custom_pc_top_up", "read_only": 1,
     "description": "Category captured by transfer automation, for example XXPC."},
    {"fieldname": "custom_pc_employee", "label": "Funded Employee", "fieldtype": "Link",
     "options": "Employee", "insert_after": "custom_pc_transfer_category",
     "depends_on": "eval:doc.custom_pc_top_up", "mandatory_depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_funding_date", "label": "Funding Date", "fieldtype": "Date",
     "insert_after": "custom_pc_employee", "depends_on": "eval:doc.custom_pc_top_up",
     "mandatory_depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_funding_source", "label": "Funding Source", "fieldtype": "Select",
     "options": "\nBank Statement\nManual Finance", "insert_after": "custom_pc_funding_date",
     "depends_on": "eval:doc.custom_pc_top_up", "mandatory_depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_bank_txn_id", "label": "Bank Transaction ID", "fieldtype": "Data",
     "insert_after": "custom_pc_funding_source", "depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_bank_journal_number", "label": "Bank Journal Number", "fieldtype": "Data",
     "insert_after": "custom_pc_bank_txn_id", "depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_statement_key", "label": "Statement Idempotency Key", "fieldtype": "Data",
     "insert_after": "custom_pc_bank_journal_number", "read_only": 1,
     "depends_on": "eval:doc.custom_pc_top_up"},
    {"fieldname": "custom_pc_funding_source_key", "label": "Funding Source Key", "fieldtype": "Data",
     "insert_after": "custom_pc_statement_key", "read_only": 1,
     "depends_on": "eval:doc.custom_pc_top_up"},
]


def execute():
    if not frappe.db.exists("DocType", "Journal Entry"):
        frappe.throw("Journal Entry is required before adding petty-cash funding fields.")
    for field in FIELDS:
        name = "Journal Entry-" + field["fieldname"]
        if not frappe.db.exists("Custom Field", name):
            continue
        existing = frappe.get_doc("Custom Field", name)
        for key in ("fieldtype", "options", "insert_after", "read_only", "permlevel",
                    "depends_on", "mandatory_depends_on", "unique", "no_copy"):
            default = 0 if key in ("read_only", "permlevel", "unique", "no_copy") else ""
            if (existing.get(key) or default) != (field.get(key) or default):
                frappe.throw("Journal Entry funding field contract differs; review before migration: " + name)
    create_custom_fields({"Journal Entry": FIELDS}, update=True)
    frappe.clear_cache(doctype="Journal Entry")
