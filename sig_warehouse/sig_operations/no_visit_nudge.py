"""Daily send-only WhatsApp message to field staff who have no visit recorded today.

    preview  ->  sig_warehouse.sig_operations.no_visit_nudge.run(mode="preview")   nothing is sent
    test     ->  ... mode="test"   every message goes to Maytapi Settings.test_phone_number only
    live     ->  ... mode="live"   real recipients (Maytapi test_mode still redirects to the test phone)

The hourly scheduler job `run_scheduled` does nothing unless SIG Field Ops Settings.nv_mode is Test or Live,
and only after the configured local hour. One message per person per day and mode (SIG No Visit Nudge).
Replies are read by the coordinator; nothing here writes a visit, session or any business record.
"""
import json
import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, get_datetime_in_timezone

from sig_warehouse.sig_operations.no_visit_logic import compose_message, decide, parse_ids, planner_leaders

NUDGE = "SIG No Visit Nudge"
SETTINGS = "SIG Field Ops Settings"
ALLOWED_ROLES = {"System Manager", "Operations Manager"}
LATEST_HOUR = 23


def _guard():
    if not ALLOWED_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only Operations Manager or System Manager can run the no-visit message."), frappe.PermissionError)


def _setting(fieldname, default=None):
    value = frappe.db.get_single_value(SETTINGS, fieldname)
    return default if value in (None, "") else value


def _active_today(day):
    start, end = f"{day} 00:00:00", f"{day} 23:59:59"
    between = ["between", [start, end]]
    ids = set(frappe.get_all("SIG Field Visit", filters={"start_at": between, "employee": ["is", "set"]},
                              pluck="employee", limit_page_length=0))
    ids |= set(frappe.get_all("SIG Field Session", filters={"start_at": between, "employee": ["is", "set"]},
                               pluck="employee", limit_page_length=0))
    phones = set(frappe.get_all("SIG Field Message", filters={"occurred_at": between}, pluck="reporter",
                                 limit_page_length=0))
    if phones:
        ids |= set(frappe.get_all("SIG Field Reporter Map", filters={"reporter_phone": ["in", list(phones)]},
                                   pluck="employee", limit_page_length=0))
    return {i for i in ids if i}


def _on_leave_or_holiday(names, day):
    out = set()
    if frappe.db.exists("DocType", "Leave Application"):
        out |= set(frappe.get_all("Leave Application", filters={
            "employee": ["in", list(names)], "docstatus": 1, "status": "Approved",
            "from_date": ["<=", day], "to_date": [">=", day]}, pluck="employee", limit_page_length=0))
    from erpnext.setup.doctype.employee.employee import is_holiday
    out |= {n for n in names if is_holiday(n, day)}
    return out


def _already_sent(day, mode):
    return set(frappe.get_all(NUDGE, filters={"nudge_date": day, "mode": mode.capitalize(), "status": "Queued"},
                              pluck="employee", limit_page_length=0))


def build(day=None, mode="live"):
    day = str(getdate(day or get_datetime_in_timezone("Asia/Riyadh").date()))
    exclude = parse_ids(_setting("nv_exclude"))
    setup = json.loads(frappe.db.get_single_value("SIG Excel Setup", "configuration_json") or "{}")
    roster = planner_leaders(setup, day)
    employees = frappe.get_all("Employee", fields=["name", "employee_name", "cell_number", "status"],
                               limit_page_length=0)
    candidates = {e.name for e in employees if e.name in roster}
    rows, truncated = decide(
        [dict(e) for e in employees], roster, _active_today(day),
        _on_leave_or_holiday(candidates, day) if candidates else set(),
        exclude, _already_sent(day, mode),
    )
    return day, rows, truncated


def _mask(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return digits[:3] + "***" + digits[-3:] if len(digits) > 6 else "***"


def _send_text(settings, to_number, message):
    import json
    from sig_whatsapp.maytapi import _post
    result = _post(settings, {"to_number": to_number, "type": "text", "message": message})
    if not 200 <= int(result.get("status", 0)) < 300:
        raise frappe.ValidationError(_("Maytapi returned HTTP {0}.").format(result.get("status")))
    try:
        body = json.loads(result.get("body") or "{}")
    except ValueError:
        body = {}
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    return str(body.get("message_id") or body.get("id") or data.get("msgId") or data.get("id") or "")


def _record(day, mode, row, status, message_id="", error="", masked=""):
    name = f"NV-{row['employee']}-{day}-{mode.capitalize()}"
    values = {"nudge_key": name, "employee": row["employee"], "employee_name": row["employee_name"], "nudge_date": day,
              "mode": mode.capitalize(), "status": status, "message_id": message_id, "error": error[:500],
              "recipient": masked, "sent_at": now_datetime()}
    if frappe.db.exists(NUDGE, name):
        frappe.db.set_value(NUDGE, name, values, update_modified=False)
    else:
        frappe.get_doc({"doctype": NUDGE, **values}).insert(ignore_permissions=True)
    return name


def run(mode="preview", day=None):
    mode = str(mode).lower()
    if mode not in ("preview", "test", "live"):
        frappe.throw(_("mode must be preview, test or live"))
    day, rows, truncated = build(day, "live" if mode == "preview" else mode)
    if getdate(day).weekday() in (4, 5):
        for row in rows:
            row["decision"], row["reason"] = "skip", "Friday or Saturday"
    senders = [r for r in rows if r["decision"] == "send"]
    summary = {"mode": mode, "day": day, "would_send": len(senders), "truncated": truncated,
               "rows": [{**r, "phone": _mask(r["phone"])} for r in rows],
               "text": compose_message(day)}
    if mode == "preview" or not senders:
        return summary
    if mode == "live" and str(_setting("nv_mode", "Off")).lower() != "live":
        frappe.throw(_("No-visit message mode must be Live to send to employees."))

    from sig_whatsapp.maytapi import _audit, _settings, normalize_recipient
    settings = _settings()
    test_number = normalize_recipient(settings.test_phone_number) if settings.test_phone_number else None
    if mode == "test" and not test_number:
        frappe.throw(_("Set a test phone number in Maytapi Settings first."))
    sent, failed = 0, []
    for row in senders:
        resolved = normalize_recipient(row["phone"])
        to_number = test_number if (mode == "test" or settings.test_mode) else resolved
        message = compose_message(day, test_for=row["employee_name"] if to_number == test_number else None)
        try:
            message_id = _send_text(settings, to_number, message)
            name = _record(day, mode, row, "Queued", message_id, masked=_mask(to_number))
            _audit(NUDGE, name, resolved, to_number, "QUEUED", message_id)
            sent += 1
        except Exception as exc:  # one failure must not stop the rest
            name = _record(day, mode, row, "Failed", error=str(exc), masked=_mask(to_number))
            _audit(NUDGE, name, resolved, to_number, "FAILED", error=str(exc)[:500])
            failed.append({"employee": row["employee"], "error": str(exc)[:200]})
    frappe.db.commit()
    summary.update({"sent": sent, "failed": failed, "testing_redirect": bool(settings.test_mode) or mode == "test"})
    return summary


@frappe.whitelist()
def run_now(mode="preview"):
    _guard()
    return run(mode)


def run_scheduled():
    """Hourly. Sends at most once per person per day, after the configured local hour."""
    mode = str(_setting("nv_mode", "Off")).lower()
    if mode not in ("test", "live"):
        return {"result": "off"}
    hour = get_datetime_in_timezone("Asia/Riyadh").hour
    if hour < int(_setting("nv_hour", 19)) or hour > LATEST_HOUR:
        return {"result": "outside the send window"}
    return run(mode)
