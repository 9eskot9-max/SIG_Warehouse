"""sig_dispatch_mr: the atomic, submit-capable dispatch endpoint for the
SIG Warehouse Workbench (Stage 2). Separate from register_stock_entry (the
live WH VBA mirror) per 9A.9's writer-placement decision - different
authorization model (a real operator's own session, not a service key),
different identity family (operation_id, not a WH voucher).

DN26 voucher allocation (9A.9 decision 2): a Stock Entry created here gets a
real DN26-#### voucher (sig_warehouse.cutover.allocate_dn_voucher) only once
its warehouse has an ACTIVE, accepted Stage 4 cutover - allocating real DN26
numbers before WH's own VBA has stopped issuing them for a given warehouse
would risk a live numbering collision. Before that warehouse's cutover, the
Stock Entry gets no voucher and keeps ERPNext's own naming series only, same
as before Stage 4 existed.
"""
import hashlib

import frappe

from sig_warehouse.sig_warehouse import cutover, rollup

WH_MAP = {
    "Riyadh": "مستودع المزاحمية - SIG", "Ry": "مستودع المزاحمية - SIG",
    "Makkah": "مستودع مكة - SIG", "Mk": "مستودع مكة - SIG",
    "Jizan": "مستودع جازان - SIG", "Jz": "مستودع جازان - SIG",
    "Qasim": "مستودع القصيم - SIG", "Qs": "مستودع القصيم - SIG",
}
ALLOWED_DISPATCH_ROLES = ("Stock Manager", "System Manager")
COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"
EPS = 1e-6


def _signature(mr, lines):
    parts = [mr]
    for line in sorted(lines, key=lambda x: x["mri"]):
        parts.append(f"{line['mri']}:{line['qty']}:{line['outcome']}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _authorize(mr_doc, warehouse):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not authenticated", frappe.PermissionError)
    roles = frappe.get_roles(user)
    if not any(r in ALLOWED_DISPATCH_ROLES for r in roles):
        frappe.throw("Not authorized to dispatch", frappe.PermissionError)
    if mr_doc.docstatus != 1:
        frappe.throw("Material Request is not submitted", frappe.ValidationError)
    if mr_doc.material_request_type != "Material Issue":
        frappe.throw("Not a Material Issue request", frappe.ValidationError)
    if not frappe.has_permission("Warehouse", "write", doc=warehouse, user=user):
        frappe.throw(f"Not permitted to dispatch from {warehouse}", frappe.PermissionError)


def _parse_lines(line_count, form):
    lines = []
    for i in range(1, int(line_count or 0) + 1):
        mri = form.get(f"mri_{i}")
        outcome = form.get(f"outcome_{i}") or "DISPATCH"
        if not mri or outcome != "DISPATCH":
            continue
        qty_raw = form.get(f"qty_{i}")
        try:
            qty = float(qty_raw or 0)
        except (TypeError, ValueError):
            qty = -1
        if qty <= 0:
            frappe.throw(f"Invalid qty on line {i}: {qty_raw}", frappe.ValidationError)
        lines.append({"mri": mri, "qty": qty, "outcome": outcome, "rowkey": form.get(f"rowkey_{i}")})
    return lines


@frappe.whitelist()
def sig_dispatch_mr(operation_id, mr, from_wh, posting_date=None, dispatched_to=None,
                     initiated_by=None, remarks=None, line_count=0, **kwargs):
    if not operation_id or not mr or not from_wh:
        return {"result": "exception", "reason": "operation_id/mr/from_wh required"}

    lines = _parse_lines(line_count, kwargs)
    if not lines:
        return {"result": "exception", "reason": "no DISPATCH lines"}

    mr_doc = frappe.get_doc("Material Request", mr)
    warehouse = WH_MAP.get(from_wh, from_wh)
    _authorize(mr_doc, warehouse)

    sig = _signature(mr, lines)
    existing = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "signature", "stock_entry"], as_dict=True,
    )
    if existing:
        if existing.signature != sig:
            return {"result": "conflict", "operation_id": operation_id}
        return {"result": "duplicate", "operation_id": operation_id, "stock_entry": existing.stock_entry}

    mri_names = [line["mri"] for line in lines]
    mri_rows = {
        row.name: row for row in frappe.get_all(
            "Material Request Item", filters={"name": ["in", mri_names]},
            fields=["name", "item_code", "uom", "custom_qty_remaining"],
        )
    }
    for line in lines:
        row = mri_rows.get(line["mri"])
        if not row:
            return {"result": "exception", "reason": "UNKNOWN_LINE", "line": line["mri"]}
        remaining = float(row.custom_qty_remaining or 0)
        if line["qty"] - remaining > EPS:
            return {"result": "exception", "reason": "CAP_EXCEEDED", "line": line["mri"],
                     "requested": line["qty"], "remaining": remaining}

    items = []
    for line in lines:
        row = mri_rows[line["mri"]]
        detail = {
            "item_code": row.item_code, "qty": line["qty"], "uom": row.uom,
            "s_warehouse": warehouse, "material_request": mr, "material_request_item": line["mri"],
            "cost_center": "Main - SIG",
        }
        if line["rowkey"]:
            detail["custom_row_key"] = line["rowkey"]
        rate = frappe.db.get_value(
            "Stock Ledger Entry", {"item_code": row.item_code, "warehouse": warehouse, "is_cancelled": 0},
            "valuation_rate", order_by="posting_date desc, creation desc",
        )
        if not rate:
            detail["allow_zero_valuation_rate"] = 1
        items.append(detail)

    dn_voucher = None
    try:
        dn_voucher = cutover.allocate_dn_voucher(warehouse)
    except frappe.ValidationError as e:
        if "is not active" not in str(e):
            raise  # a real problem (e.g. counter never seeded) - do not swallow it

    se = frappe.get_doc({
        "doctype": "Stock Entry", "stock_entry_type": "Material Issue", "purpose": "Material Issue",
        "company": COMPANY,
        "posting_date": posting_date or frappe.utils.nowdate(),
        "set_posting_time": 1 if posting_date else 0,
        "remarks": (remarks or "SIG Warehouse dispatch") + f" | operation {operation_id}",
        "items": items,
    })
    if dn_voucher:
        se.custom_source_id = dn_voucher
    se.insert(ignore_permissions=False)
    se.submit()
    frappe.db.commit()  # commits the allocated voucher together with its Stock Entry, or not at all

    mr_state = rollup.recompute_mr_dispatch_state(mr)  # also clears the MR's document cache
    # the new dispatch SE itself needs its own clear - see rollup.py for why.
    frappe.clear_document_cache("Stock Entry", se.name)

    frappe.get_doc({
        "doctype": "SIG Dispatch Operation", "operation_id": operation_id, "mr": mr,
        "stock_entry": se.name, "operator": frappe.session.user, "state": "SUBMITTED",
        "signature": sig, "line_count": len(lines), "created_at": frappe.utils.now(),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "result": "created", "operation_id": operation_id, "stock_entry": se.name,
        "dn_voucher": dn_voucher,
        "lines": len(items), "readback_ok": len(se.items) == len(items), "mr_state": mr_state,
    }


@frappe.whitelist()
def sig_check_dispatch_status(operation_id):
    row = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "state", "stock_entry", "mr"], as_dict=True,
    )
    if not row:
        return {"state": "not_found"}
    return {"state": "submitted" if row.state == "SUBMITTED" else "failed",
            "stock_entry": row.stock_entry, "mr": row.mr}
