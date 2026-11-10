"""Remove an old malformed Select default without changing actual references."""
import frappe

LEGACY_VALUE = r"\nPurchase Order\nPurchase Invoice"


def execute():
    # The former DocType JSON encoded literal backslash-n characters in the
    # options, so Frappe saved the entire string as its first/default option.
    # Only empty references can be safely cleared automatically.
    anomalous = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabSNB Movement Review` WHERE payment_reference_doctype=%s "
        "AND COALESCE(payment_reference, '') != ''", (LEGACY_VALUE,),
    )[0][0]
    if anomalous:
        frappe.throw("Legacy bank router reference types have linked records; review them before migration.")
    frappe.db.sql(
        "UPDATE `tabSNB Movement Review` SET payment_reference_doctype='' "
        "WHERE payment_reference_doctype=%s AND COALESCE(payment_reference, '') = ''", (LEGACY_VALUE,),
    )
