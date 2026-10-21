"""Receive small, idempotent receipts when SIGPC updates its Mapping Master."""

import hashlib
import re

import frappe


ALLOWED_ROLES = {
    "System Manager",
    "Operations Manager",
    "Operations User",
    "Projects Manager",
    "SIG Excel Setup Editor",
}


@frappe.whitelist(methods=["POST"])
def record_revision():
    user = frappe.session.user
    if user == "Guest" or not (set(frappe.get_roles(user)) & ALLOWED_ROLES):
        frappe.throw("You are not allowed to record Mapping Master revisions", frappe.PermissionError)

    master_key = str(frappe.form_dict.get("master_key") or "").strip()[:140]
    fingerprint = str(frappe.form_dict.get("fingerprint") or "").strip().lower()
    workbook = str(frappe.form_dict.get("source_workbook") or "").strip()[:140]
    sheet = str(frappe.form_dict.get("source_sheet") or "").strip()[:140]
    row_count = _bounded_int(frappe.form_dict.get("row_count"), "row_count")
    site_count = _bounded_int(frappe.form_dict.get("site_count"), "site_count")
    if not master_key or not workbook or not sheet:
        frappe.throw("master_key, source_workbook and source_sheet are required")
    if not re.fullmatch(r"[0-9a-f]{8,64}", fingerprint):
        frappe.throw("fingerprint must be 8-64 lowercase hexadecimal characters")

    # Name is deterministic across retries and scoped to this source master.
    name = hashlib.sha256((master_key + "|" + fingerprint).encode("utf-8")).hexdigest()
    if frappe.db.exists("SIG Mapping Master Revision", name):
        return {"result": "duplicate", "name": name}

    doc = frappe.get_doc({
        "doctype": "SIG Mapping Master Revision",
        "name": name,
        "master_key": master_key,
        "fingerprint": fingerprint,
        "source_workbook": workbook,
        "source_sheet": sheet,
        "row_count": row_count,
        "site_count": site_count,
        "recorded_at": frappe.utils.now(),
        "recorded_by": user,
    })
    doc.insert(ignore_permissions=True)
    return {"result": "created", "name": name}


def _bounded_int(value, field):
    try:
        number = int(value)
    except (TypeError, ValueError):
        frappe.throw(field + " must be a non-negative integer")
    if number < 0 or number > 10000000:
        frappe.throw(field + " is outside the accepted range")
    return number
