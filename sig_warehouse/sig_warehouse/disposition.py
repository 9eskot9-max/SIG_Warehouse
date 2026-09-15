"""sig_declare_disposition: the Stage 3 return/custody declaration endpoint.

Implements the outstanding piece of 9A.7 - routes a RETURN by the ORIGINAL
DN's own ERPNext movement type (Material Issue -> Material Receipt into the
same store; Material Transfer -> Material Transfer back), never by a raw
label. CUSTODY is always a non-stock bookkeeping event (SIG IH Event/
Position) regardless of whether the original line already sits in real
inventory (BI/Material Transfer) or was already expensed (Material Issue) -
the Material Issue/Transfer already moved the stock; custody is a record of
who is holding it, not a second movement. CLOSE marks a line's remaining gap
as intentionally exhausted (WH's own 'Closed? = 1').

Scope note: this first pass covers RETURN/CUSTODY/CLOSE - the three-way
disposition the warehouse's own Manage Return flow already uses (Return/
In-Hand/Closed). CONSUME and REASSIGN (operating on an existing SIG IH
Position rather than the original DN line) are designed in 9A.9 but not
built in this pass - deliberately scoped to what was actually asked for.
"""
import hashlib

import frappe

from sig_warehouse.sig_warehouse import rollup

ALLOWED_ACTIONS = ("RETURN", "CUSTODY", "CLOSE")
ALLOWED_ROLES = ("Stock Manager", "System Manager")
COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"
EPS = 1e-6


def _signature(source_se, action, lines):
    parts = [source_se, action]
    for line in sorted(lines, key=lambda x: x["sed"]):
        parts.append(f"{line['sed']}:{line.get('qty', '')}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _authorize(source_doc, warehouse=None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not authenticated", frappe.PermissionError)
    roles = frappe.get_roles(user)
    if not any(r in ALLOWED_ROLES for r in roles):
        frappe.throw("Not authorized to declare disposition", frappe.PermissionError)
    if source_doc.docstatus != 1:
        frappe.throw("Source Stock Entry is not submitted", frappe.ValidationError)
    if source_doc.is_return:
        frappe.throw("Source Stock Entry is itself a return - not eligible", frappe.ValidationError)
    if source_doc.purpose not in ("Material Issue", "Material Transfer"):
        frappe.throw("Source Stock Entry purpose not eligible for disposition", frappe.ValidationError)
    if warehouse and not frappe.has_permission("Warehouse", "write", doc=warehouse, user=user):
        frappe.throw(f"Not permitted to declare disposition for {warehouse}", frappe.PermissionError)


def _parse_lines(line_count, form):
    lines = []
    for i in range(1, int(line_count or 0) + 1):
        sed = form.get(f"sed_{i}")
        if not sed:
            continue
        qty_raw = form.get(f"qty_{i}")
        qty = None
        if qty_raw not in (None, ""):
            try:
                qty = float(qty_raw)
            except (TypeError, ValueError):
                frappe.throw(f"Invalid qty on line {i}: {qty_raw}", frappe.ValidationError)
        lines.append({"sed": sed, "qty": qty})
    return lines


def _load_source_details(source_se, sed_names):
    rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"name": ["in", sed_names], "parent": source_se, "parenttype": "Stock Entry"},
        fields=[
            "name", "item_code", "qty", "uom", "s_warehouse", "t_warehouse", "custom_row_key",
            "custom_qty_returned", "custom_qty_custody", "custom_return_closed",
        ],
    )
    return {row.name: row for row in rows}


@frappe.whitelist()
def sig_declare_disposition(operation_id, action, source_se, line_count=0, to_wh=None,
                             custodian=None, reason=None, posting_date=None, **kwargs):
    action = (action or "").upper().strip()
    if action not in ALLOWED_ACTIONS:
        return {"result": "exception", "reason": "INVALID_ACTION", "action": action}
    if not operation_id or not source_se:
        return {"result": "exception", "reason": "operation_id/source_se required"}

    lines = _parse_lines(line_count, kwargs)
    if not lines:
        return {"result": "exception", "reason": "no lines"}

    source_doc = frappe.get_doc("Stock Entry", source_se)
    warehouse_for_auth = to_wh if action == "RETURN" else None
    _authorize(source_doc, warehouse_for_auth)

    sig = _signature(source_se, action, lines)
    existing = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "signature", "stock_entry"], as_dict=True,
    )
    if existing:
        if existing.signature != sig:
            return {"result": "conflict", "operation_id": operation_id}
        return {"result": "duplicate", "operation_id": operation_id, "stock_entry": existing.stock_entry}

    details = _load_source_details(source_se, [line["sed"] for line in lines])
    for line in lines:
        row = details.get(line["sed"])
        if not row:
            return {"result": "exception", "reason": "UNKNOWN_LINE", "line": line["sed"]}
        if row.custom_return_closed:
            return {"result": "exception", "reason": "LINE_CLOSED", "line": line["sed"]}
        if action in ("RETURN", "CUSTODY"):
            qty = line["qty"]
            if qty is None or qty <= 0:
                return {"result": "exception", "reason": "QTY_REQUIRED", "line": line["sed"]}
            allocated = float(row.custom_qty_returned or 0) + float(row.custom_qty_custody or 0)
            remaining = float(row.qty) - allocated
            if qty - remaining > EPS:
                return {"result": "exception", "reason": "CAP_EXCEEDED", "line": line["sed"],
                         "requested": qty, "remaining": remaining}

    stock_entry_name = None
    if action == "RETURN":
        if not to_wh:
            return {"result": "exception", "reason": "to_wh required for RETURN"}
        if source_doc.purpose == "Material Issue":
            new_purpose = "Material Receipt"
        else:
            new_purpose = "Material Transfer"

        items = []
        for line in lines:
            row = details[line["sed"]]
            item = {
                "item_code": row.item_code, "qty": line["qty"], "uom": row.uom,
                "custom_original_stock_entry": source_se, "custom_original_se_detail": row.name,
            }
            if row.custom_row_key:
                item["custom_row_key"] = row.custom_row_key
            if new_purpose == "Material Receipt":
                item["t_warehouse"] = row.s_warehouse
            else:
                item["s_warehouse"] = row.t_warehouse
                item["t_warehouse"] = row.s_warehouse
            items.append(item)

        return_se = frappe.get_doc({
            "doctype": "Stock Entry", "stock_entry_type": new_purpose, "purpose": new_purpose,
            "company": COMPANY, "is_return": 1, "custom_return_against_se": source_se,
            "posting_date": posting_date or frappe.utils.nowdate(),
            "set_posting_time": 1 if posting_date else 0,
            "remarks": (reason or "SIG Warehouse return") + f" | operation {operation_id}",
            "items": items,
        })
        return_se.insert(ignore_permissions=False)
        return_se.submit()
        frappe.db.commit()
        stock_entry_name = return_se.name

        for line in lines:
            row = details[line["sed"]]
            new_returned = float(row.custom_qty_returned or 0) + line["qty"]
            frappe.db.set_value("Stock Entry Detail", line["sed"], "custom_qty_returned", new_returned, update_modified=False)

    elif action == "CUSTODY":
        if not custodian:
            return {"result": "exception", "reason": "custodian required"}
        custodian_name = frappe.db.get_value("Employee", custodian, "employee_name") or custodian
        for line in lines:
            row = details[line["sed"]]
            event_id = f"{operation_id}-{line['sed']}"
            if not frappe.db.exists("SIG IH Event", event_id):
                frappe.get_doc({
                    "doctype": "SIG IH Event", "event_id": event_id, "event_type": "OPEN",
                    "occurred_at": frappe.utils.now(), "custodian": custodian, "custodian_name": custodian_name,
                    "item_code": row.item_code, "qty": line["qty"], "condition": "Serviceable",
                    "source_stock_entry": source_se, "source_se_detail": row.name,
                    "source_row_key": row.custom_row_key, "operator": frappe.session.user,
                    "source_sub": operation_id, "remarks": reason,
                }).insert(ignore_permissions=True)
            position_key = f"{custodian}|{row.item_code}|Serviceable"
            existing_qty = frappe.db.get_value("SIG IH Position", position_key, "qty_open")
            if existing_qty is not None:
                frappe.db.set_value("SIG IH Position", position_key, {
                    "qty_open": float(existing_qty) + line["qty"],
                    "last_event_at": frappe.utils.now(), "last_source_se": source_se,
                }, update_modified=False)
            else:
                frappe.get_doc({
                    "doctype": "SIG IH Position", "position_key": position_key, "custodian": custodian,
                    "custodian_name": custodian_name, "item_code": row.item_code, "condition": "Serviceable",
                    "qty_open": line["qty"], "last_event_at": frappe.utils.now(), "last_source_se": source_se,
                }).insert(ignore_permissions=True)
            new_custody = float(row.custom_qty_custody or 0) + line["qty"]
            frappe.db.set_value("Stock Entry Detail", line["sed"], "custom_qty_custody", new_custody, update_modified=False)
        frappe.db.commit()

    elif action == "CLOSE":
        for line in lines:
            frappe.db.set_value("Stock Entry Detail", line["sed"], "custom_return_closed", 1, update_modified=False)
        frappe.db.commit()

    return_state = rollup.recompute_return_state(source_se)

    frappe.get_doc({
        "doctype": "SIG Dispatch Operation", "operation_id": operation_id, "op_type": "DISPOSITION",
        "action": action, "source_se": source_se, "stock_entry": stock_entry_name,
        "operator": frappe.session.user, "state": "SUBMITTED", "signature": sig,
        "line_count": len(lines), "created_at": frappe.utils.now(),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "result": "created", "operation_id": operation_id, "action": action,
        "stock_entry": stock_entry_name, "lines": len(lines), "return_state": return_state,
    }


@frappe.whitelist()
def sig_check_disposition_status(operation_id):
    row = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "state", "stock_entry", "source_se", "action"], as_dict=True,
    )
    if not row:
        return {"state": "not_found"}
    return {"state": "submitted" if row.state == "SUBMITTED" else "failed",
            "stock_entry": row.stock_entry, "source_se": row.source_se, "action": row.action}
