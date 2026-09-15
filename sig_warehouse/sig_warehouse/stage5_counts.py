"""Pure policy helpers for the future Stage 5 blind-count workflow.

These helpers deliberately do not read ERP or post Stock Reconciliation. The
future endpoint supplies the frozen book revision server-side and calls these
checks before creating a count batch.
"""
import math


COUNT_STATES = (
    "DRAFT", "ISSUED", "COUNTING", "REVIEW", "APPROVED", "POSTED", "CANCELLED",
)
_TRANSITIONS = {
    "DRAFT": {"ISSUED", "CANCELLED"},
    "ISSUED": {"COUNTING", "CANCELLED"},
    "COUNTING": {"REVIEW", "CANCELLED"},
    "REVIEW": {"APPROVED", "COUNTING", "CANCELLED"},
    "APPROVED": {"POSTED", "CANCELLED"},
    "POSTED": set(),
    "CANCELLED": set(),
}


def _finite_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {label}")
    if not math.isfinite(number):
        raise ValueError(f"invalid {label}")
    return number


def validate_state_transition(current, target):
    """Allow only the controlled count-batch lifecycle transitions."""
    if current not in COUNT_STATES or target not in COUNT_STATES:
        raise ValueError("unknown count batch state")
    if target not in _TRANSITIONS[current]:
        raise ValueError(f"invalid count state transition: {current} -> {target}")
    return target


def ensure_count_mutable(state):
    """Count values are editable only before the batch enters REVIEW."""
    if state not in ("DRAFT", "ISSUED", "COUNTING"):
        raise ValueError("count lines are immutable after submission")
    return True


def validate_counter_payload(rows, counter_user):
    """Validate the blind input; book values must never reach the counter UI."""
    if not counter_user or not rows:
        raise ValueError("counter and at least one count line are required")
    clean = []
    seen = set()
    for row in rows:
        if any(key in row for key in ("book_qty", "expected_qty", "variance")):
            raise ValueError("blind count payload must not contain book quantity or variance")
        item = str(row.get("item_code") or "").strip()
        warehouse = str(row.get("warehouse") or "").strip()
        if not item or not warehouse:
            raise ValueError("item_code and warehouse are required")
        key = (item, warehouse, str(row.get("bin") or "").strip())
        if key in seen:
            raise ValueError(f"duplicate count line for {item} in {warehouse}")
        seen.add(key)
        qty = _finite_number(row.get("count_qty"), f"count quantity for {item}")
        if qty < 0:
            raise ValueError(f"count quantity cannot be negative for {item}")
        clean.append({
            "item_code": item,
            "warehouse": warehouse,
            "bin": str(row.get("bin") or "").strip() or None,
            "count_qty": qty,
        })
    return clean


def approve_count(*, state, counter_user, approver_user, rows, threshold=0.0):
    """Return approved count lines after the supervisor separation check."""
    if state != "REVIEW":
        raise ValueError("only REVIEW batches can be approved")
    if not approver_user or approver_user == counter_user:
        raise ValueError("the counter cannot approve its own count")
    threshold = _finite_number(threshold, "variance threshold")
    if threshold < 0:
        raise ValueError("variance threshold cannot be negative")
    approved = []
    for row in rows:
        if row.get("variance") is None:
            raise ValueError("variance must be calculated from the frozen book revision")
        variance = _finite_number(row["variance"], "variance")
        approved.append({
            "item_code": row["item_code"], "warehouse": row["warehouse"],
            "bin": row.get("bin"),
            "qty": _finite_number(row["count_qty"], "count quantity"),
            "variance": variance,
            "recount_required": abs(variance) > threshold,
        })
    return approved


def build_reconciliation_items(batch_id, approved_rows, reason="SIG blind count"):
    """Build a Stock Reconciliation item payload without posting it.

    The caller must obtain the frozen book revision and supervisor decision on
    the server before using this payload.  The batch identity is retained in
    every row so a later Stock Reconciliation remains auditable.
    """
    if not batch_id or not approved_rows:
        raise ValueError("batch_id and approved rows are required")
    items = []
    for row in approved_rows:
        if row.get("recount_required"):
            raise ValueError("rows requiring recount cannot be posted")
        items.append({
            "item_code": row["item_code"],
            "warehouse": row["warehouse"],
            "qty": float(row["qty"]),
            "batch_id": batch_id,
            "reason": reason,
        })
    return items
