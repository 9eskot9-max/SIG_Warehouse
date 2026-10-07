"""HR: ask employees on .local logins for their official email over WhatsApp; collect replies for HR review.

    preview  ->  sig_warehouse.sig_hr.email_request.send_email_requests(mode="preview")
    test     ->  ... mode="test"   one message to Maytapi Settings.test_phone_number only
    send     ->  ... mode="send"   real recipients (Maytapi test_mode still redirects to the test phone)
    collect  ->  collect_email_replies()  (hourly scheduler; also callable by HR)

Never changes a User or Employee: a reply only fills SIG Employee Onboarding.proposed_email for HR to approve.
Sending uses sig_whatsapp's own transport/audit (Maytapi Message Log row per send / failure).
"""
import json

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from sig_warehouse.sig_hr.email_request_logic import (
    REQUEST_TEXT, match_replies, needs_email_request, parse_inbox_row, phone_key,
)

ALLOWED_ROLES = {"HR Manager", "System Manager"}
RESEND_AFTER_DAYS = 14
ONBOARDING = "SIG Employee Onboarding"


def _guard():
    if not ALLOWED_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only HR Manager or System Manager can send HR email requests."), frappe.PermissionError)


def _recipients():
    rows = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "cell_number", "user_id", "company_email", "personal_email"],
        limit_page_length=0,
    )
    return [r for r in rows if needs_email_request(r)]


def _mask(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return digits[:3] + "***" + digits[-3:] if len(digits) > 6 else "***"


def _recently_asked(employee):
    return frappe.db.exists("Maytapi Message Log", {
        "reference_doctype": "Employee", "reference_name": employee, "status": "QUEUED",
        "creation": [">", add_days(now_datetime(), -RESEND_AFTER_DAYS)],
    })


def _send_text(settings, to_number):
    from sig_whatsapp.maytapi import _post
    result = _post(settings, {"to_number": to_number, "type": "text", "message": REQUEST_TEXT})
    if not 200 <= int(result.get("status", 0)) < 300:
        raise frappe.ValidationError(_("Maytapi returned HTTP {0}.").format(result.get("status")))
    try:
        body = json.loads(result.get("body") or "{}")
    except ValueError:
        body = {}
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    return str(body.get("message_id") or body.get("id") or data.get("msgId") or data.get("id") or "")


def _mark_sent(employee, when):
    if frappe.db.exists(ONBOARDING, employee):
        frappe.db.set_value(ONBOARDING, employee, "email_request_sent_at", when, update_modified=False)


@frappe.whitelist()
def send_email_requests(mode="preview"):
    _guard()
    recipients = _recipients()
    if mode == "preview":
        return {
            "mode": "preview", "count": len(recipients), "text": REQUEST_TEXT,
            "recipients": [{"employee": r.name, "name": r.employee_name, "phone": _mask(r.cell_number),
                            "already_asked": bool(_recently_asked(r.name))} for r in recipients],
        }
    if mode not in ("test", "send"):
        frappe.throw(_("mode must be preview, test or send"))

    from sig_whatsapp.maytapi import _audit, _settings, normalize_recipient
    settings = _settings()
    if mode == "test":
        targets = [("User", frappe.session.user, settings.test_phone_number)]
    else:
        targets = [("Employee", r.name, r.cell_number) for r in recipients if not _recently_asked(r.name)]

    sent, failed, skipped = [], [], len(recipients) - len(targets) if mode == "send" else 0
    for ref_doctype, ref_name, phone in targets:
        resolved = normalize_recipient(phone)
        to_number = normalize_recipient(settings.test_phone_number) if settings.test_mode else resolved
        try:
            message_id = _send_text(settings, to_number)
            _audit(ref_doctype, ref_name, resolved, to_number, "QUEUED", message_id)
            if ref_doctype == "Employee" and not settings.test_mode:
                _mark_sent(ref_name, now_datetime())
            sent.append(ref_name)
        except Exception as exc:  # one failure must not stop the rest
            _audit(ref_doctype, ref_name, resolved, to_number, "FAILED", error=str(exc)[:500])
            failed.append({"ref": ref_name, "error": str(exc)[:200]})
    frappe.db.commit()
    return {"mode": mode, "sent": len(sent), "failed": failed, "skipped_recently_asked": skipped,
            "testing_redirect": bool(settings.test_mode)}


def _inbox_rows(limit=2000):
    from sig_warehouse.sig_warehouse.field_sessions import _gviz
    # No %-formatting here: the query itself contains a literal "%" (like '%@c.us').
    rows = _gviz("select A,C,E where E like '%@c.us' order by A desc limit " + str(int(limit)))
    return [parse_inbox_row(r[0], r[1], r[2]) for r in rows if len(r) >= 3]


@frappe.whitelist()
def collect_email_replies():
    """Hourly. Fill proposed_email on onboarding records whose request is unanswered; never touches Employee/User."""
    if frappe.session.user != "Administrator":
        _guard()
    pending = frappe.get_all(
        ONBOARDING,
        filters={"email_request_sent_at": ["is", "set"], "email_reply_at": ["is", "not set"]},
        fields=["name", "email_request_sent_at"],
        limit_page_length=0,
    )
    if not pending:
        return {"pending": 0, "matched": 0}
    phones = {r.name: r.cell_number for r in frappe.get_all(
        "Employee", filters={"name": ["in", [p.name for p in pending]]}, fields=["name", "cell_number"])}
    requests, emp_by_key = {}, {}
    for p in pending:
        key = phone_key(phones.get(p.name))
        if key:
            requests[key] = str(p.email_request_sent_at)[:19]
            emp_by_key[key] = p.name
    matched = match_replies(requests, _inbox_rows())
    for key, (received_at, email) in matched.items():
        frappe.db.set_value(ONBOARDING, emp_by_key[key], {"proposed_email": email, "email_reply_at": received_at},
                            update_modified=False)
    frappe.db.commit()
    return {"pending": len(pending), "matched": len(matched)}
