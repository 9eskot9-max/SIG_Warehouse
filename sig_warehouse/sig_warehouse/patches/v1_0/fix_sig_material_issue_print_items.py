"""Fix dictionary access in the live SIG Material Issue print format."""

import frappe

FORMAT_NAME = "SIG Material Issue"
BROKEN_EXPRESSION = "_d.items"
FIXED_EXPRESSION = '_d.get("items")'
EXPECTED_OCCURRENCES = 3


def repair_html(html):
    """Return a safely repaired template or raise if its shape is unexpected."""
    count = html.count(BROKEN_EXPRESSION)
    if count == 0:
        return html
    if count != EXPECTED_OCCURRENCES:
        raise ValueError(
            f"Expected {EXPECTED_OCCURRENCES} broken item references; found {count}."
        )
    return html.replace(BROKEN_EXPRESSION, FIXED_EXPRESSION)


def execute():
    if not frappe.db.exists("Print Format", FORMAT_NAME):
        return

    doc = frappe.get_doc("Print Format", FORMAT_NAME)
    if doc.doc_type != "Stock Entry":
        frappe.throw(
            f"{FORMAT_NAME} is configured for {doc.doc_type}, not Stock Entry; "
            "review it before migration."
        )

    try:
        repaired_html = repair_html(doc.html or "")
    except ValueError as exc:
        frappe.throw(f"Cannot safely repair {FORMAT_NAME}: {exc}")

    if repaired_html == (doc.html or ""):
        return

    doc.html = repaired_html
    doc.save(ignore_permissions=True)