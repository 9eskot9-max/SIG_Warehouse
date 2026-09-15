"""Pure planning/identity helpers for Stage 5 bulk MR dispatch.

The live single-MR ``sig_dispatch_mr`` endpoint remains the stock-writing
authority.  This module only validates and fingerprints a bulk request so a
future transaction wrapper can call the same server-side line-cap and submit
logic exactly once.  It deliberately has no Frappe imports and no writes.
"""

import hashlib
import json
import math


def _qty(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {label}")
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def normalize_bulk_lines(lines):
    if not lines:
        raise ValueError("at least one dispatch line is required")
    normalized = []
    seen = set()
    warehouses = set()
    uoms = set()
    for line in lines:
        mr = str(line.get("mr") or "").strip()
        mri = str(line.get("mri") or "").strip()
        warehouse = str(line.get("warehouse") or "").strip()
        uom = str(line.get("uom") or "").strip()
        if not mr or not mri or not warehouse or not uom:
            raise ValueError("mr, mri, warehouse and uom are required")
        key = (mr, mri)
        if key in seen:
            raise ValueError(f"duplicate material request line: {mri}")
        seen.add(key)
        warehouses.add(warehouse)
        uoms.add(uom)
        normalized.append({
            "mr": mr,
            "mri": mri,
            "warehouse": warehouse,
            "uom": uom,
            "qty": _qty(line.get("qty"), f"quantity for {mri}"),
            "outcome": str(line.get("outcome") or "DISPATCH").upper(),
            "rowkey": str(line.get("rowkey") or "").strip() or None,
        })
    if len(warehouses) != 1:
        raise ValueError("bulk dispatch cannot mix warehouses")
    if len(uoms) != 1:
        raise ValueError("bulk dispatch cannot mix UOMs")
    invalid = [line for line in normalized if line["outcome"] != "DISPATCH"]
    if invalid:
        raise ValueError("bulk dispatch accepts DISPATCH lines only")
    return sorted(normalized, key=lambda row: (row["mr"], row["mri"]))


def bulk_signature(operation_id, lines):
    if not str(operation_id or "").strip():
        raise ValueError("operation_id is required")
    canonical = json.dumps(
        normalize_bulk_lines(lines), sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(f"{operation_id}|{canonical}".encode("utf-8")).hexdigest()


def retry_result(operation_id, incoming_signature, stored_signature, stored_result):
    """Return duplicate/conflict semantics for a retried bulk operation."""
    if incoming_signature != stored_signature:
        return {"result": "conflict", "operation_id": operation_id}
    result = dict(stored_result or {})
    result.update({"result": "duplicate", "operation_id": operation_id})
    return result


def build_bulk_plan(operation_id, lines):
    normalized = normalize_bulk_lines(lines)
    return {
        "operation_id": operation_id,
        "warehouse": normalized[0]["warehouse"],
        "uom": normalized[0]["uom"],
        "lines": normalized,
        "signature": bulk_signature(operation_id, normalized),
    }
