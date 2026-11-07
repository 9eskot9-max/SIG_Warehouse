"""Own-employee Planner comments, grouped by the Sunday 19:00 Riyadh cutoff."""
from datetime import datetime, time, timedelta
import hashlib

import frappe
from frappe import _

from sig_warehouse.sig_warehouse.field_planner_api import _require_access, _riyadh_now
from sig_warehouse.sig_warehouse.project_family import DISPLAY_LABELS, normalize_family

DOCTYPE = "SIG Planner Weekly Comment"
FAMILY_DOCTYPE = "SIG Planner Family Weekly Comment"
FIELDS = ("last_week", "this_week", "erp_plan")
MAX_COMMENT_LENGTH = 4000


def period_start(now):
    sunday = now.date() - timedelta(days=(now.weekday() + 1) % 7)
    if now.weekday() == 6 and (now.hour, now.minute, now.second) < (19, 0, 0):
        sunday -= timedelta(days=7)
    return sunday


def _employee():
    _require_access()
    if not set(frappe.get_roles()).intersection({"Projects Manager", "System Manager"}):
        frappe.throw(_("Weekly PM comments require the Projects Manager role."), frappe.PermissionError)
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


def _family_key(value):
    family = normalize_family(value)
    if family not in DISPLAY_LABELS:
        frappe.throw(_("Choose one of the configured project families."))
    return family


def _family_entry_key(family, start):
    return f"{start}-{family}"


@frappe.whitelist()
def get_family_comments(family=None):
    """Read the current and recent shared weekly comments for one project family."""
    _require_access()
    family = _family_key(family or next(iter(DISPLAY_LABELS)))
    now = _riyadh_now()
    start = period_start(now)
    key = _family_entry_key(family, start)
    doc = frappe.get_doc(FAMILY_DOCTYPE, key) if frappe.db.exists(FAMILY_DOCTYPE, key) else None
    if doc and (doc.family != family or str(doc.period_start) != str(start)):
        frappe.throw(_("Weekly family comment identity mismatch."), frappe.PermissionError)
    history = frappe.get_all(FAMILY_DOCTYPE,
                             filters={"family": family, "period_start": ["<", str(start)]},
                             fields=["period_start", *FIELDS], order_by="period_start desc", limit_page_length=12)
    next_reset = datetime.combine(start + timedelta(days=7), time(19), tzinfo=now.tzinfo)
    return {"family": family, "family_label": DISPLAY_LABELS[family],
            "families": [{"value": key, "label": label} for key, label in DISPLAY_LABELS.items()],
            "period_start": str(start), "next_reset": str(start + timedelta(days=7)) + " 19:00",
            "seconds_until_reset": max(1, int((next_reset - now).total_seconds())),
            "modified": str(doc.modified) if doc else "",
            "comments": {field: (doc.get(field) or "") if doc else "" for field in FIELDS},
            "history": history}


@frappe.whitelist(methods=["POST"])
def save_family_comments(family, period, last_week="", this_week="", erp_plan="", modified=""):
    """Save the shared family entry; do not grant Planner users direct DocType write access."""
    _require_access()
    family = _family_key(family)
    start = period_start(_riyadh_now())
    if str(period) != str(start):
        frappe.throw(_("The weekly period has changed. Reload before saving these comments."))
    values = {"last_week": last_week, "this_week": this_week, "erp_plan": erp_plan}
    if any(not isinstance(value, str) or len(value) > MAX_COMMENT_LENGTH for value in values.values()):
        frappe.throw(_("Each comment must be text of at most 4,000 characters."))
    key = _family_entry_key(family, start)
    with frappe.cache().lock("sig_planner_family_weekly_comment_" + key, timeout=30):
        if period_start(_riyadh_now()) != start:
            frappe.throw(_("The weekly period has changed. Reload before saving these comments."))
        if frappe.db.exists(FAMILY_DOCTYPE, key):
            doc = frappe.get_doc(FAMILY_DOCTYPE, key)
            if doc.family != family or str(doc.period_start) != str(start):
                frappe.throw(_("Weekly family comment identity mismatch."), frappe.PermissionError)
            if not modified or str(doc.modified) != str(modified):
                frappe.throw(_("These comments changed in another session. Reload before saving."))
        else:
            if modified:
                frappe.throw(_("The weekly comments changed. Reload before saving."))
            doc = frappe.get_doc({"doctype": FAMILY_DOCTYPE, "entry_key": key,
                                  "family": family, "period_start": start})
        doc.update(values)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    return get_family_comments(family)


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
