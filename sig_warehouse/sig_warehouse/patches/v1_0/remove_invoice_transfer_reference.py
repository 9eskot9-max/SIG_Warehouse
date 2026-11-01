"""Remove the misleading quote-transfer instruction from the SIG invoice print."""

import frappe


PRINT_FORMAT = "SIG Tax Invoice (Infographic)"
REFERENCE_LINE = '<p><b>Reference:</b> Quote {{ doc.name }} on your transfer.</p>'


def execute():
    """Remove only the obsolete instruction, preserving the rest of the live format."""
    if not frappe.db.exists("Print Format", PRINT_FORMAT):
        frappe.throw(
            f"Expected existing Sales Invoice print format {PRINT_FORMAT!r}; "
            "refusing to mark the invoice wording update complete."
        )

    doc = frappe.get_doc("Print Format", PRINT_FORMAT)
    if doc.doc_type != "Sales Invoice" or not doc.custom_format:
        frappe.throw(
            f"Print Format {PRINT_FORMAT!r} is no longer the expected custom Sales Invoice format."
        )

    html = doc.html or ""
    if REFERENCE_LINE not in html:
        # Idempotent when the exact unwanted wording has already been removed.
        if "Quote {{ doc.name }} on your transfer." not in html:
            return
        frappe.throw(
            f"Print Format {PRINT_FORMAT!r} contains a changed version of the unwanted wording; "
            "manual review is required before migration."
        )

    doc.db_set("html", html.replace(REFERENCE_LINE, "", 1))
