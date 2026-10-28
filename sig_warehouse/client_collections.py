"""Client invoice follow-up drafts and explicit delivery actions.

Drafts always reference the submitted Sales Invoices in ERPNext. The recipient is
entered by the operator; no customer contact number is inferred or auto-selected.
"""

import base64
import json
import re

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today


ALLOWED = {"Accounts User", "Accounts Manager", "System Manager"}
DOCTYPE = "SIG Client Collection Draft"
PRINT_FORMAT = "SIG Client Payment Reminder"
LETTER_TYPES = {"Invoice Delivery", "Friendly Reminder", "Overdue Reminder"}
LANGUAGES = {"English", "Arabic", "Bilingual"}
CHANNELS = {"WhatsApp", "Email", "WhatsApp + Email"}
DONE_STATUSES = {"Queued", "Sent"}


def _guard():
    if not ALLOWED.intersection(frappe.get_roles()):
        frappe.throw(_("You do not have access to Client Collections."), frappe.PermissionError)


def _parse_names(invoice_names):
    names = json.loads(invoice_names) if isinstance(invoice_names, str) else invoice_names
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n.strip() for n in names):
        frappe.throw(_("Select one or more invoices."))
    names = [n.strip() for n in names]
    if len(names) > 20 or len(names) != len(set(names)):
        frappe.throw(_("Select 1–20 different invoices."))
    return names


def _phone_digits(value):
    digits = "".join(c for c in str(value or "") if c.isdigit())
    if not 8 <= len(digits) <= 15:
        frappe.throw(_("Enter the client's WhatsApp number with country code."))
    return digits


def _email(value):
    value = str(value or "").strip()
    if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        frappe.throw(_("Enter a valid client email address."))
    return value


def _load_invoices(names):
    invoices = []
    customer = currency = None
    for name in names:
        doc = frappe.get_doc("Sales Invoice", name)
        doc.check_permission("read")
        if doc.docstatus != 1 or float(doc.outstanding_amount or 0) <= 0:
            frappe.throw(_("{0} is not a submitted invoice with an outstanding balance.").format(name))
        if customer and customer != doc.customer:
            frappe.throw(_("A reminder draft can contain invoices for one customer only."))
        if currency and currency != doc.currency:
            frappe.throw(_("A reminder draft can contain invoices in one currency only."))
        customer, currency = doc.customer, doc.currency
        invoices.append({
            "sales_invoice": doc.name,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "currency": doc.currency,
            "invoice_total": float(doc.grand_total or 0),
            "outstanding_amount": float(doc.outstanding_amount or 0),
        })
    return customer, currency, invoices


def _money(amount, currency):
    return frappe.utils.fmt_money(amount, currency=currency)


def _build_letter(customer_name, invoices, currency, total, letter_type, language):
    is_overdue = any(row.get("due_date") and getdate(row["due_date"]) < getdate(today()) for row in invoices)
    if letter_type == "Invoice Delivery":
        en_intro = "Please find the invoice copy/copies attached."
        ar_intro = "نرفق لكم نسخة من الفاتورة أو الفواتير."
    elif letter_type == "Friendly Reminder":
        en_intro = "This is a friendly reminder about the outstanding invoice balance(s) below."
        ar_intro = "نود تذكيركم بكل لطف بالأرصدة المستحقة الموضحة أدناه."
    else:
        en_intro = ("Our records show that the following invoice balance(s) are overdue."
                    if is_overdue else "Our records show the following outstanding invoice balance(s).")
        ar_intro = ("تظهر سجلاتنا أن أرصدة الفواتير التالية متأخرة عن السداد."
                    if is_overdue else "تظهر سجلاتنا أرصدة الفواتير المستحقة التالية.")

    invoice_lines_en = "\n".join(
        "{0} | Due: {1} | Outstanding: {2}".format(
            row["sales_invoice"], row.get("due_date") or "—", _money(row["outstanding_amount"], currency)
        ) for row in invoices
    )
    invoice_lines_ar = "\n".join(
        "{0} | تاريخ الاستحقاق: {1} | الرصيد المستحق: {2}".format(
            row["sales_invoice"], row.get("due_date") or "—", _money(row["outstanding_amount"], currency)
        ) for row in invoices
    )
    total_en = "Total outstanding: {0}".format(_money(total, currency))
    total_ar = "إجمالي الرصيد المستحق: {0}".format(_money(total, currency))
    en_body = en_intro + "\n\nPlease advise the expected payment date or contact SIG Finance if you need supporting information."
    ar_body = ar_intro + "\n\nنرجو إفادتنا بموعد السداد المتوقع، أو التواصل مع الإدارة المالية في حال احتجتم إلى أي مستندات إضافية."
    if language == "Arabic":
        subject = "تذكير بسداد الفواتير المستحقة"
        greeting, closing, body = "السادة المحترمين،", "وتفضلوا بقبول فائق الاحترام،\nالإدارة المالية – SIG", ar_body
        whatsapp_message = "{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}".format(
            greeting, body, invoice_lines_ar, total_ar, closing
        )
    elif language == "Bilingual":
        subject = "Invoice Payment Reminder | تذكير بسداد الفواتير"
        greeting, closing, body = "Dear {0}, / السادة المحترمين،".format(customer_name), "Regards, SIG Finance / مع التحية، الإدارة المالية – SIG", en_body + "\n\n" + ar_body
        whatsapp_message = "{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}\n\n{5}\n\n{6}".format(
            greeting, body, invoice_lines_en, total_en, invoice_lines_ar, total_ar, closing
        )
    else:
        subject = "Invoice Payment Reminder"
        greeting, closing, body = "Dear {0},".format(customer_name), "Regards,\nSIG Finance", en_body
        whatsapp_message = "{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}".format(
            greeting, body, invoice_lines_en, total_en, closing
        )
    return subject, greeting, body, closing, whatsapp_message, is_overdue


@frappe.whitelist()
def get_open_invoices(start=0, limit=100):
    """Read-only queue based on submitted Sales Invoices and their live balances."""
    _guard()
    start = max(int(start), 0)
    limit = min(max(int(limit), 1), 100)
    rows = frappe.get_list(
        "Sales Invoice",
        filters={"docstatus": 1, "outstanding_amount": [">", 0]},
        fields=["name", "customer", "customer_name", "posting_date", "due_date", "currency",
                "grand_total", "outstanding_amount", "status"],
        order_by="due_date asc, posting_date asc, name asc",
        start=start,
        page_length=limit + 1,
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    for row in rows:
        due = getdate(row.due_date) if row.due_date else None
        row["age_days"] = (getdate(today()) - due).days if due else None
        row["collection_status"] = "Past Due" if due and due < getdate(today()) else ("Due Date Missing" if not due else "Upcoming")
    return {"rows": rows, "start": start, "limit": limit, "has_more": has_more, "has_previous": start > 0}


@frappe.whitelist()
def create_draft(invoice_names, send_to="", send_to_email="", channel="WhatsApp", letter_type="Overdue Reminder", language="English"):
    """Create a persistent, editable client reminder draft; never sends on creation."""
    _guard()
    names = _parse_names(invoice_names)
    if channel not in CHANNELS or letter_type not in LETTER_TYPES or language not in LANGUAGES:
        frappe.throw(_("Select a valid channel, letter type, and language."))
    phone = _phone_digits(send_to) if channel in ("WhatsApp", "WhatsApp + Email") else ""
    email = _email(send_to_email) if channel in ("Email", "WhatsApp + Email") else ""
    if channel in ("Email", "WhatsApp + Email") and not email:
        frappe.throw(_("Enter the client's email address for the selected channel."))

    customer, currency, invoices = _load_invoices(names)
    customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
    total = sum(row["outstanding_amount"] for row in invoices)
    subject, greeting, body, closing, whatsapp_message, overdue = _build_letter(
        customer_name, invoices, currency, total, letter_type, language
    )
    company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
    if not company:
        frappe.throw(_("Set a default Company before creating a client reminder."))

    doc = frappe.get_doc({
        "doctype": DOCTYPE,
        "customer": customer,
        "company": company,
        "letter_date": getdate(today()),
        "letter_type": letter_type,
        "language": language,
        "channel": channel,
        "recipient_whatsapp": phone,
        "recipient_email": email,
        "currency": currency,
        "total_outstanding": total,
        "subject": subject,
        "greeting": greeting,
        "letter_body": body,
        "whatsapp_message": whatsapp_message,
        "closing": closing,
        "status": "Draft",
        "is_overdue": int(overdue),
        "invoices": invoices,
    })
    doc.insert()
    return {"name": doc.name, "status": doc.status, "invoice_count": len(invoices)}


@frappe.whitelist()
def get_drafts(start=0, limit=100):
    _guard()
    start = max(int(start), 0)
    limit = min(max(int(limit), 1), 100)
    rows = frappe.get_list(
        DOCTYPE,
        fields=["name", "customer", "modified", "total_outstanding", "currency", "recipient_whatsapp",
                "recipient_email", "channel", "status", "letter_type", "language"],
        order_by="modified desc",
        start=start,
        page_length=limit,
    )
    return {"rows": rows, "start": start, "limit": limit, "has_previous": start > 0}


def _validate_snapshot(doc):
    current = []
    for row in doc.invoices:
        inv = frappe.get_doc("Sales Invoice", row.sales_invoice)
        inv.check_permission("read")
        inv.check_permission("print")
        if inv.docstatus != 1 or float(inv.outstanding_amount or 0) <= 0:
            frappe.throw(_("{0} is no longer an open submitted invoice. Create a new reminder draft.").format(inv.name))
        if inv.customer != doc.customer or inv.currency != doc.currency:
            frappe.throw(_("Invoice {0} no longer matches this draft's customer and currency.").format(inv.name))
        if abs(float(inv.outstanding_amount or 0) - float(row.outstanding_amount or 0)) > 0.01 or str(inv.due_date or "") != str(row.due_date or ""):
            frappe.throw(_("The balance or due date for {0} changed after this draft was created. Create a fresh draft before sending.").format(inv.name))
        current.append(inv)
    return current


def _pdf_bytes(doctype, name, print_format=None):
    content = frappe.get_print(doctype, name, print_format=print_format, as_pdf=True)
    if isinstance(content, str):
        content = content.encode("latin-1")
    if not content:
        frappe.throw(_("Could not render PDF for {0} {1}.").format(doctype, name))
    return content


def _pdf_filename(value):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "document")).strip("._")
    return (safe or "document")[:100] + ".pdf"


def _response(result):
    status = int((result or {}).get("status") or 0)
    if not 200 <= status < 300:
        raise RuntimeError(_("Maytapi returned HTTP {0}.").format(status))
    try:
        body = json.loads((result or {}).get("body") or "{}")
    except (TypeError, ValueError):
        body = {}
    if body.get("success") is False or body.get("status") in ("error", "failed", "failure"):
        raise RuntimeError(str(body.get("message") or body.get("error") or _("Maytapi rejected the message."))[:500])
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    message_id = body.get("message_id") or body.get("id") or data.get("msgId") or data.get("id") or ""
    return str(message_id)


def _delivery_row(doc, key):
    return next((row for row in doc.deliveries if row.delivery_key == key), None)


def _dispatch_component(doc, key, channel, component, recipient, sender):
    row = _delivery_row(doc, key)
    if row and row.status in DONE_STATUSES:
        return True
    if not row:
        row = doc.append("deliveries", {
            "delivery_key": key, "channel": channel, "component": component,
            "recipient": recipient, "status": "Sending", "attempts": 0,
        })
    row.status = "Sending"
    row.recipient = recipient
    row.attempts = int(row.attempts or 0) + 1
    row.attempted_at = now_datetime()
    row.error = ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    try:
        result = sender()
        row.message_id = result.get("message_id", "") if isinstance(result, dict) else ""
        row.queue_reference = result.get("queue_reference", "") if isinstance(result, dict) else ""
        row.status = "Queued"
        row.error = ""
    except Exception as exc:
        row.status = "Failed"
        row.error = str(exc)[:1000]
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return row.status in DONE_STATUSES


def _maytapi_send(doc, invoice_docs):
    from sig_whatsapp.maytapi import _audit, _post, _settings, normalize_recipient

    settings = _settings()
    if not settings.enabled:
        frappe.throw(_("Maytapi is disabled in Maytapi Settings."))
    requested = normalize_recipient(doc.recipient_whatsapp)
    destination = normalize_recipient(settings.test_phone_number) if settings.test_mode else requested
    if not destination:
        frappe.throw(_("Maytapi recipient is empty after normalization."))

    def send(payload):
        result = _post(settings, payload)
        message_id = _response(result)
        try:
            _audit(DOCTYPE, doc.name, requested, destination, "QUEUED", message_id)
        except Exception:
            # The draft's delivery log is authoritative for this feature; do not
            # misreport an accepted external send because secondary audit failed.
            frappe.log_error(frappe.get_traceback(), "Client Collection Maytapi audit write failed")
        return {"message_id": message_id}

    ok = True
    ok = _dispatch_component(
        doc, "whatsapp:text", "WhatsApp", "Reminder text", destination,
        lambda: send({"to_number": destination, "type": "text", "message": doc.whatsapp_message}),
    ) and ok
    letter_pdf = _pdf_bytes(DOCTYPE, doc.name, PRINT_FORMAT)
    letter_payload = {
        "to_number": destination,
        "type": "media",
        "message": "data:application/pdf;base64," + base64.b64encode(letter_pdf).decode("ascii"),
        "filename": _pdf_filename(doc.name + "-Payment-Reminder"),
    }
    ok = _dispatch_component(
        doc, "whatsapp:letter", "WhatsApp", "Reminder letter PDF", destination,
        lambda: send(letter_payload),
    ) and ok
    for inv in invoice_docs:
        key = "whatsapp:invoice:" + inv.name
        filename = _pdf_filename(inv.name)

        def send_invoice(invoice=inv, file_name=filename):
            pdf = _pdf_bytes("Sales Invoice", invoice.name)
            return send({
                "to_number": destination,
                "type": "media",
                "message": "data:application/pdf;base64," + base64.b64encode(pdf).decode("ascii"),
                "filename": file_name,
            })

        ok = _dispatch_component(doc, key, "WhatsApp", "Invoice PDF " + inv.name, destination, send_invoice) and ok
    return ok


def _email_send(doc, invoice_docs):
    attachments = [{
        "fname": _pdf_filename(doc.name + "-Payment-Reminder"),
        "fcontent": _pdf_bytes(DOCTYPE, doc.name, PRINT_FORMAT),
    }]
    for inv in invoice_docs:
        attachments.append({"fname": _pdf_filename(inv.name), "fcontent": _pdf_bytes("Sales Invoice", inv.name)})
    message = "<p>{}</p>".format(frappe.utils.escape_html(doc.whatsapp_message or "").replace("\n", "<br>"))

    def queue_email():
        result = frappe.sendmail(
            recipients=[doc.recipient_email],
            subject=doc.subject,
            message=message,
            attachments=attachments,
            reference_doctype=DOCTYPE,
            reference_name=doc.name,
            delayed=True,
        )
        queue_reference = getattr(result, "name", "") or ""
        return {"queue_reference": queue_reference}

    return _dispatch_component(
        doc, "email:reminder-and-invoices", "Email", "Reminder and invoice PDF attachments",
        doc.recipient_email, queue_email,
    )


def _final_status(doc):
    required = []
    if doc.channel in ("WhatsApp", "WhatsApp + Email"):
        required.extend(["whatsapp:text", "whatsapp:letter"])
        required.extend("whatsapp:invoice:" + row.sales_invoice for row in doc.invoices)
    if doc.channel in ("Email", "WhatsApp + Email"):
        required.append("email:reminder-and-invoices")
    rows = {row.delivery_key: row for row in doc.deliveries}
    failed = [key for key in required if key not in rows or rows[key].status == "Failed"]
    sending = [key for key in required if key in rows and rows[key].status == "Sending"]
    done = [key for key in required if key in rows and rows[key].status in DONE_STATUSES]
    if sending:
        doc.status = "Sending"
    elif failed and done:
        doc.status = "Partially Sent"
    elif failed:
        doc.status = "Failed"
    else:
        doc.status = "Queued"
    doc.last_error = "\n".join(
        "{0}: {1}".format(key, rows[key].error or "delivery failed") for key in failed if key in rows
    )[:2000]
    doc.last_attempt_at = now_datetime()
    doc.flags.collection_dispatch = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": doc.status, "accepted": len(done), "failed": len(failed), "total": len(required)}


@frappe.whitelist()
def send_draft(name):
    """Explicitly send a saved draft; retries only delivery components not accepted before."""
    _guard()
    frappe.db.sql("select name from `tabSIG Client Collection Draft` where name=%s for update", name)
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    doc.check_permission("print")
    if doc.status == "Sending":
        frappe.throw(_("This reminder is already being sent."))
    if doc.status == "Queued":
        return {"status": "Queued", "message": _("The selected delivery channel(s) already accepted this reminder.")}
    if doc.status not in ("Draft", "Partially Sent", "Failed"):
        frappe.throw(_("This reminder cannot be sent from its current status."))
    invoice_docs = _validate_snapshot(doc)
    doc.status = "Sending"
    doc.last_attempt_at = now_datetime()
    doc.last_error = ""
    doc.flags.collection_dispatch = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # The delivery child table is a durable per-component idempotency ledger.
    # A retried draft skips text/PDFs/email already accepted by their provider.
    channel_errors = []
    if doc.channel in ("WhatsApp", "WhatsApp + Email"):
        try:
            _maytapi_send(doc, invoice_docs)
        except Exception as exc:
            channel_errors.append("WhatsApp: " + str(exc)[:900])
    if doc.channel in ("Email", "WhatsApp + Email"):
        try:
            _email_send(doc, invoice_docs)
        except Exception as exc:
            channel_errors.append("Email: " + str(exc)[:900])
    doc.reload()
    result = _final_status(doc)
    if channel_errors:
        doc.last_error = "\n".join(filter(None, [doc.last_error, *channel_errors]))[:2000]
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        result["error"] = doc.last_error
    return result
