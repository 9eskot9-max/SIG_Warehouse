"""Pure, testable comparison used by the Stage 4 cutover package.

Rows are normalized to the stock UOM before this module sees them.  It is
intentionally independent of Frappe so the same result can be reproduced from
a frozen WH CSV before any ERP cutover document is updated.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def _quantity(value):
    try:
        return Decimal(str(value or "0").strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"Invalid quantity: {value!r}")


def normalize(rows):
    result = defaultdict(Decimal)
    for row in rows:
        item = str(row.get("item_code") or "").strip()
        warehouse = str(row.get("warehouse") or "").strip()
        if not item or not warehouse:
            raise ValueError("Every row needs item_code and warehouse")
        result[(item, warehouse)] += _quantity(row.get("qty"))
    return result


def compare(wh_rows, erp_rows):
    wh = normalize(wh_rows)
    erp = normalize(erp_rows)
    keys = sorted(set(wh) | set(erp))
    rows = []
    for item, warehouse in keys:
        wh_qty = wh.get((item, warehouse), Decimal())
        erp_qty = erp.get((item, warehouse), Decimal())
        rows.append({
            "item_code": item,
            "warehouse": warehouse,
            "wh_qty": str(wh_qty),
            "erp_qty": str(erp_qty),
            "difference": str(erp_qty - wh_qty),
            "match": erp_qty == wh_qty,
        })
    return rows


def summary(rows):
    return {
        "wh_line_count": len([row for row in rows if row["wh_qty"] != "0"]),
        "erp_line_count": len([row for row in rows if row["erp_qty"] != "0"]),
        "matched_line_count": sum(1 for row in rows if row["match"]),
        "mismatch_line_count": sum(1 for row in rows if not row["match"]),
    }
