"""Add the optional PO-scoped Excel CSV label to canonical Project records."""
import frappe


def execute():
    fieldname = "custom_excel_csv_alias"
    existing = frappe.db.get_value("Custom Field", {"dt": "Project", "fieldname": fieldname}, "name")
    if existing:
        field = frappe.get_doc("Custom Field", existing)
        if field.fieldtype != "Data" or field.label != "Excel CSV Alias":
            frappe.throw("Project Excel CSV Alias field exists with an unexpected definition; review it before migration.")
        return

    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Project",
        "fieldname": fieldname,
        "label": "Excel CSV Alias",
        "fieldtype": "Data",
        "length": 140,
        "insert_after": "custom_default_tawal_contact",
        "description": "Optional label for legacy Excel CSV routing. ERP Project and PO remain the canonical identity.",
        "no_copy": 1,
    }).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Project")
