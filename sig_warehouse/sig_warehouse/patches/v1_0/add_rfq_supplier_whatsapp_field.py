"""Add the WhatsApp destination directly to each native RFQ supplier row."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Request for Quotation Supplier": [{
        "fieldname": "custom_whatsapp_number",
        "label": "WhatsApp Number",
        "fieldtype": "Data",
        "options": "Phone",
        "insert_after": "contact",
        "in_list_view": 1,
        "allow_on_submit": 1,
        "no_copy": 1,
        "description": "Enter the supplier's WhatsApp number, including country code. Saving creates or updates the supplier's WhatsApp Contact.",
    }]}, update=True)
