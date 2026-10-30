"""Add delivery history to native Request for Quotation records."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Request for Quotation": [{
        "fieldname": "custom_rfq_deliveries",
        "label": "WhatsApp Deliveries",
        "fieldtype": "Table",
        "options": "SIG Client Collection Delivery",
        "read_only": 1,
        "allow_on_submit": 1,
        "no_copy": 1,
    }]}, update=True)
