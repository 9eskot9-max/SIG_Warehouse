"""Operations: send a reviewed WhatsApp notice to SIG project managers, through the same Maytapi transport and audit as HR.

    preview ->  sig_warehouse.sig_operations.pm_notice.send_pm_notices(notices, mode="preview")
    test    ->  ... mode="test"  every notice goes to Maytapi Settings.test_phone_number only
    send    ->  ... mode="send"  each PM's own number (Maytapi test_mode still redirects to the test phone)

notices: [{"employee": "HR-EMP-...", "text": "..."}]. Only enabled PM rows of the Operations Setup Hub can receive one,
so this is not a general messaging tool. Each send or failure leaves a Maytapi Message Log row on the Employee.
"""
import hashlib

import frappe
from frappe import _

from sig_warehouse.sig_hr.email_request import _mask, _send_text

ALLOWED_ROLES = {"Operations Manager", "System Manager"}
MAX_TEXT = 3000
MAX_NOTICES = 20


def validate_notices(notices, pm_employees):
    """Clean, checked notices: one per PM, non-empty text within the limit. Pure, so it is tested without Frappe."""
    if not isinstance(notices, list) or not 1 <= len(notices) <= MAX_NOTICES:
        raise ValueError(f"Send between 1 and {MAX_NOTICES} notices.")
    seen, clean = set(), []
    for item in notices:
        employee = str((item or {}).get("employee") or "").strip()
        text = str((item or {}).get("text") or "").strip()
        if employee not in pm_employees:
            raise ValueError(f"{employee or 'A recipient'} is not an enabled project manager in the Operations Setup Hub.")
        if employee in seen:
            raise ValueError(f"{employee} appears more than once.")
        if not text or len(text) > MAX_TEXT:
            raise ValueError(f"The notice for {employee} must have between 1 and {MAX_TEXT} characters.")
        seen.add(employee)
        clean.append({"employee": employee, "text": text})
    return clean


def notice_key(employee, text):
    """Same PM and same text: sent once per day, so a retry or double click does not repeat it."""
    return "sig:pm-notice:" + hashlib.sha256((employee + "\n" + text).encode("utf-8")).hexdigest()


def _guard():
    if not ALLOWED_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only an Operations Manager or System Manager can send project manager notices."), frappe.PermissionError)


def _pm_employees():
    from sig_warehouse.sig_operations.excel_setup import _state
    _doc, datasets = _state()
    return {str(r.get("employee") or "") for r in datasets.get("ops_team_members", [])
            if r.get("role") == "pm" and r.get("enabled") not in (0, False, "0", "")}


@frappe.whitelist(methods=["POST"])
def send_pm_notices(notices, mode="preview"):
    _guard()
    if mode not in ("preview", "test", "send"):
        frappe.throw(_("mode must be preview, test or send"))
    try:
        clean = validate_notices(frappe.parse_json(notices) if isinstance(notices, str) else notices, _pm_employees())
    except ValueError as error:
        frappe.throw(str(error))
    people = {r.name: r for r in frappe.get_all("Employee", filters={"name": ["in", [n["employee"] for n in clean]], "status": "Active"},
                                                fields=["name", "employee_name", "cell_number"], limit_page_length=0)}
    for notice in clean:
        person = people.get(notice["employee"])
        if not person or not person.cell_number:
            frappe.throw(_("{0} is not an active Employee with a mobile number.").format(notice["employee"]))
        notice.update(name=person.employee_name, phone=person.cell_number)
    if mode == "preview":
        return {"mode": "preview", "count": len(clean), "notices": [
            {"employee": n["employee"], "name": n["name"], "phone": _mask(n["phone"]), "text": n["text"],
             "already_sent_today": bool(frappe.cache().get_value(notice_key(n["employee"], n["text"])))} for n in clean]}

    from sig_whatsapp.maytapi import _audit, _settings, normalize_recipient
    settings = _settings()
    if mode == "test" and not settings.test_phone_number:
        frappe.throw(_("Set a test phone number in Maytapi Settings first."))
    sent, failed, skipped = [], [], []
    for n in clean:
        key = notice_key(n["employee"], n["text"])
        if mode == "send" and frappe.cache().get_value(key):
            skipped.append(n["employee"])
            continue
        resolved = normalize_recipient(n["phone"])
        to_number = normalize_recipient(settings.test_phone_number) if (mode == "test" or settings.test_mode) else resolved
        try:
            message_id = _send_text(settings, to_number, n["text"])
            _audit("Employee", n["employee"], resolved, to_number, "QUEUED", message_id)
            if mode == "send" and not settings.test_mode:
                frappe.cache().set_value(key, 1, expires_in_sec=86400)
            sent.append({"employee": n["employee"], "message_id": message_id, "to": _mask(to_number)})
        except Exception as exc:  # one failure must not stop the rest
            _audit("Employee", n["employee"], resolved, to_number, "FAILED", error=str(exc)[:500])
            failed.append({"employee": n["employee"], "error": str(exc)[:200]})
    frappe.db.commit()
    return {"mode": mode, "sent": sent, "failed": failed, "skipped_already_sent": skipped,
            "testing_redirect": bool(settings.test_mode) or mode == "test"}
