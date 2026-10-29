"""Move the no-PO receipt limit to submission; only the owner's accounts may exceed it."""
import hashlib

import frappe

SCRIPT_NAME = "sig_pr_threshold_validator"
PRIOR_SHA256 = "0999577531b9b84e1cc8217b4f4549689bac07e4951e76076cb1a0461e25cc68"
SCRIPT = '''# No-PO receipt policy: drafts are unrestricted by value. On submission,
# only the explicitly authorized owner accounts may post above SAR 20,000.
total = 0.0
has_po = 0
for it in doc.items:
    if it.purchase_order:
        has_po = 1
    total = total + float(it.qty or 0) * float(it.rate or 0)
if total > 20000 and not has_po:
    if frappe.session.user not in ('Administrator', '9eskot9@gmail.com'):
        frappe.throw('Only the owner can submit a receipt without a Purchase Order above SAR 20,000. You may save it as a draft for owner submission.')
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
