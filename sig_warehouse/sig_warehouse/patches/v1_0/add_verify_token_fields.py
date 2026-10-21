"""Create the hidden verification token field on every doctype registered in sig_verify.

Idempotent: create_custom_fields updates the field when it already exists (the Quotation field was
first created live by the API harness, so this adopts it).
"""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from sig_warehouse.sig_verify.registry import VERIFIABLE, token_field_spec


def execute():
    create_custom_fields({doctype: [token_field_spec(doctype)] for doctype in VERIFIABLE})
