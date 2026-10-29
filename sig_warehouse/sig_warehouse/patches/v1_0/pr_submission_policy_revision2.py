"""Apply the current PR submit validator after its earlier patch was already recorded."""
import hashlib

import frappe

from sig_warehouse.sig_warehouse.patches.v1_0.pr_owner_submit_limit import SCRIPT


SCRIPT_NAME = "sig_pr_threshold_validator"
PRIOR_SHA256 = "0ec5c82680bcf7a73f8c86be8301d5e9ca9bea1c2abe4657321fe9067a4fa8e5"
TARGET_SHA256 = hashlib.sha256(SCRIPT.encode("utf-8")).hexdigest()


def execute():
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        frappe.throw("Purchase Receipt submit validator is missing; review before migration.")
    doc = frappe.get_doc("Server Script", SCRIPT_NAME)
    if doc.script_type != "DocType Event" or doc.disabled or doc.reference_doctype != "Purchase Receipt" or doc.doctype_event != "Before Submit":
        frappe.throw("Purchase Receipt submit validator configuration changed; review before migration.")
    source = doc.script or ""
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest == TARGET_SHA256:
        return
    if digest != PRIOR_SHA256:
        frappe.throw("Purchase Receipt submit validator changed; review before migration.")
    doc.script = SCRIPT
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Server Script")
    saved = frappe.get_doc("Server Script", SCRIPT_NAME)
    if hashlib.sha256((saved.script or "").encode("utf-8")).hexdigest() != TARGET_SHA256:
        frappe.throw("Purchase Receipt submit validator read-back did not match the intended policy.")
