"""Default new Items to the ERP-backed RV80 material catalogue."""
import frappe


def execute():
    field = frappe.db.get_value(
        "Custom Field", {"dt": "Item", "fieldname": "custom_wh_catalogue"}, "name"
    )
    if not field:
        field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Item",
            "fieldname": "custom_wh_catalogue",
            "label": "In WH / RV80 material catalogue",
            "fieldtype": "Check",
            "insert_after": "disabled",
            "default": "1",
            "description": "Ticked items are carried to RV80's WHC material list by the RV80 catalogue refresh. WH code = item code.",
        }).insert(ignore_permissions=True).name
    elif frappe.db.get_value("Custom Field", field, "default") != "1":
        frappe.db.set_value("Custom Field", field, "default", "1", update_modified=False)

    frappe.clear_cache(doctype="Item")
