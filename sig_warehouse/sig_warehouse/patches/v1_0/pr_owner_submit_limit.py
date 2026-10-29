"""Move the no-PO receipt limit to submission; only the owner's accounts may exceed it."""
import hashlib

import frappe

SCRIPT_NAME = "sig_pr_threshold_validator"
PRIOR_SHA256 = "0999577531b9b84e1cc8217b4f4549689bac07e4951e76076cb1a0461e25cc68"
SCRIPT = '''# Draft preparation has no value ceiling. Before stock is posted, every
# received stock line needs a positive PO or provisional valuation rate. This is
# not required to equal the final supplier invoice rate. For a receipt below
# SAR 20,000, the final invoice price may arrive later; above that value, a known
# valuation is required before submission.
total = 0.0
no_po_total = 0.0
for it in doc.items:
    rate = float(it.rate or 0)
    if float(it.qty or 0) > 0 and rate <= 0:
        frappe.throw('Each received stock line needs a positive PO or provisional valuation rate before submission. A draft may remain unpriced; do not post zero-value stock.')
    line_total = float(it.qty or 0) * rate
    total = total + line_total
    if not it.purchase_order:
        no_po_total = no_po_total + line_total
supplier_window_total = no_po_total
if no_po_total > 0 and doc.supplier and doc.posting_date:
    window_start = frappe.utils.add_days(doc.posting_date, -6)
    prior_receipts = frappe.get_all('Purchase Receipt',
        filters={'supplier': doc.supplier, 'docstatus': 1,
                 'posting_date': ['between', [window_start, doc.posting_date]]},
        fields=['name'], limit_page_length=0)
    prior_names = [row.name for row in prior_receipts if row.name != doc.name]
    if prior_names:
        prior_lines = frappe.get_all('Purchase Receipt Item',
            filters={'parent': ['in', prior_names]},
            fields=['purchase_order', 'qty', 'rate'], limit_page_length=0)
        for prior in prior_lines:
            if not prior.purchase_order:
                supplier_window_total = supplier_window_total + float(prior.qty or 0) * float(prior.rate or 0)
if supplier_window_total > 20000:
    if frappe.session.user not in ('Administrator', '9eskot9@gmail.com'):
        frappe.throw("Only the owner may submit when this no-PO receipt and the same supplier's submitted no-PO receipts in the last 7 days exceed SAR 20,000. Drafts remain unrestricted; use a positive stock valuation before submission.")
'''


def execute():
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        frappe.throw("Purchase Receipt threshold script missing; review before migration.")
    doc = frappe.get_doc("Server Script", SCRIPT_NAME)
    if doc.script_type != "DocType Event" or doc.reference_doctype != "Purchase Receipt" or doc.disabled:
        frappe.throw("Purchase Receipt threshold script configuration changed; review before migration.")
    if doc.doctype_event == "Before Submit" and doc.script == SCRIPT:
        return
    digest = hashlib.sha256((doc.script or "").encode("utf-8")).hexdigest()
    if doc.doctype_event != "Before Validate" or digest != PRIOR_SHA256:
        frappe.throw("Purchase Receipt threshold script changed; review before migration.")
    doc.doctype_event = "Before Submit"
    doc.script = SCRIPT
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Server Script")
