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


def _phone_digits(value):
    return re.sub(r"[\s()+-]", "", str(value or ""))


def _normalize_phone(value):
    phone = _phone_digits(value)
    if not re.fullmatch(r"\d{8,15}", phone):
        frappe.throw(_("Enter a phone number with country code (8 to 15 digits)."))
    return phone


def _contact_phone(contact):
    if contact.mobile_no:
        return contact.mobile_no
    if contact.phone:
        return contact.phone
    primary = next((p.phone for p in contact.phone_nos if p.is_primary_mobile_no), None)
    return primary or next((p.phone for p in contact.phone_nos if p.phone), "")


def _supplier_contacts(supplier):
    if not frappe.has_permission("Contact", "read"):
        frappe.throw(_("You do not have permission to read Contacts."), frappe.PermissionError)
    links = frappe.get_all("Dynamic Link", filters={
        "parenttype": "Contact", "link_doctype": "Supplier", "link_name": supplier,
    }, fields=["parent"], limit_page_length=500)
    contacts = []
    for name in dict.fromkeys(link.parent for link in links):
        contact = frappe.get_doc("Contact", name)
        contact.check_permission("read")
        contacts.append(contact)
    return contacts


def _legacy_supplier_phone(supplier):
    if not frappe.db.exists("DocType", "SIG Supplier RFQ Contact"):
        return ""
    return frappe.db.get_value("SIG Supplier RFQ Contact", {"supplier": supplier}, "whatsapp_number") or ""


def _supplier_phone(supplier, preferred_contact=None):
    contacts = _supplier_contacts(supplier)
    whatsapp_contact = next((contact for contact in contacts
        if contact.first_name == "WhatsApp" and _contact_phone(contact)), None)
    if whatsapp_contact:
        return _contact_phone(whatsapp_contact)
    if preferred_contact:
        selected = next((contact for contact in contacts if contact.name == preferred_contact), None)
        if selected and selected.first_name == "WhatsApp" and _contact_phone(selected):
            return _contact_phone(selected)
    legacy_phone = _legacy_supplier_phone(supplier)
    if legacy_phone:
        return legacy_phone
    return ""


def sync_supplier_contacts(doc, method=None):
    """Turn numbers entered on native RFQ supplier rows into linked Contacts."""
    for row in doc.get("suppliers") or []:
        if not row.supplier or not row.get("custom_whatsapp_number"):
            continue
        phone = _normalize_phone(row.custom_whatsapp_number)
        row.custom_whatsapp_number = phone
        supplier = frappe.get_doc("Supplier", row.supplier)
        supplier.check_permission("read")
        contacts = _supplier_contacts(supplier.name)
        exact = next((contact for contact in contacts
            if re.fullmatch(r"\d{8,15}", _phone_digits(_contact_phone(contact)))
            and _phone_digits(_contact_phone(contact)) == phone), None)
        if exact:
            row.contact = exact.name
            continue

        # Keep a dedicated, clearly labelled WhatsApp contact. Do not overwrite
        # an existing named supplier representative when a different number is entered.
        supplier_label = supplier.supplier_name or supplier.name
        contact = next((candidate for candidate in contacts
            if candidate.first_name == "WhatsApp" and candidate.last_name == supplier_label), None)
        if contact:
            contact.check_permission("write")
        else:
            if not frappe.has_permission("Contact", "create"):
                frappe.throw(_("You need Contact create permission to save this supplier number."), frappe.PermissionError)
            contact = frappe.new_doc("Contact")
            contact.first_name = "WhatsApp"
            contact.last_name = supplier_label
            contact.company_name = supplier_label
            contact.append("links", {"link_doctype": "Supplier", "link_name": supplier.name})

        contact.mobile_no = phone
        primary = next((entry for entry in contact.phone_nos if entry.is_primary_mobile_no), None)
        if primary:
            primary.phone = phone
        else:
            contact.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
        if contact.is_new():
            contact.insert()
        else:
            contact.save()
        row.contact = contact.name


@frappe.whitelist()
def supplier_phone(supplier):
    supplier_doc = frappe.get_doc("Supplier", supplier)
    supplier_doc.check_permission("read")
    return {"phone": _supplier_phone(supplier_doc.name)}


@frappe.whitelist()
def supplier_numbers(name):
    doc = _rfq(name)
    result = []
    for row in doc.suppliers:
        supplier = frappe.get_doc("Supplier", row.supplier)
        supplier.check_permission("read")
        result.append({"supplier": supplier.name,
            "phone": row.get("custom_whatsapp_number") or _supplier_phone(supplier.name, row.contact)})
    from sig_whatsapp.maytapi import _settings
    settings = _settings()
    return {"suppliers": result, "test_mode": bool(settings.test_mode)}


@frappe.whitelist(methods=["POST"])
def save_supplier_number(name, supplier, phone):
    doc = _rfq(name)
    doc.check_permission("write")
    if supplier not in [row.supplier for row in doc.suppliers]:
        frappe.throw(_("Supplier is not on this request for quotation."))
    phone = _normalize_phone(phone)
    row = next((entry for entry in doc.suppliers if entry.supplier == supplier), None)
    row.custom_whatsapp_number = phone
    doc.save()
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
    supplier_row = next((row for row in doc.suppliers if row.supplier == supplier), None)
    phone = (supplier_row.get("custom_whatsapp_number") if supplier_row else "") or _supplier_phone(supplier, supplier_row.contact if supplier_row else None)
    if supplier_row and phone and not supplier_row.get("custom_whatsapp_number"):
        # A number from an older saved RFQ-contact record or linked Supplier
        # Contact is absorbed into the inline row and native Contact as used.
        supplier_row.custom_whatsapp_number = _normalize_phone(phone)
        doc.save()
        doc.reload()
        supplier_row = next((row for row in doc.suppliers if row.supplier == supplier), None)
        phone = supplier_row.get("custom_whatsapp_number") if supplier_row else phone
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
