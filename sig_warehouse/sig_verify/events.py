"""Issue the verification token + QR when a registered document is submitted."""

import frappe
from frappe.utils import get_url

from .qr_style import render_png
from .registry import QR_FILE_PREFIX, TOKEN_FIELD, VERIFIABLE, qr_file_name
from .tokens import new_token, verify_url


def on_submit(doc, method=None):
    """doc_events hook. Never blocks the submit: any failure goes to the Error Log."""
    if doc.doctype not in VERIFIABLE:
        return
    try:
        issue(doc.doctype, doc.name)
    except Exception:
        frappe.log_error(
            title=f"SIG Verify: could not issue QR for {doc.doctype} {doc.name}",
            message=frappe.get_traceback(),
        )


def issue(doctype, name):
    """Create the token and the QR file if missing. Idempotent; returns the token.

    The token is written with ``update_modified=False`` so "modified by" stays the submitter -
    print formats read it for "Authorized by".
    """
    if doctype not in VERIFIABLE:
        frappe.throw(f"{doctype} is not registered for verification (sig_verify.registry.VERIFIABLE)")

    token = frappe.db.get_value(doctype, name, TOKEN_FIELD)
    if not token:
        token = new_token()
        frappe.db.set_value(doctype, name, TOKEN_FIELD, token, update_modified=False)

    if not _qr_file_exists(doctype, name):
        png = render_png(verify_url(get_url(), token))
        frappe.get_doc({
            "doctype": "File",
            "file_name": qr_file_name(name),
            "attached_to_doctype": doctype,
            "attached_to_name": name,
            "content": png,
            "is_private": 0,
            "folder": "Home/Attachments",
        }).save(ignore_permissions=True)
    return token


def backfill(doctype, name):
    """Issue a QR for a document submitted before this feature existed.

    bench --site <site> execute sig_warehouse.sig_verify.events.backfill \
        --kwargs "{'doctype': 'Quotation', 'name': 'QTN-26-055'}"
    """
    docstatus = frappe.db.get_value(doctype, name, "docstatus")
    if docstatus is None:
        frappe.throw(f"{doctype} {name} does not exist")
    if docstatus == 2:
        frappe.throw(f"{doctype} {name} is cancelled; not issuing a QR")
    token = issue(doctype, name)
    frappe.db.commit()
    return {"doctype": doctype, "name": name, "docstatus": docstatus, "token_set": bool(token)}


def _qr_file_exists(doctype, name):
    return bool(frappe.db.exists("File", {
        "attached_to_doctype": doctype,
        "attached_to_name": name,
        "file_name": ["like", f"{QR_FILE_PREFIX}%"],
    }))
