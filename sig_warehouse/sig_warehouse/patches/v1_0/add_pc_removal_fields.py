"""Install reversible petty-cash removal metadata without changing permission matrices."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

FIELDS = [
    {"fieldname": "pc_removed", "label": "Removed from Review", "fieldtype": "Check", "default": "0", "read_only": 1, "no_copy": 1, "insert_after": "closure_status"},
    {"fieldname": "pc_removed_reason", "label": "Removal Reason", "fieldtype": "Small Text", "read_only": 1, "no_copy": 1, "insert_after": "pc_removed"},
    {"fieldname": "pc_removed_by", "label": "Removed By", "fieldtype": "Link", "options": "User", "read_only": 1, "no_copy": 1, "insert_after": "pc_removed_reason"},
    {"fieldname": "pc_removed_at", "label": "Removed At", "fieldtype": "Datetime", "read_only": 1, "no_copy": 1, "insert_after": "pc_removed_by"},
    {"fieldname": "pc_removed_prior_status", "label": "Status Before Removal", "fieldtype": "Data", "read_only": 1, "hidden": 1, "no_copy": 1, "insert_after": "pc_removed_at"},
]

def execute():
    if not frappe.db.exists("DocType", "SIG PC Transaction"):
        frappe.throw("SIG PC Transaction is required for petty-cash removal.")
    for field in FIELDS:
        name = "SIG PC Transaction-" + field["fieldname"]
        if frappe.db.exists("Custom Field", name):
            current = frappe.get_doc("Custom Field", name)
            for key in ("fieldtype", "options", "read_only", "no_copy"):
                default = 0 if key in ("read_only", "no_copy") else ""
                if (current.get(key) or default) != (field.get(key) or default):
                    frappe.throw("Existing PC removal field differs: " + name)
    status_field = frappe.get_meta("SIG PC Transaction").get_field("closure_status")
    if not status_field or status_field.fieldtype != "Select":
        frappe.throw("PC closure status must be a Select field.")
    options = [option for option in (status_field.options or "").splitlines() if option]
    if not {"Draft", "Needs Review", "Closed", "Rejected"}.issubset(options):
        frappe.throw("PC closure status options differ from the expected contract.")
    create_custom_fields({"SIG PC Transaction": FIELDS}, update=True)
    if "Removed" not in options:
        options.append("Removed")
        make_property_setter("SIG PC Transaction", "closure_status", "options", "\n".join(options), "Text")
    frappe.db.sql("UPDATE `tabSIG PC Transaction` SET pc_removed = 0 WHERE pc_removed IS NULL")
    frappe.clear_cache(doctype="SIG PC Transaction")
