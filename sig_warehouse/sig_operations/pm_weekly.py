"""Weekly PM check: snapshot the plan, prepare one review per PM, send the three messages once on Sunday.

    preview  ->  sig_warehouse.sig_operations.pm_weekly.run_now(mode="preview")   builds reviews, sends nothing
    test     ->  ... mode="test"   messages go to the Maytapi test number only
    live     ->  ... mode="live"   messages go to each PM (Maytapi test_mode still redirects)

Scheduled job `run_scheduled` (hourly) does nothing unless SIG Field Ops Settings.pm_weekly_mode is Test or Live,
it is Sunday in Riyadh, and it is at or after pm_weekly_hour. Each PM's messages are sent once per week.
"""
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

from sig_warehouse.sig_operations import pm_weekly_logic as L
from sig_warehouse.sig_operations.no_visit_nudge import _mask, _send_text

SETTINGS = "SIG Field Ops Settings"
SNAPSHOT = "SIG Weekly Plan Snapshot"
REVIEW = "SIG PM Weekly Review"
SCOPE = "SIG PM Weekly Scope"
ALLOWED_ROLES = {"System Manager", "Operations Manager"}
SUNDAY = 6


def _guard():
    if not ALLOWED_ROLES.intersection(frappe.get_roles()):
        frappe.throw(_("Only Operations Manager or System Manager can run the weekly PM check."), frappe.PermissionError)


def _riyadh_now():
    return frappe.utils.get_datetime_in_timezone("Asia/Riyadh")


def _current_week():
    return L.sunday_on_or_before(_riyadh_now().date())


def _day(value):
    return L.as_date(value) if value else None


def snapshot_for(week_start):
    """The planner's sites for the week, saved once. Read through the planner as Administrator (a scheduled job)."""
    key = str(week_start)
    if frappe.db.exists(SNAPSHOT, key):
        return frappe.get_doc(SNAPSHOT, key)
    from sig_warehouse.sig_warehouse import field_planner_api as planner_api
    previous = frappe.session.user
    frappe.set_user("Administrator")
    try:
        plan = planner_api.get_field_plan(week_start=key)
    finally:
        frappe.set_user(previous)
    rows = []
    for trip in plan.get("trips") or []:
        for stop in trip.get("stops") or []:
            raw_day = stop.get("day") or trip.get("first_day") or ""
            rows.append({"site": stop.get("site"), "cycle": stop.get("cycle") or "", "project": stop.get("project") or "",
                         "team": trip.get("team") or "", "planned_day": _day(str(raw_day)[:10]) if raw_day else None,
                         "kind": "Trip"})
    summary = plan.get("summary") or {}
    doc = frappe.get_doc({"doctype": SNAPSHOT, "week_key": key, "week_start": week_start,
                          "generated_at": now_datetime(), "planner_summary": str(summary)[:140],
                          "rows": rows})
    doc.insert(ignore_permissions=True)
    return doc


def _snapshot_rows(week_start):
    if not frappe.db.exists(SNAPSHOT, str(week_start)):
        return None
    return [{"site": r.site, "cycle": r.cycle, "project": r.project, "planned_day": r.planned_day}
            for r in frappe.get_all("SIG Weekly Plan Snapshot Row", filters={"parent": str(week_start)},
                                    fields=["site", "cycle", "project", "planned_day"], order_by="idx asc", limit_page_length=0)]


def _visits(start, end):
    rows = frappe.get_all("SIG Field Visit", filters={"start_at": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
                          fields=["site", "project", "start_at"], limit_page_length=0)
    return [{"site": r.site, "project": r.project or "", "day": L.as_date(r.start_at)} for r in rows if r.site]


def _pms():
    """Active PMs and the projects each covers."""
    from sig_warehouse.sig_warehouse.people_model_gate import PEOPLE_MODEL_ACTIVE
    try:
        setup = frappe.db.get_single_value("SIG Excel Setup", "configuration_json") or "{}"
        data = frappe.parse_json(setup)
    except (TypeError, ValueError, frappe.DoesNotExistError):
        data = {}
    configured = [row for row in data.get("project_responsibilities", [])
                  if row.get("enabled") and row.get("role") == "weekly_pm"]
    if PEOPLE_MODEL_ACTIVE and configured:
        today = str(frappe.utils.nowdate())[:10]
        out = {}
        for row in configured:
            start = str(row.get("effective_from") or "")[:10]
            end = str(row.get("effective_to") or "")[:10]
            if start and start <= today and (not end or today <= end):
                out.setdefault(str(row["employee"]), set()).add(str(row["project"]))
        return out
    rows = frappe.get_all(SCOPE, filters={"active": 1}, fields=["employee", "project", "active"], limit_page_length=0)
    out = {}
    for r in rows:
        out.setdefault(r.employee, set()).add(r.project)
    return out


def create_reviews(week_start=None):
    week = L.as_date(week_start) if week_start else _current_week()
    snapshot = snapshot_for(week)
    prev = L.previous_week(week)
    prev_rows = _snapshot_rows(prev) or []
    visits = _visits(prev, prev + timedelta(days=6))
    created = []
    for employee, projects in _pms().items():
        key = f"{week}-{employee}"
        if frappe.db.exists(REVIEW, key):
            continue
        emp = frappe.db.get_value("Employee", employee, ["employee_name", "status"], as_dict=True)
        if not emp or emp.status != "Active":
            continue
        last = L.last_week_lines(prev_rows, projects, prev, visits)
        planned = {r["site"] for r in prev_rows if r["project"] in projects}
        extra = L.additions(visits, prev, planned, projects)
        snapshot_rows = [{"site": r.site, "cycle": r.cycle, "project": r.project, "planned_day": r.planned_day}
                         for r in snapshot.rows]
        this = L.this_week_lines(snapshot_rows, projects)
        comment = L.system_comment(last, extra)
        doc = frappe.get_doc({
            "doctype": REVIEW, "review_key": key, "employee": employee, "employee_name": emp.employee_name,
            "week_start": week, "status": "Open",
            "last_week_lines": [{**line, "is_addition": 0, "recorded": 0} for line in last],
            "this_week_lines": [{**line, "recorded": 0} for line in this],
            "additions": [{**e, "is_addition": 1, "visited": 1, "planned_day": None} for e in extra],
            "system_comment": comment["en"] + "\n" + comment["ar"],
        })
        doc.insert(ignore_permissions=True)
        created.append({"review": doc.name, "employee": employee, "comment": comment,
                        "this_week": len(this)})
    return {"week": str(week), "reviews": created}


def _composed(review, link):
    employee = frappe.db.get_value("Employee", review.employee, ["first_name", "employee_name", "cell_number"], as_dict=True)
    comment = {"en": "", "ar": "", "planned": 0, "visited": 0}
    lines = review.get("last_week_lines") or []
    comment["planned"] = len(lines)
    comment["visited"] = sum(1 for l in lines if l.visited)
    comment["en"] = (review.system_comment or "").split("\n")[0]
    comment["ar"] = (review.system_comment or "").split("\n")[-1]
    messages = L.build_messages(employee.first_name or employee.employee_name, comment,
                                len(review.get("this_week_lines") or []), link)
    return employee, messages


def send_reviews(week_start=None, mode="test"):
    week = L.as_date(week_start) if week_start else _current_week()
    from sig_whatsapp.maytapi import _audit, _settings, normalize_recipient
    settings = _settings()
    test_number = normalize_recipient(settings.test_phone_number) if settings.test_phone_number else None
    if mode == "test" and not test_number:
        frappe.throw(_("Set a test phone number in Maytapi Settings first."))
    sent, failed = [], []
    for name in frappe.get_all(REVIEW, filters={"week_start": week, "status": "Open"}, pluck="name", limit_page_length=0):
        review = frappe.get_doc(REVIEW, name)
        link = get_url(f"/desk/sig-pm-weekly-review/{review.name}")
        employee, messages = _composed(review, link)
        if not employee or not employee.cell_number:
            failed.append({"employee": review.employee, "error": "no phone number"})
            continue
        resolved = normalize_recipient(employee.cell_number)
        to_number = test_number if (mode == "test" or settings.test_mode) else resolved
        log = []
        try:
            for text in messages:
                body = f"[TEST - would go to {employee.employee_name}]\n{text}" if to_number == test_number else text
                message_id = _send_text(settings, to_number, body)
                _audit(REVIEW, review.name, resolved, to_number, "QUEUED", message_id)
                log.append(message_id)
            frappe.db.set_value(REVIEW, review.name, {"status": "Sent", "sent_at": now_datetime(),
                                                      "sent_messages": f"{len(log)} messages to {_mask(to_number)}"},
                                update_modified=False)
            sent.append(review.name)
        except Exception as exc:  # one PM's failure must not stop the rest
            _audit(REVIEW, review.name, resolved, to_number, "FAILED", error=str(exc)[:500])
            failed.append({"employee": review.employee, "error": str(exc)[:200]})
    frappe.db.commit()
    return {"sent": len(sent), "failed": failed, "testing_redirect": mode == "test" or bool(settings.test_mode)}


@frappe.whitelist()
def run_now(mode="preview"):
    _guard()
    mode = str(mode).lower()
    if mode not in ("preview", "test", "live"):
        frappe.throw(_("mode must be preview, test or live"))
    built = create_reviews()
    if mode == "preview":
        return {"mode": "preview", **built, "text": "Nothing was sent."}
    return {"mode": mode, **built, **send_reviews(mode=mode)}


def run_scheduled():
    """Hourly. Sends once a week, on Sunday in Riyadh, after the configured hour."""
    mode = str(frappe.db.get_single_value(SETTINGS, "pm_weekly_mode") or "Off").lower()
    if mode not in ("test", "live"):
        return {"result": "off"}
    now = _riyadh_now()
    hour = int(frappe.db.get_single_value(SETTINGS, "pm_weekly_hour") or 8)
    if now.weekday() != SUNDAY or now.hour < hour:
        return {"result": "outside the Sunday send window"}
    created = create_reviews()
    return {"created": len(created["reviews"]), **send_reviews(mode=mode)}


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles.intersection({"Administrator", "System Manager", "Operations Manager"}):
        return ""
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"
    return f"`tabSIG PM Weekly Review`.`employee` = {frappe.db.escape(employee)}"


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles.intersection({"Administrator", "System Manager", "Operations Manager"}):
        return True
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return bool(employee and employee == doc.employee)

