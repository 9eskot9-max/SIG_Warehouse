"""sig_dispatch_tool: standalone tool/equipment custody dispatch.

Deliberately separate from sig_dispatch_mr (Material Request issuing): a
tool going out to a person is not linked to a site/project/Material Request
the way consumable material issuing is (9A.9 owner decision) - it is a real
stock movement (Material Issue, no material_request reference) paired
immediately with a custody declaration, in one step. Contrast with
disposition.sig_declare_disposition's CUSTODY action, which declares
custody against an *already-dispatched* DN line after the fact; this module
creates the dispatch and the custody record together since there is no
prior DN here.

Custodian is either a real Employee (Link, reportable) or a free-text
"Other" person (name + phone, no Employee record) - a contractor or anyone
else outside the Employee list. Both share the same SIG IH Event/Position
ledger as the existing disposition-based custody flow; a non-Employee
custodian is given a stable synthetic key ("OTHER:name:phone") in place of
an Employee id so two different outside people never collide into the same
SIG IH Position row.
"""
import hashlib

import frappe
from frappe import _

ALLOWED_ROLES = ("Stock Manager", "System Manager")
COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"


def _authorize(warehouse):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not authenticated"), frappe.PermissionError)
    roles = frappe.get_roles(user)
    if not any(r in ALLOWED_ROLES for r in roles):
        frappe.throw(_("Not authorized to dispatch"), frappe.PermissionError)
    if not frappe.has_permission("Warehouse", "write", doc=warehouse, user=user):
        frappe.throw(_("Not permitted to dispatch from {0}").format(warehouse), frappe.PermissionError)


def _signature(item_code, qty, from_wh, custodian_key):
    parts = [item_code, str(qty), from_wh, custodian_key]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


@frappe.whitelist()
def sig_dispatch_tool(operation_id, item_code, qty, from_wh, custodian_type,
                       custodian=None, custodian_name=None, custodian_phone=None,
                       reason=None, posting_date=None):
    if not operation_id or not item_code or not from_wh:
        return {"result": "exception", "reason": "operation_id/item_code/from_wh required"}
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        qty = -1
    if qty <= 0:
        return {"result": "exception", "reason": "invalid qty"}

    custodian_type = (custodian_type or "Employee").strip()
    if custodian_type not in ("Employee", "Other"):
        return {"result": "exception", "reason": "invalid custodian_type"}

    if custodian_type == "Employee":
        if not custodian:
            return {"result": "exception", "reason": "custodian (Employee) required"}
        resolved_name = frappe.db.get_value("Employee", custodian, "employee_name") or custodian
        custodian_key = custodian
        custodian_phone = None
    else:
        custodian_name = (custodian_name or "").strip()
        if not custodian_name:
            return {"result": "exception", "reason": "custodian_name required for Other"}
        resolved_name = custodian_name
        custodian = None
        custodian_key = f"OTHER:{custodian_name}:{(custodian_phone or '').strip()}"

    _authorize(from_wh)

    if not frappe.db.exists("Item", item_code):
        return {"result": "exception", "reason": "UNKNOWN_ITEM", "item": item_code}

    sig = _signature(item_code, qty, from_wh, custodian_key)
    existing = frappe.db.get_value(
        "SIG Dispatch Operation", {"operation_id": operation_id},
        ["name", "signature", "stock_entry"], as_dict=True,
    )
    if existing:
        if existing.signature != sig:
            return {"result": "conflict", "operation_id": operation_id}
        return {"result": "duplicate", "operation_id": operation_id, "stock_entry": existing.stock_entry}

    item_uom = frappe.db.get_value("Item", item_code, "stock_uom")
    detail = {
        "item_code": item_code, "qty": qty, "uom": item_uom,
        "s_warehouse": from_wh, "cost_center": "Main - SIG",
    }
    rate = frappe.db.get_value(
        "Stock Ledger Entry", {"item_code": item_code, "warehouse": from_wh, "is_cancelled": 0},
        "valuation_rate", order_by="posting_date desc, creation desc",
    )
    if not rate:
        detail["allow_zero_valuation_rate"] = 1

    se = frappe.get_doc({
        "doctype": "Stock Entry", "stock_entry_type": "Material Issue", "purpose": "Material Issue",
        "company": COMPANY,
        "posting_date": posting_date or frappe.utils.nowdate(),
        "set_posting_time": 1 if posting_date else 0,
        "remarks": (reason or "SIG tool dispatch (custody)") + f" | operation {operation_id}",
        "items": [detail],
    })
    se.insert(ignore_permissions=False)
    se.submit()
    frappe.db.commit()

    sed_name = se.items[0].name
    event_id = f"{operation_id}-{sed_name}"
    frappe.get_doc({
        "doctype": "SIG IH Event", "event_id": event_id, "event_type": "OPEN",
        "occurred_at": frappe.utils.now(), "custodian_type": custodian_type,
        "custodian": custodian, "custodian_name": resolved_name, "custodian_phone": custodian_phone,
        "item_code": item_code, "qty": qty, "condition": "Serviceable",
        "source_stock_entry": se.name, "source_se_detail": sed_name,
        "operator": frappe.session.user, "source_sub": operation_id, "remarks": reason,
    }).insert(ignore_permissions=True)

    position_key = f"{custodian_key}|{item_code}|Serviceable"
    existing_qty = frappe.db.get_value("SIG IH Position", position_key, "qty_open")
    if existing_qty is not None:
        frappe.db.set_value("SIG IH Position", position_key, {
            "qty_open": float(existing_qty) + qty,
            "last_event_at": frappe.utils.now(), "last_source_se": se.name,
        }, update_modified=False)
    else:
        frappe.get_doc({
            "doctype": "SIG IH Position", "position_key": position_key, "custodian_type": custodian_type,
            "custodian": custodian, "custodian_name": resolved_name, "custodian_phone": custodian_phone,
            "item_code": item_code, "condition": "Serviceable",
            "qty_open": qty, "last_event_at": frappe.utils.now(), "last_source_se": se.name,
        }).insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.get_doc({
        "doctype": "SIG Dispatch Operation", "operation_id": operation_id, "op_type": "DISPOSITION",
        "action": "CUSTODY", "stock_entry": se.name, "operator": frappe.session.user,
        "state": "SUBMITTED", "signature": sig, "line_count": 1, "created_at": frappe.utils.now(),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "result": "created", "operation_id": operation_id, "stock_entry": se.name,
        "custodian_name": resolved_name,
    }
