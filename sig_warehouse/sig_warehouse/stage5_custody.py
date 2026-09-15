"""Pure Stage 5 custody transition rules over the Stage 3 event vocabulary.

The helpers accept the future Stage 5 names but normalize them to the event
semantics already used by ``SIG IH Event``.  They do not write ERP stock or
ledger documents.
"""

import math

EVENT_DELTAS = {
    "OPEN": 1,
    "ISSUED": 1,
    "REASSIGN_IN": 1,
    "RETURN": -1,
    "RETURNED": -1,
    "USE": -1,
    "CONSUMED": -1,
    "LOST": -1,
    "RECONCILED": -1,
    "REASSIGN_OUT": -1,
}

CONDITIONS = ("SERVICEABLE", "DAMAGED", "LOST", "QUARANTINED")
_CONDITION_ALIASES = {
    "SERVICEABLE": "SERVICEABLE",
    "DAMAGED": "DAMAGED",
    "UNSERVICEABLE": "QUARANTINED",
    "QUARANTINED": "QUARANTINED",
    "LOST": "LOST",
}


def _finite_qty(qty):
    try:
        amount = float(qty)
    except (TypeError, ValueError):
        raise ValueError("custody event quantity must be numeric")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("custody event quantity must be positive")
    return amount


def apply_custody_event(current_qty, event_type, qty):
    if event_type not in EVENT_DELTAS:
        raise ValueError(f"unsupported custody event: {event_type}")
    amount = _finite_qty(qty)
    current = float(current_qty)
    if not math.isfinite(current) or current < 0:
        raise ValueError("current custody position must be non-negative")
    result = current + EVENT_DELTAS[event_type] * amount
    if result < -1e-6:
        raise ValueError("custody position cannot become negative")
    return max(0.0, result)


def validate_condition(condition):
    key = str(condition or "").strip().upper()
    if key not in _CONDITION_ALIASES:
        raise ValueError("condition must use SERVICEABLE, DAMAGED, LOST or QUARANTINED")
    return _CONDITION_ALIASES[key]


def validate_custody_identity(*, custodian, item_code, source_line, qty,
                              condition="SERVICEABLE", lot_no=None, serial_no=None,
                              tracking="NONE"):
    """Validate one advanced-custody allocation before a future write path."""
    if not str(custodian or "").strip():
        raise ValueError("custodian is required")
    if not str(item_code or "").strip():
        raise ValueError("item_code is required")
    if not str(source_line or "").strip():
        raise ValueError("source line is required")
    amount = _finite_qty(qty)
    normalized_condition = validate_condition(condition)
    tracking = str(tracking or "NONE").strip().upper()
    if tracking == "SERIAL" and not str(serial_no or "").strip():
        raise ValueError("serial number is required for a serial-tracked item")
    if tracking == "BATCH" and not str(lot_no or "").strip():
        raise ValueError("lot number is required for a batch-tracked item")
    if tracking not in ("NONE", "SERIAL", "BATCH"):
        raise ValueError("tracking must be NONE, SERIAL or BATCH")
    return {
        "custodian": str(custodian).strip(),
        "item_code": str(item_code).strip(),
        "source_line": str(source_line).strip(),
        "qty": amount,
        "condition": normalized_condition,
        "lot_no": str(lot_no or "").strip() or None,
        "serial_no": str(serial_no or "").strip() or None,
        "tracking": tracking,
    }


def position_key(custodian, item_code, condition="SERVICEABLE", lot_no=None, serial_no=None):
    """Stable key for a Stage 5 position; no second stock balance is implied."""
    return "|".join([
        str(custodian or "").strip(),
        str(item_code or "").strip(),
        validate_condition(condition),
        str(lot_no or "").strip(),
        str(serial_no or "").strip(),
    ])


def ensure_allocation_within_issued(issued, returned=0, custody=0, consumed=0, additional=0):
    """Ensure a new custody/return allocation cannot exceed issued quantity."""
    raw_values = (issued, returned, custody, consumed, additional)
    values = []
    for value in raw_values:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            raise ValueError("allocation quantities must be numeric")
        if not math.isfinite(number) or number < 0:
            raise ValueError("allocation quantities must be non-negative")
        values.append(number)
    issued_qty, returned_qty, custody_qty, consumed_qty, additional_qty = values
    if returned_qty + custody_qty + consumed_qty + additional_qty > issued_qty + 1e-6:
        raise ValueError("custody/return allocation exceeds issued quantity")
    return issued_qty - returned_qty - custody_qty - consumed_qty - additional_qty
