"""Supplier contact preparation for native Requests for Quotation."""
import re
import base64
import hashlib
import json
import frappe
from frappe import _
from frappe.utils import escape_html, now_datetime
from frappe.utils.pdf import get_pdf


def _rfq(name):
    doc = frappe.get_doc("Request for Quotation", name)
    doc.check_permission("read")
    return doc


@frappe.whitelist()
def supplier_numbers(name):
    doc = _rfq(name)
    if not frappe.has_permission("SIG Supplier RFQ Contact", "read"):
        frappe.throw(_("You do not have access to supplier RFQ contacts."), frappe.PermissionError)
    result = []
    for row in doc.suppliers:
        supplier = frappe.get_doc("Supplier", row.supplier)
        supplier.check_permission("read")
        contact = frappe.db.get_value("SIG Supplier RFQ Contact", {"supplier": supplier.name}, "whatsapp_number")
        result.append({"supplier": supplier.name, "phone": contact or ""})
    from sig_whatsapp.maytapi import _settings
    settings = _settings()
    return {"suppliers": result, "test_mode": bool(settings.test_mode)}


@frappe.whitelist(methods=["POST"])
def save_supplier_number(name, supplier, phone):
    doc = _rfq(name)
    doc.check_permission("write")
    if supplier not in [row.supplier for row in doc.suppliers]:
        frappe.throw(_("Supplier is not on this request for quotation."))
    phone = re.sub(r"[\s()+-]", "", str(phone or ""))
    if not re.fullmatch(r"\d{8,15}", phone):
        frappe.throw(_("Enter a phone number with country code (8 to 15 digits)."))
    if not frappe.has_permission("SIG Supplier RFQ Contact", "read"):
        frappe.throw(_("You do not have access to supplier RFQ contacts."), frappe.PermissionError)
    contact_name = frappe.db.get_value("SIG Supplier RFQ Contact", {"supplier": supplier})
    if contact_name:
        contact = frappe.get_doc("SIG Supplier RFQ Contact", contact_name)
        contact.check_permission("write")
    else:
        contact = frappe.new_doc("SIG Supplier RFQ Contact")
        contact.supplier = supplier
    contact.whatsapp_number = phone
    if contact.is_new():
        contact.insert()
    else:
        contact.save()
    return {"supplier": supplier, "phone": phone}


def _letter(doc, supplier):
    e = lambda value: escape_html(str(value or ""))
    rows = "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        e(row.item_code), e(row.description or row.item_name), e(row.qty), e(row.uom)) for row in doc.items)
    return """<html><body><h2>Request for Quotation</h2><p>To: {supplier}</p>
    <p>Reference: {name} &nbsp; Date: {date}</p><p>Dear Supplier,</p>
    <p>Please provide your quotation for the following items, including delivery time, VAT and payment terms.</p>
    <table border="1" cellpadding="6" cellspacing="0" width="100%"><tr><th>Item</th><th>Description</th><th>Quantity</th><th>Unit</th></tr>{rows}</table>
    <p>Required by: {required}</p><p>Regards,<br>SIG Purchasing</p></body></html>""".format(
        supplier=e(supplier), name=e(doc.name), date=e(doc.transaction_date),
        required=e(doc.get("schedule_date") or "See item schedule"), rows=rows)


@frappe.whitelist(methods=["POST"])
def send_supplier(name, supplier, retry_failed=0):
    doc = _rfq(name)
    doc.check_permission("write")
    if doc.docstatus != 1:
        frappe.throw(_("Submit the Request for Quotation before sending."))
    if supplier not in [r.supplier for r in doc.suppliers]:
        frappe.throw(_("Supplier is not on this request for quotation."))
    party = frappe.get_doc("Supplier", supplier)
    party.check_permission("read")
    from sig_whatsapp.maytapi import _settings, normalize_recipient
    from sig_warehouse.client_collections import _response
    settings = _settings()
    if not settings.enabled:
        frappe.throw(_("Maytapi is disabled."))
    phone = frappe.db.get_value("SIG Supplier RFQ Contact", {"supplier": supplier}, "whatsapp_number")
    requested = normalize_recipient(phone or "")
    destination = normalize_recipient(settings.test_phone_number) if settings.test_mode else requested
    if not requested or not destination:
        frappe.throw(_("Save the supplier WhatsApp number first."))
    html = _letter(doc, supplier)
    digest = hashlib.sha256(json.dumps([name, supplier, destination, html], ensure_ascii=False).encode()).hexdigest()
    key = "rfq:" + digest

    # Serialize sends for one RFQ and persist the idempotency marker before queueing.
    frappe.db.sql("select name from `tabRequest for Quotation` where name=%s for update", name)
    doc.reload()
    doc.check_permission("write")
    if doc.docstatus != 1 or supplier not in [r.supplier for r in doc.suppliers]:
        frappe.throw(_("The submitted RFQ or supplier selection has changed."))
    attempts = [row for row in doc.custom_rfq_deliveries
                if row.delivery_key == key or row.delivery_key.startswith(key + ":retry:")]
    existing = attempts[-1] if attempts else None
    if existing and existing.status in ("Sending", "Queued"):
        return {"supplier": supplier, "status": existing.status, "message_id": existing.message_id,
                "existing": True}
    if existing and existing.status == "Failed" and str(retry_failed).lower() not in ("1", "true", "yes"):
        return {"supplier": supplier, "status": "Failed", "retry_confirmation_required": True,
                "error": existing.error or ""}
    attempt = int(existing.attempts or 1) + 1 if existing else 1
    attempt_key = key if attempt == 1 else key + ":retry:" + str(attempt)
    row = doc.append("custom_rfq_deliveries", {"delivery_key": attempt_key, "channel": "WhatsApp",
        "component": "RFQ: " + supplier + (" (Retry {})".format(attempt) if attempt > 1 else ""),
        "recipient": destination, "status": "Sending", "attempts": attempt, "attempted_at": now_datetime()})
    doc.save()
    frappe.db.commit()
    try:
        frappe.enqueue(
            "sig_warehouse.sig_warehouse.rfq_whatsapp.process_supplier_send",
            queue="long", timeout=1200,
            job_name="rfq-whatsapp-" + doc.name + "-" + frappe.generate_hash(length=8),
            name=doc.name, supplier=supplier, delivery_key=attempt_key, request_key=key,
            requested=requested, destination=destination,
        )
    except Exception as exc:
        error = _("Could not queue delivery; no provider request was made: {0}").format(str(exc)[:700])
        frappe.db.set_value(row.doctype, row.name, {
            "status": "Failed", "error": error
        })
        frappe.db.commit()
        return {"supplier": supplier, "status": "Failed", "error": error}
    return {"supplier": supplier, "status": "Sending", "queued": True}


def process_supplier_send(name, supplier, delivery_key, request_key, requested, destination):
    """Render and deliver one supplier's RFQ outside the browser request."""
    doc = frappe.get_doc("Request for Quotation", name)
    row = next((entry for entry in doc.custom_rfq_deliveries if entry.delivery_key == delivery_key), None)
    if not row or row.status != "Sending":
        return {"status": row.status if row else "Missing"}
    try:
        if doc.docstatus != 1 or supplier not in [entry.supplier for entry in doc.suppliers]:
            frappe.throw(_("The submitted RFQ or supplier selection changed before delivery."))
        from sig_whatsapp.maytapi import _audit, _post, _settings
        settings = _settings()
        if not settings.enabled:
            frappe.throw(_("Maytapi is disabled."))
        html = _letter(doc, supplier)
        current_key = "rfq:" + hashlib.sha256(
            json.dumps([name, supplier, destination, html], ensure_ascii=False).encode()
        ).hexdigest()
        if current_key != request_key:
            frappe.throw(_("The RFQ content changed after this send was queued. Open the current RFQ and queue a new delivery."))
        pdf = get_pdf(html)
        result = _post(settings, {
            "to_number": destination, "type": "media",
            "message": "data:application/pdf;base64," + base64.b64encode(pdf).decode("ascii"),
            "filename": re.sub(r"[^A-Za-z0-9._-]", "_", doc.name) + "-RFQ.pdf",
        })
        message_id = _response(result)
        frappe.db.set_value(row.doctype, row.name, {"status": "Queued", "message_id": message_id, "error": ""})
        frappe.db.commit()
        try:
            _audit("Request for Quotation", name, requested, destination, "QUEUED", message_id)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "RFQ WhatsApp audit")
        return {"status": "Queued", "message_id": message_id}
    except Exception as exc:
        # A timeout can happen after provider acceptance; require Maytapi log review before any resend.
        error = _("Delivery failed or is uncertain; check Maytapi before retrying: {0}").format(str(exc)[:700])
        frappe.db.set_value(row.doctype, row.name, {"status": "Failed", "error": error})
        frappe.db.commit()
        try:
            from sig_whatsapp.maytapi import _audit
            _audit("Request for Quotation", name, requested, destination, "FAILED", error=error[:500])
        except Exception:
            frappe.log_error(frappe.get_traceback(), "RFQ WhatsApp failure audit")
        return {"status": "Failed", "error": error}
