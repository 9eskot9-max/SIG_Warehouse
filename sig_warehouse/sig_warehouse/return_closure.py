"""Daily, DN-scoped closure of undeclared return balances after the 10-day window."""

import hashlib

import frappe
import pytz
from frappe.utils import add_days, getdate, now
from frappe.utils.data import get_datetime, get_datetime_in_timezone, get_system_timezone

from sig_warehouse.sig_warehouse import rollup

WINDOW_DAYS = 10
POLICY_TIMEZONE = "Asia/Riyadh"
POLICY_START_ID = "SIG-RETURN-WINDOW-POLICY-START"
AUTO_CLOSE_PREFIX = "SIG-AUTO-CLOSE-"
EPS = 1e-6


def _policy_date(value):
    """Interpret ERP creation timestamps in the policy's fixed Riyadh date."""
    dt = get_datetime(value)
    if dt.tzinfo is None:
        dt = pytz.timezone(get_system_timezone()).localize(dt)
    return dt.astimezone(pytz.timezone(POLICY_TIMEZONE)).date()


def initialize_return_policy_start():
    """Record the production go-live timestamp once, during the site migration."""
    if frappe.db.exists("SIG Dispatch Operation", POLICY_START_ID):
        return
    policy_text = "10 calendar days from outbound DN posting date; close from day 11"
    frappe.get_doc({
        "doctype": "SIG Dispatch Operation",
        "operation_id": POLICY_START_ID,
        "op_type": "DISPOSITION",
        "action": "RETURN_WINDOW_POLICY_START",
        "operator": frappe.session.user,
        "state": "SUBMITTED",
        "signature": hashlib.sha256(policy_text.encode("utf-8")).hexdigest(),
        "line_count": 0,
        "created_at": now(),
    }).insert(ignore_permissions=True)


def _add_backdated_review_note(source_se, posting_date, due_date):
    marker = "[SIG_RETURN_WINDOW_REVIEW_REQUIRED]"
    existing = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Stock Entry",
            "reference_name": source_se,
            "content": ["like", f"%{marker}%"],
        },
        pluck="name",
        limit_page_length=1,
    )
    if existing:
        return
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "Stock Entry",
        "reference_name": source_se,
        "content": (
            f"{marker} This DN was created after the return-window policy started, "
            f"but its posting date ({posting_date}) was already past its 10-day deadline "
            f"({due_date}) at creation. Warehouse review is required; the scheduler did not close it."
        ),
    }).insert(ignore_permissions=True)


def _close_due_dn(source_name, policy_started_at, today):
    locked = frappe.db.sql(
        "select name from `tabStock Entry` where name = %s for update",
        (source_name,),
    )
    if not locked:
        return "missing"

    source = frappe.get_doc("Stock Entry", source_name)
    if source.docstatus != 1 or source.is_return or source.purpose not in ("Material Issue", "Material Transfer"):
        return "ineligible"
    if getdate(source.creation) < getdate(policy_started_at):
        return "pre_policy"

    posting_date = getdate(source.posting_date)
    due_date = add_days(posting_date, WINDOW_DAYS)
    if due_date >= today:
        return "not_due"
    if due_date < _policy_date(source.creation):
        _add_backdated_review_note(source.name, posting_date, due_date)
        return "backdated_review"

    operation_id = AUTO_CLOSE_PREFIX + source.name
    if frappe.db.exists("SIG Dispatch Operation", operation_id):
        # A late correction has already reopened a previously auto-closed DN.
        # Leave it to the Warehouse correction path instead of repeatedly closing it.
        return "already_auto_closed"

    rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"parent": source.name, "parenttype": "Stock Entry"},
        fields=["name", "qty", "custom_qty_returned", "custom_qty_custody", "custom_return_closed"],
        order_by="idx asc, name asc",
    )
    close_lines = []
    for row in rows:
        issued = float(row.qty or 0)
        allocated = float(row.custom_qty_returned or 0) + float(row.custom_qty_custody or 0)
        if allocated > issued + EPS:
            raise ValueError(f"Return/custody exceeds issued quantity on {source.name}/{row.name}")
        if row.custom_return_closed:
            continue
        remaining = max(0.0, issued - allocated)
        if remaining > EPS:
            close_lines.append((row.name, remaining))

    if not close_lines:
        return "nothing_open"

    for detail_name, _remaining in close_lines:
        frappe.db.set_value(
            "Stock Entry Detail", detail_name, "custom_return_closed", 1, update_modified=False,
        )
        frappe.clear_document_cache("Stock Entry Detail", detail_name)

    signature_text = "|".join(f"{detail}:{qty:.12g}" for detail, qty in close_lines)
    signature = hashlib.sha256(signature_text.encode("utf-8")).hexdigest()
    frappe.get_doc({
        "doctype": "SIG Dispatch Operation",
        "operation_id": operation_id,
        "op_type": "DISPOSITION",
        "action": "AUTO_CLOSE",
        "source_se": source.name,
        "operator": frappe.session.user,
        "state": "SUBMITTED",
        "signature": signature,
        "line_count": len(close_lines),
        "created_at": now(),
    }).insert(ignore_permissions=True)

    closed_summary = ", ".join(f"{detail}: {qty:g}" for detail, qty in close_lines)
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "Stock Entry",
        "reference_name": source.name,
        "content": (
            "Automatic 10-day return-window closure. No stock movement was created. "
            f"Posting date {posting_date}; deadline {due_date}; undeclared balances closed: {closed_summary}."
        ),
    }).insert(ignore_permissions=True)

    rollup.recompute_return_state(source.name)
    for mr_name in rollup._linked_mr_names(source):
        rollup.recompute_mr_lifecycle_state(mr_name)
    return "closed"


def close_expired_return_windows():
    """Close each eligible DN independently; stock and recorded allocations are untouched."""
    policy_started_at = frappe.db.get_value("SIG Dispatch Operation", POLICY_START_ID, "created_at")
    if not policy_started_at:
        frappe.log_error(
            title="SIG Warehouse return policy start is missing",
            message="No SIG-RETURN-WINDOW-POLICY-START operation was found; no DN was auto-closed.",
        )
        return

    today = get_datetime_in_timezone(POLICY_TIMEZONE).date()
    oldest_due_posting_date = add_days(today, -WINDOW_DAYS)
    candidates = frappe.get_all(
        "Stock Entry",
        filters={
            "docstatus": 1,
            "is_return": 0,
            "purpose": ["in", ["Material Issue", "Material Transfer"]],
            "posting_date": ["<", oldest_due_posting_date],
            "creation": [">=", policy_started_at],
        },
        fields=["name"],
        order_by="posting_date asc, name asc",
        limit_page_length=0,
    )

    counts = {}
    for candidate in candidates:
        try:
            outcome = _close_due_dn(candidate.name, policy_started_at, today)
            counts[outcome] = counts.get(outcome, 0) + 1
            # Commit per DN so its row lock is released and any audit-only
            # backdated-review note survives a later candidate failure.
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(
                title=f"SIG Warehouse return auto-close failed: {candidate.name}",
                message=frappe.get_traceback(),
            )
            counts["failed"] = counts.get("failed", 0) + 1

    frappe.logger("sig_warehouse").info("10-day return closure: %s", counts)
