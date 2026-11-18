"""Add Mohammed Algain as a designated no-PO receipt submitter above SAR 20,000."""
import hashlib

import frappe

from sig_warehouse.sig_warehouse.patches.v1_0.pr_submission_policy_revision2 import (
    SCRIPT as PRIOR_SCRIPT,
    TARGET_SHA256 as PRIOR_SHA256,
)


SCRIPT_NAME = "sig_pr_threshold_validator"

old_users = "('Administrator', '9eskot9@gmail.com')"
new_users = "('Administrator', '9eskot9@gmail.com', 'mohammed.gain@sigtele.com')"
old_message = "Only the owner may submit when this no-PO receipt and the same supplier's submitted no-PO receipts in the last 7 days exceed SAR 20,000. Drafts remain unrestricted; use a positive stock valuation before submission."
new_message = "Only an authorized approver may submit when this no-PO receipt and the same supplier's submitted no-PO receipts in the last 7 days exceed SAR 20,000. Drafts remain unrestricted; use a positive stock valuation before submission."

if PRIOR_SCRIPT.count(old_users) != 1 or PRIOR_SCRIPT.count(old_message) != 1:
    raise RuntimeError("The known Purchase Receipt submission policy changed; review the approver update.")

SCRIPT = PRIOR_SCRIPT.replace(old_users, new_users).replace(old_message, new_message)
TARGET_SHA256 = hashlib.sha256(SCRIPT.encode("utf-8")).hexdigest()


def execute():
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        frappe.throw("Purchase Receipt submit validator is missing; review before migration.")
    doc = frappe.get_doc("Server Script", SCRIPT_NAME)
    if (doc.script_type != "DocType Event" or doc.disabled
            or doc.reference_doctype != "Purchase Receipt" or doc.doctype_event != "Before Submit"):
        frappe.throw("Purchase Receipt submit validator configuration changed; review before migration.")
    digest = hashlib.sha256((doc.script or "").encode("utf-8")).hexdigest()
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
