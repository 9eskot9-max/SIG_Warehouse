"""Ensure every registered document has a hidden verification token field.

Existing Custom Fields are adopted/updated; native fields are validated and left in place.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from sig_warehouse.sig_verify.registry import TOKEN_FIELD, VERIFIABLE, token_field_spec


def execute():
    custom_fields = {}
    for doctype in VERIFIABLE:
        if not frappe.db.exists("DocType", doctype):
            continue

        spec = token_field_spec(doctype)
        custom_name = frappe.db.get_value(
            "Custom Field", {"dt": doctype, "fieldname": TOKEN_FIELD}, "name"
        )
        if custom_name:
            custom_fields[doctype] = [spec]
            continue

        native = frappe.get_meta(doctype).get_field(TOKEN_FIELD)
        if native:
            expected = {
                "fieldtype": "Data",
                "hidden": 1,
                "read_only": 1,
                "no_copy": 1,
                "allow_on_submit": 1,
                "print_hide": 1,
            }
            mismatches = [
                key for key, value in expected.items()
                if key != "fieldtype" and int(getattr(native, key, 0) or 0) != value
            ]
            if native.fieldtype != expected["fieldtype"]:
                mismatches.append("fieldtype")
            if mismatches:
                frappe.throw(
                    f"{doctype}.{TOKEN_FIELD} exists as a native field with an unexpected "
                    f"definition ({', '.join(sorted(set(mismatches)))}); review before migration."
                )
            continue

        custom_fields[doctype] = [spec]

    if custom_fields:
        create_custom_fields(custom_fields)
