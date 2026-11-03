"""Customer/supplier addresses must be attached to a party.

An Address created from the plain Address list is blank in its Links table, so it never shows on the
customer's Address & Contact tab. This keeps a read-only "Linked To" summary that the Address list shows,
and refuses a new Address that links to nothing when it is saved from the Desk.
"""
import frappe
from frappe import _

SUMMARY_FIELD = "custom_linked_party"


def linked_summary(doc):
    rows = [f"{row.link_doctype}: {row.link_name}" for row in (doc.get("links") or []) if row.link_doctype and row.link_name]
    return "; ".join(rows)[:140]


def validate_address(doc, method=None):
    if doc.meta.has_field(SUMMARY_FIELD):
        doc.set(SUMMARY_FIELD, linked_summary(doc))
    flags = frappe.flags
    if not doc.is_new() or getattr(flags, "in_import", False) or getattr(flags, "in_patch", False) \
            or getattr(flags, "in_install", False) or getattr(flags, "in_migrate", False) \
            or getattr(flags, "in_test", False) or not getattr(frappe.local, "request", None):
        return
    if not linked_summary(doc):
        frappe.throw(_("Link this address to a Customer or Supplier: open it from the Customer's Address & Contact tab, "
                       "or add the Customer in the Links table."), title=_("Address has no party"))
