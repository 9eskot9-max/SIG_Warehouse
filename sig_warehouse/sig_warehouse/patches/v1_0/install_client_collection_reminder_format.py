"""Install the private, ERP-rendered PDF format for client collection drafts."""

from pathlib import Path

import frappe


PRINT_FORMAT = "SIG Client Payment Reminder"


def execute():
    html_path = Path(frappe.get_app_path("sig_warehouse")) / "sig_accounting" / "doctype" / "sig_client_collection_draft" / "print_format" / "sig_client_payment_reminder.html"
    if not html_path.is_file():
        frappe.throw("Client payment reminder print source is missing; refusing to install an empty format.")
    values = {
        "doc_type": "SIG Client Collection Draft",
        "print_format_type": "Jinja",
        "custom_format": 1,
        "standard": "No",
        "disabled": 0,
        "html": html_path.read_text(encoding="utf-8-sig"),
        "module": "SIG Accounting",
    }
    if frappe.db.exists("Print Format", PRINT_FORMAT):
        frappe.db.set_value("Print Format", PRINT_FORMAT, values)
    else:
        frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT, **values}).insert(ignore_permissions=True)
    frappe.make_property_setter({
        "doctype": "SIG Client Collection Draft",
        "doctype_or_field": "DocType",
        "property": "default_print_format",
        "value": PRINT_FORMAT,
        "property_type": "Data",
    })
