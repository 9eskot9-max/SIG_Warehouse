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
                     dispatched_to_other=None, initiated_by=None, remarks=None,
                     line_count=0, **kwargs):
    if not operation_id or not mr or not from_wh:
        return {"result": "exception", "reason": "operation_id/mr/from_wh required"}

    lines = _parse_lines(line_count, kwargs)
    if not lines:
        return {"result": "exception", "reason": "no DISPATCH lines"}

    mr_doc = frappe.get_doc("Material Request", mr)
    warehouse = WH_MAP.get(from_wh, from_wh)
    _authorize(mr_doc, warehouse)

    dispatched_to = str(dispatched_to or "").strip()
    dispatched_to_other = str(dispatched_to_other or "").strip()
    if bool(dispatched_to) == bool(dispatched_to_other):
        return {"result": "exception", "reason": "RECIPIENT_REQUIRED",
                "detail": "Select one Employee or enter an Other recipient."}
    if dispatched_to and not frappe.db.exists("Employee", dispatched_to):
        return {"result": "exception", "reason": "RECIPIENT_EMPLOYEE_NOT_FOUND",
                "employee": dispatched_to}

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

    dispatch_remarks = (remarks or "SIG Warehouse dispatch") + f" | operation {operation_id}"
    if dispatched_to_other:
        dispatch_remarks += f" | dispatched to other: {dispatched_to_other}"
    se = frappe.get_doc({
        "doctype": "Stock Entry", "stock_entry_type": "Material Issue", "purpose": "Material Issue",
        "company": COMPANY,
        "posting_date": posting_date or frappe.utils.nowdate(),
        "set_posting_time": 1 if posting_date else 0,
        "remarks": dispatch_remarks,
        "items": items,
    })
    if dispatched_to:
        se.custom_dispatched_to = dispatched_to
    elif dispatched_to_other and frappe.get_meta("Stock Entry").has_field("custom_dispatched_to_other"):
        se.custom_dispatched_to_other = dispatched_to_other
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

    whatsapp_notify = _notify_dispatch_whatsapp(lines, se.name)

    return {
        "result": "created", "operation_id": operation_id, "stock_entry": se.name,
        "dn_voucher": dn_voucher,
        "lines": len(items), "readback_ok": len(se.items) == len(items), "mr_state": mr_state,
        "whatsapp_notify": whatsapp_notify,
    }


def _notify_dispatch_whatsapp(lines, stock_entry_name):
    """Best-effort default: send the DN print to WhatsApp after a successful
    dispatch, group resolved by the dispatch's project text (Maytapi Settings
    > Dispatch Recipients, matched case-insensitive startswith) - mirrors
    WH's own MaytapiSend.bas ResolveGroupIdForProject exactly (DNs go to a
    WhatsApp GROUP resolved from the line's Project text, not the
    warehouse). Uses the first dispatched line's Material Request Item
    custom_source_project_name, matching VBA's single projectText parameter
    for the whole DN. Never raises - a WhatsApp failure must not block, fail,
    or reverse an already-submitted, already-committed Stock Entry; that
    would make a side-channel notification a hard dependency of the actual
    stock movement, which it isn't. Silently a no-op if SIG WhatsApp isn't
    installed, disabled, or the project text matches no configured prefix
    (WH's own VBA prompts the operator in that case; there is no interactive
    operator here, so it is logged and skipped rather than sent blind).
    """
    try:
        if not frappe.db.exists("DocType", "Maytapi Settings"):
            return {"sent": False, "reason": "sig_whatsapp not installed"}
        settings = frappe.get_single("Maytapi Settings")
        if not settings.enabled or not settings.dispatch_notify_enabled:
            return {"sent": False, "reason": "disabled"}
        if not lines:
            return {"sent": False, "reason": "no dispatched lines"}
        project_text = frappe.db.get_value(
            "Material Request Item", lines[0]["mri"], "custom_source_project_name"
        ) or ""
        project_text = project_text.strip().lower()
        if not project_text:
            return {"sent": False, "reason": "dispatched line has no project text"}
        recipient = next(
            (row.recipient for row in (settings.dispatch_recipients or [])
             if row.project_prefix and project_text.startswith(row.project_prefix.strip().lower())),
            None,
        )
        if not recipient:
            return {"sent": False, "reason": f"project text '{project_text}' matched no configured group"}
        from sig_whatsapp.maytapi import send_document
        result = send_document("Stock Entry", stock_entry_name, to=recipient)
        return {"sent": True, "status": result.get("status"), "message_id": result.get("message_id")}
    except Exception as e:
        frappe.log_error(title="SIG Warehouse: dispatch WhatsApp notify failed", message=frappe.get_traceback())
        return {"sent": False, "reason": str(e)[:200]}


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


@frappe.whitelist()
def sig_add_mr_line(mr, item_code, qty, uom=None, site=None, project=None):
    """Append a new line to an already-submitted Material Issue MR, so the
    Issue dialog can offer 'add an item that wasn't on the original request'
    without a separate MR-editing flow. A direct child-row insert (not
    mr_doc.save()) because Material Request's items table isn't
    allow_on_submit for a fresh row - same "act on the row directly, not
    through the parent's submit-guard" approach this app already uses
    elsewhere for submitted-doc gaps (see rollup.py). The caller (the Issue
    dialog) only calls this at the moment of Confirm, for items the operator
    chose to keep - anything added-then-removed in the dialog never reaches
    here, so there's nothing to clean up on a change of mind.
    """
    if not mr or not item_code:
        return {"result": "exception", "reason": "mr/item_code required"}
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        qty = -1
    if qty <= 0:
        return {"result": "exception", "reason": "invalid qty"}

    mr_doc = frappe.get_doc("Material Request", mr)
    if mr_doc.docstatus != 1:
        return {"result": "exception", "reason": "Material Request is not submitted"}
    if mr_doc.material_request_type != "Material Issue":
        return {"result": "exception", "reason": "Not a Material Issue request"}

    warehouse = mr_doc.set_warehouse
    if not warehouse:
        return {"result": "exception", "reason": "MR has no warehouse set"}
    _authorize(mr_doc, warehouse)

    if not frappe.db.exists("Item", item_code):
        return {"result": "exception", "reason": "UNKNOWN_ITEM", "item": item_code}

    # Material Request Item has mandatory stock_uom/conversion_factor fields.
    # The dialog normally supplies the item's stock UOM, but this endpoint is
    # also callable directly and must not rely on the client-side item-detail
    # fill. Resolve the requested UOM against the Item master so a new line is
    # valid on insert and remains correct for any alternate UOM the item owns.
    item_doc = frappe.get_doc("Item", item_code)
    stock_uom = str(item_doc.stock_uom or "").strip()
    item_uom = str(uom or stock_uom).strip()
    conversion_factor = None
    if stock_uom and item_uom.casefold() == stock_uom.casefold():
        conversion_factor = 1.0
    else:
        for item_uom_row in (item_doc.uoms or []):
            candidate = str(item_uom_row.uom or "").strip()
            if candidate and candidate.casefold() == item_uom.casefold():
                conversion_factor = float(item_uom_row.conversion_factor or 0)
                break
    if not stock_uom or not item_uom or not conversion_factor or conversion_factor <= 0:
        return {"result": "exception", "reason": "UOM_CONVERSION_NOT_FOUND",
                "item": item_code, "uom": item_uom, "stock_uom": stock_uom}

    max_idx = frappe.db.sql(
        "SELECT MAX(idx) FROM `tabMaterial Request Item` WHERE parent=%s", mr
    )[0][0] or 0

    row = frappe.get_doc({
        "doctype": "Material Request Item", "parent": mr, "parentfield": "items",
        "parenttype": "Material Request", "idx": max_idx + 1,
        "item_code": item_code, "qty": qty, "uom": item_uom,
        "stock_uom": stock_uom, "conversion_factor": conversion_factor,
        "stock_qty": qty * conversion_factor,
        "warehouse": warehouse, "schedule_date": frappe.utils.nowdate(),
        "cost_center": "Main - SIG", "custom_site": site or mr_doc.get("custom_site"),
        "project": project,
    })
    row.insert(ignore_permissions=True)
    frappe.db.commit()

    mr_state = rollup.recompute_mr_dispatch_state(mr)
    frappe.clear_document_cache("Material Request", mr)

    return {"result": "created", "mri": row.name, "item_code": item_code, "uom": item_uom,
            "qty": qty, "mr_state": mr_state}


@frappe.whitelist()
def sig_cancel_mr_lines(operation_id, mr, line_count=0, **kwargs):
    """Mark remaining undispatched qty on one or more MR lines as no longer
    needed. No stock movement - only custom_qty_cancelled, which the rollup
    folds into custom_qty_remaining (recompute_mr_dispatch_state). Same
    idempotency/authorization shape as sig_dispatch_mr so it is safe to
    trigger from a UI action (e.g. the Kanban card menu) without special-case
    retry handling on the caller's side.
    """
    if not operation_id or not mr:
        return {"result": "exception", "reason": "operation_id/mr required"}

    lines = []
    for i in range(1, int(line_count or 0) + 1):
        mri = kwargs.get(f"mri_{i}")
        if not mri:
            continue
        qty_raw = kwargs.get(f"qty_{i}")
        try:
            qty = float(qty_raw or 0)
        except (TypeError, ValueError):
            qty = -1
        if qty <= 0:
            return {"result": "exception", "reason": f"Invalid qty on line {i}: {qty_raw}"}
        lines.append({"mri": mri, "qty": qty})
    if not lines:
        return {"result": "exception", "reason": "no lines"}

    mr_doc = frappe.get_doc("Material Request", mr)
    if mr_doc.docstatus != 1:
        return {"result": "exception", "reason": "Material Request is not submitted"}

    sig = _signature(mr, [{**l, "outcome": "CANCEL"} for l in lines])
    existing = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "signature"], as_dict=True,
    )
    if existing:
        if existing.signature != sig:
            return {"result": "conflict", "operation_id": operation_id}
        return {"result": "duplicate", "operation_id": operation_id}

    mri_names = [line["mri"] for line in lines]
    mri_rows = {
        row.name: row for row in frappe.get_all(
            "Material Request Item", filters={"name": ["in", mri_names]},
            fields=["name", "warehouse", "custom_qty_remaining", "custom_qty_cancelled"],
        )
    }
    for line in lines:
        row = mri_rows.get(line["mri"])
        if not row:
            return {"result": "exception", "reason": "UNKNOWN_LINE", "line": line["mri"]}
        warehouse = WH_MAP.get(row.warehouse, row.warehouse)
        _authorize(mr_doc, warehouse)
        remaining = float(row.custom_qty_remaining or 0)
        if line["qty"] - remaining > EPS:
            return {"result": "exception", "reason": "CAP_EXCEEDED", "line": line["mri"],
                     "requested": line["qty"], "remaining": remaining}

    for line in lines:
        row = mri_rows[line["mri"]]
        new_cancelled = float(row.custom_qty_cancelled or 0) + line["qty"]
        frappe.db.set_value("Material Request Item", line["mri"], "custom_qty_cancelled", new_cancelled, update_modified=False)
        frappe.clear_document_cache("Material Request Item", line["mri"])

    mr_state = rollup.recompute_mr_dispatch_state(mr)  # also clears the MR's document cache

    frappe.get_doc({
        "doctype": "SIG Dispatch Operation", "operation_id": operation_id, "op_type": "CANCEL",
        "action": "CANCEL", "mr": mr, "operator": frappe.session.user, "state": "SUBMITTED",
        "signature": sig, "line_count": len(lines), "created_at": frappe.utils.now(),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {"result": "created", "operation_id": operation_id, "lines": len(lines), "mr_state": mr_state}


@frappe.whitelist()
def sig_kanban_availability_status(mrs):
    """Per-MR stock-availability traffic light for the Kanban board.

    green: every open (undispatched-remaining) line is covered by its own
    warehouse's current Bin qty. yellow: not fully covered locally, but every
    short line has enough qty somewhere else in the system. red: at least one
    open line has no warehouse - own or otherwise - holding enough. A card
    with no open lines (fully dispatched/cancelled) is left out of the result
    entirely; the caller treats "no entry" as "no light".
    """
    if isinstance(mrs, str):
        mrs = frappe.parse_json(mrs)
    mrs = [m for m in (mrs or []) if m]
    if not mrs:
        return {}

    mri_rows = frappe.get_all(
        "Material Request Item",
        filters={"parent": ["in", mrs]},
        fields=["parent", "item_code", "warehouse", "custom_qty_remaining"],
    )
    open_rows = [r for r in mri_rows if float(r.custom_qty_remaining or 0) > EPS]
    if not open_rows:
        return {}

    item_codes = list({r.item_code for r in open_rows})
    bins = frappe.get_all(
        "Bin", filters={"item_code": ["in", item_codes]},
        fields=["item_code", "warehouse", "actual_qty"],
    )
    qty_by_item_wh = {(b.item_code, b.warehouse): float(b.actual_qty or 0) for b in bins}
    qty_by_item = {}
    for b in bins:
        qty_by_item.setdefault(b.item_code, {})[b.warehouse] = float(b.actual_qty or 0)

    by_mr = {}
    for r in open_rows:
        by_mr.setdefault(r.parent, []).append(r)

    result = {}
    for mr, rows in by_mr.items():
        covered_locally = True
        covered_elsewhere = True
        for r in rows:
            remaining = float(r.custom_qty_remaining or 0)
            own_qty = qty_by_item_wh.get((r.item_code, r.warehouse), 0.0)
            if own_qty + EPS >= remaining:
                continue
            covered_locally = False
            best_other = max(
                (qty for wh, qty in qty_by_item.get(r.item_code, {}).items() if wh != r.warehouse),
                default=0.0,
            )
            if best_other + EPS < remaining:
                covered_elsewhere = False
        result[mr] = "green" if covered_locally else ("yellow" if covered_elsewhere else "red")

    return result

