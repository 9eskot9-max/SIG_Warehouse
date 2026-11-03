"""Add a read-only "Linked To" column to Address (shown in the list) and fill it for existing addresses."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from sig_warehouse.sig_warehouse.address_links import SUMMARY_FIELD


def execute():
    if not frappe.db.exists("Custom Field", {"dt": "Address", "fieldname": SUMMARY_FIELD}):
        create_custom_field("Address", {
            "fieldname": SUMMARY_FIELD, "label": "Linked To", "fieldtype": "Data", "read_only": 1,
            "in_list_view": 1, "in_standard_filter": 0, "search_index": 0, "insert_after": "address_title",
            "no_copy": 1, "print_hide": 1,
        })
    rows = frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "parentfield": "links"},
                          fields=["parent", "link_doctype", "link_name"], order_by="idx asc", limit_page_length=0)
    summary = {}
    for row in rows:
        summary.setdefault(row.parent, []).append(f"{row.link_doctype}: {row.link_name}")
    for name in frappe.get_all("Address", pluck="name", limit_page_length=0):
        frappe.db.set_value("Address", name, SUMMARY_FIELD, "; ".join(summary.get(name, []))[:140], update_modified=False)
    frappe.clear_cache(doctype="Address")
