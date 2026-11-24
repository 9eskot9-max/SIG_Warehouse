"""Close the cycles still open behind submitted Tawal invoices (left open since the 9 November allocation rewrite)."""

import frappe

from sig_warehouse.sig_warehouse.tawal_invoice_evidence import close_invoice_cycle

TAWAL = "Telecommunications Towers Company / Tawal"
BATCH = "TAWAL-INVOICE-CLOSE-BACKFILL-20261124"


def execute():
    if not frappe.db.exists("DocType", "SIG Tawal Invoice Link"):
        return
    links = frappe.get_all("SIG Tawal Invoice Link", filters={"cycle": ["is", "set"], "sales_invoice": ["is", "set"]},
                           fields=["cycle", "sales_invoice", "source_row_key"],
                           order_by="sales_invoice asc, source_row asc", limit_page_length=0)
    names = sorted({link.sales_invoice for link in links})
    if not names:
        return
    invoices = {row.name: row for row in frappe.get_all("Sales Invoice", filters={"name": ["in", names]},
                fields=["name", "docstatus", "customer", "custom_tawal_test"], limit_page_length=0)}
    amounts = {(row.parent, row.custom_source_row_key): row.amount for row in frappe.get_all(
        "Sales Invoice Item", filters={"parent": ["in", names]}, fields=["parent", "custom_source_row_key", "amount"],
        limit_page_length=0)}
    now, closed = frappe.utils.now(), 0
    for seq, link in enumerate(links, start=1):
        invoice = invoices.get(link.sales_invoice)
        if (not invoice or invoice.docstatus != 1 or invoice.customer != TAWAL or int(invoice.custom_tawal_test or 0)
                or not frappe.db.exists("SIG Site Cycle", link.cycle)):
            continue
        if close_invoice_cycle(link.cycle, link.sales_invoice, link.source_row_key, seq,
                               amounts.get((link.sales_invoice, link.source_row_key)), "Administrator", now, BATCH):
            closed += 1
    print(f"Closed {closed} cycles of submitted Tawal invoices")
