"""Remove the PR draft value ceiling; submission policy stays server-side."""
import hashlib

import frappe


SCRIPT_NAME = "sig_register_purchase_receipt"
PRIOR_SHA256 = "9f380f18c755c3350389c34a845fa051a32d29dbf30380306ac8d8cce8a8c81a"
UPDATED_SHA256 = "5715fa3954eefc769a602fe1c5d401d2519ff683fa9e66ab9bc6538c25a96266"
START = "        if route == 'NOPO' and amount > 20000:"
END = "        for ln in lines:"


def execute():
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        frappe.throw("Purchase Receipt draft endpoint is missing; review before migration.")
    doc = frappe.get_doc("Server Script", SCRIPT_NAME)
    if doc.script_type != "API" or doc.disabled:
        frappe.throw("Purchase Receipt draft endpoint configuration changed; review before migration.")
    source = doc.script or ""
    if "# Draft staging has no value ceiling; PR submit policy is enforced by sig_pr_threshold_validator." in source:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() == UPDATED_SHA256:
            return
        frappe.throw("Updated Purchase Receipt draft endpoint changed; review before migration.")
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != PRIOR_SHA256:
        frappe.throw("Purchase Receipt draft endpoint changed; review before migration.")
    lines = source.splitlines(keepends=True)
    begin = next((i for i, line in enumerate(lines) if line.rstrip("\r\n") == START), -1)
    end = next((i for i, line in enumerate(lines[begin + 1:], begin + 1)
                if line.rstrip("\r\n") == END), -1) if begin >= 0 else -1
    if begin < 0 or end < 0:
        frappe.throw("Purchase Receipt draft threshold block was not found; review before migration.")
    newline = "\r\n" if lines[begin].endswith("\r\n") else "\n"
    lines[begin:end] = ["        # Draft staging has no value ceiling; PR submit policy is enforced by sig_pr_threshold_validator." + newline]
    doc.script = "".join(lines)
    doc.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Server Script")
