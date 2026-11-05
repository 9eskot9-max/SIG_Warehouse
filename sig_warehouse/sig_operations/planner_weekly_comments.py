"""Own-employee Planner comments, grouped by the Sunday 19:00 Riyadh cutoff."""
from datetime import datetime, time, timedelta
import hashlib

import frappe
from frappe import _

from sig_warehouse.sig_warehouse.field_planner_api import _require_access, _riyadh_now

DOCTYPE = "SIG Planner Weekly Comment"
FIELDS = ("last_week", "this_week", "erp_plan")
MAX_COMMENT_LENGTH = 4000


def period_start(now):
    sunday = now.date() - timedelta(days=(now.weekday() + 1) % 7)
    if now.weekday() == 6 and (now.hour, now.minute, now.second) < (19, 0, 0):
        sunday -= timedelta(days=7)
    return sunday


def _employee():
    _require_access()
    if not frappe.has_permission("Employee", "read"):
        frappe.throw(_("Employee read access is required to save your weekly comments."), frappe.PermissionError)
    rows = frappe.get_list("Employee", filters={"user_id": frappe.session.user, "status": "Active"},
                           fields=["name", "employee_name"], page_length=2)
    if len(rows) != 1:
        frappe.throw(_("A unique active Employee linked to your User is required for weekly comments."), frappe.PermissionError)
    return rows[0]


def _key(employee, start):
    digest = hashlib.sha256(str(employee).encode("utf-8")).hexdigest()[:24]
    return f"{start}-{digest}"


@frappe.whitelist()
def get_comments():
    employee = _employee()
    now = _riyadh_now()
    start = period_start(now)
    key = _key(employee.name, start)
    doc = frappe.get_doc(DOCTYPE, key) if frappe.db.exists(DOCTYPE, key) else None
    # Owner has already been checked against the authenticated User. Do not
    # expose other employees' comments via the Planner endpoint.
    if doc and (doc.employee != employee.name or str(doc.period_start) != str(start)):
        frappe.throw(_("Weekly comment identity mismatch."), frappe.PermissionError)
    history = frappe.get_all(DOCTYPE, filters={"employee": employee.name, "period_start": ["<", str(start)]},
                             fields=["period_start", *FIELDS], order_by="period_start desc", limit_page_length=12)
    next_reset = datetime.combine(start + timedelta(days=7), time(19), tzinfo=now.tzinfo)
    return {"employee_name": employee.employee_name, "period_start": str(start),
            "next_reset": str(start + timedelta(days=7)) + " 19:00",
            "seconds_until_reset": max(1, int((next_reset - now).total_seconds())),
            "modified": str(doc.modified) if doc else "", "comments": {field: doc.get(field) or "" if doc else "" for field in FIELDS},
            "history": history}


@frappe.whitelist(methods=["POST"])
def save_comments(period, last_week="", this_week="", erp_plan="", modified=""):
    employee = _employee()
    start = period_start(_riyadh_now())
    if str(period) != str(start):
        frappe.throw(_("The weekly period has changed. Reload before saving your comments."))
    values = {"last_week": last_week, "this_week": this_week, "erp_plan": erp_plan}
    if any(not isinstance(value, str) or len(value) > MAX_COMMENT_LENGTH for value in values.values()):
        frappe.throw(_("Each comment must be text of at most 4,000 characters."))
    key = _key(employee.name, start)
    with frappe.cache().lock("sig_planner_weekly_comment_" + key, timeout=30):
        if period_start(_riyadh_now()) != start:
            frappe.throw(_("The weekly period has changed. Reload before saving your comments."))
        if frappe.db.exists(DOCTYPE, key):
            doc = frappe.get_doc(DOCTYPE, key)
            if doc.employee != employee.name or str(doc.period_start) != str(start):
                frappe.throw(_("Weekly comment identity mismatch."), frappe.PermissionError)
            if not modified or str(doc.modified) != str(modified):
                frappe.throw(_("These comments changed in another session. Reload before saving."))
        else:
            if modified:
                frappe.throw(_("The weekly comments changed. Reload before saving."))
            doc = frappe.get_doc({"doctype": DOCTYPE, "entry_key": key,
                                  "employee": employee.name, "period_start": start})
        doc.update(values)
        # Direct DocType write access is not granted to Planner users; this
        # service permits only the current employee's current-period record.
        doc.save(ignore_permissions=True)
        # Keep the lock until the write is visible to the next request.
        frappe.db.commit()
    return get_comments()
