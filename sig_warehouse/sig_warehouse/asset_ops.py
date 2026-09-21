"""Asset dispatch/return: capitalized warehouse tools go out as a native Asset Movement.

Fixed-asset Items are non-stock in ERPNext, so there is no Stock Entry and no
SIG IH Position for them: the submitted Asset Movement is the only record, and
the Asset's custody fields are derived from it here. Consumable/non-capital
tools stay on custody.sig_dispatch_tool (which rejects fixed-asset Items).
"""
import hashlib

import frappe
from frappe import _

ALLOWED_ROLES = ("Stock Manager", "System Manager")
ISSUABLE_STATUSES = ("Submitted", "Partially Depreciated", "Fully Depreciated")
DEST_TYPES = ("Employee", "Site", "Subcontractor")
MOVEMENT_TYPE = {"Employee": "Issue to Employee", "Site": "Issue to Site/Project",
                 "Subcontractor": "Issue to Subcontractor"}
CUSTODY_STATUS = {"Employee": "Issued - Employee", "Site": "Issued - Site/Project",
                  "Subcontractor": "Issued - Subcontractor"}


def validate_dispatch(dest_type, employee=None, location=None, custody_status=None):
    """Pure rule check; returns an error string or None."""
    if dest_type not in DEST_TYPES:
        return "invalid destination type"
    if custody_status not in (None, "", "In Store", "Returned"):
        return f"asset is not in store (custody: {custody_status})"
    if dest_type == "Employee" and not employee:
        return "employee required"
    if dest_type != "Employee" and not location:
        return "destination location required"
    return None


def _authorize():
    user = frappe.session.user
    if user == "Guest" or not any(r in ALLOWED_ROLES for r in frappe.get_roles(user)):
        frappe.throw(_("Not authorized for asset dispatch"), frappe.PermissionError)


def _sig(*parts):
    return hashlib.sha256("|".join(str(p or "") for p in parts).encode()).hexdigest()


def _replay(operation_id, sig):
    """Idempotency via the Asset Movement's custom_legacy_id = operation_id."""
    row = frappe.db.get_value("Asset Movement", {"custom_legacy_id": operation_id},
                              ["name", "custom_remarks"], as_dict=True)
    if not row:
        return None
    if f"sig:{sig}" not in (row.custom_remarks or ""):
        return {"result": "conflict", "operation_id": operation_id}
    return {"result": "duplicate", "operation_id": operation_id, "asset_movement": row.name}


def _submit_movement(operation_id, sig, purpose, asset, row, extra, remarks):
    am = frappe.get_doc({
        "doctype": "Asset Movement", "company": frappe.db.get_value("Asset", asset, "company"),
        "purpose": purpose, "transaction_date": frappe.utils.now(),
        "assets": [dict(asset=asset, **row)],
        "custom_legacy_id": operation_id,
        "custom_remarks": f"{remarks or ''} | sig:{sig}",
        **extra,
    })
    am.insert()
    am.submit()
    return am.name


@frappe.whitelist()
def sig_dispatch_asset(operation_id, asset, dest_type, employee=None, location=None,
                       sig_site=None, project=None, expected_return=None,
                       handover_ref=None, remarks=None):
    _authorize()
    if not operation_id or not asset:
        return {"result": "exception", "reason": "operation_id/asset required"}
    sig = _sig(asset, dest_type, employee, location, sig_site, project)
    prior = _replay(operation_id, sig)
    if prior:
        return prior
    a = frappe.db.get_value("Asset", asset, ["docstatus", "status", "location",
                            "custom_custody_status"], as_dict=True)
    if not a or a.docstatus != 1:
        return {"result": "exception", "reason": "ASSET_NOT_SUBMITTED"}
    if a.status not in ISSUABLE_STATUSES:
        return {"result": "exception", "reason": f"ASSET_STATUS_{a.status}"}
    err = validate_dispatch(dest_type, employee, location, a.custom_custody_status)
    if err:
        return {"result": "exception", "reason": err}

    extra = {"custom_movement_type": MOVEMENT_TYPE[dest_type], "custom_handover_ref": handover_ref,
             "custom_expected_return": expected_return, "custom_condition_check": "Good",
             "custom_sig_site_to": sig_site, "custom_project_to": project,
             "custom_employee_to": employee if dest_type == "Employee" else None}
    if dest_type == "Employee":
        row = {"source_location": a.location, "to_employee": employee}
        purpose = "Issue"
    else:
        row = {"source_location": a.location, "target_location": location}
        purpose = "Transfer"
    name = _submit_movement(operation_id, sig, purpose, asset, row, extra, remarks)
    frappe.db.set_value("Asset", asset, {
        "custom_custody_status": CUSTODY_STATUS[dest_type],
        "custom_custodian_employee": employee if dest_type == "Employee" else None,
        "custom_sig_site": sig_site, "custom_project_link": project,
        "custom_issue_date": frappe.utils.nowdate(), "custom_expected_return_date": expected_return,
        "custom_handover_ref": handover_ref,
    }, update_modified=False)
    frappe.db.commit()
    return {"result": "created", "operation_id": operation_id, "asset_movement": name}


@frappe.whitelist()
def sig_return_asset(operation_id, asset, to_location, condition="Good",
                     handover_ref=None, remarks=None):
    _authorize()
    if not operation_id or not asset or not to_location:
        return {"result": "exception", "reason": "operation_id/asset/to_location required"}
    sig = _sig(asset, to_location, condition)
    prior = _replay(operation_id, sig)
    if prior:
        return prior
    a = frappe.db.get_value("Asset", asset, ["docstatus", "location", "custom_custody_status",
                            "custom_custodian_employee"], as_dict=True)
    if not a or a.docstatus != 1:
        return {"result": "exception", "reason": "ASSET_NOT_SUBMITTED"}
    if not (a.custom_custody_status or "").startswith("Issued"):
        return {"result": "exception", "reason": "asset is not issued"}
    if a.custom_custodian_employee:
        row = {"target_location": to_location, "from_employee": a.custom_custodian_employee}
        purpose, mtype = "Receipt", "Return from Employee"
    else:
        row = {"source_location": a.location, "target_location": to_location}
        purpose, mtype = "Transfer", "Return from Site"
    extra = {"custom_movement_type": mtype, "custom_handover_ref": handover_ref,
             "custom_condition_check": condition,
             "custom_employee_from": a.custom_custodian_employee}
    name = _submit_movement(operation_id, sig, purpose, asset, row, extra, remarks)
    frappe.db.set_value("Asset", asset, {
        "custom_custody_status": "Sent for Repair" if condition == "Needs Repair" else "In Store",
        "custom_custodian_employee": None, "custom_sig_site": None, "custom_project_link": None,
        "custom_return_date": frappe.utils.nowdate(), "custom_expected_return_date": None,
        "custom_handover_ref": handover_ref,
        "custom_asset_condition": condition if condition in ("New", "Good", "Needs Repair", "Damaged") else "Damaged",
    }, update_modified=False)
    frappe.db.commit()
    return {"result": "created", "operation_id": operation_id, "asset_movement": name}


@frappe.whitelist()
def sig_find_asset(query):
    """Scan/search by Asset name, tag or serial; only what the dialog needs."""
    _authorize()
    q = (query or "").strip()
    if not q:
        return []
    return frappe.get_all("Asset", filters={"docstatus": 1}, or_filters={
        "name": q, "custom_asset_tag_no": q, "asset_name": ["like", f"%{q}%"]},
        fields=["name", "asset_name", "asset_category", "location", "status",
                "custom_custody_status", "custom_custodian_employee", "custom_asset_tag_no"], limit=10)


TOOL_ASSET_CATEGORY = "Tools, Machinery & Heavy Equip"
COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"


def twin_code(stock_item):
    """Fixed-asset twin of a stock Item (ERPNext forbids one Item being both)."""
    return f"FA-{stock_item}"


def _ensure_twin(stock_item):
    code = twin_code(stock_item)
    if not frappe.db.exists("Item", code):
        name = frappe.db.get_value("Item", stock_item, "item_name")
        frappe.get_doc({
            "doctype": "Item", "item_code": code, "item_name": name, "item_group": "Products",
            "stock_uom": frappe.db.get_value("Item", stock_item, "stock_uom"),
            "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": TOOL_ASSET_CATEGORY,
            "auto_create_assets": 0,
        }).insert()
    return code


@frappe.whitelist()
def sig_capitalize_tool(operation_id, stock_item, warehouse, location, tag=None, remarks=None):
    """Stock -> Asset for one unit: native Asset Capitalization consumes the
    stock Item from the warehouse and creates the tagged Asset at stock cost."""
    _authorize()
    if not (operation_id and stock_item and warehouse and location):
        return {"result": "exception", "reason": "operation_id/stock_item/warehouse/location required"}
    it = frappe.db.get_value("Item", stock_item, ["is_stock_item", "is_fixed_asset"], as_dict=True)
    if not it or not it.is_stock_item or it.is_fixed_asset:
        return {"result": "exception", "reason": "NOT_A_STOCK_ITEM"}
    sig = _sig(stock_item, warehouse, location, tag)
    title = f"{operation_id}|{sig[:16]}"
    prior = frappe.db.get_value("Asset Capitalization", {"title": ["like", f"{operation_id}|%"]},
                                ["name", "title", "target_asset"], as_dict=True)
    if prior:
        if prior.title != title:
            return {"result": "conflict", "operation_id": operation_id}
        return {"result": "duplicate", "operation_id": operation_id,
                "asset_capitalization": prior.name, "asset": prior.target_asset}
    if (frappe.db.get_value("Bin", {"item_code": stock_item, "warehouse": warehouse}, "actual_qty") or 0) < 1:
        return {"result": "exception", "reason": "NO_STOCK"}
    if tag and frappe.db.exists("Asset", {"custom_asset_tag_no": tag, "docstatus": ["<", 2]}):
        return {"result": "exception", "reason": "TAG_IN_USE"}

    ac = frappe.get_doc({
        "doctype": "Asset Capitalization", "company": COMPANY, "posting_date": frappe.utils.nowdate(),
        "target_item_code": _ensure_twin(stock_item), "target_qty": 1,
        "target_asset_location": location, "title": title, "cost_center": "Main - SIG",
        "capitalization_method": "Create a new composite asset",
        "stock_items": [{"item_code": stock_item, "warehouse": warehouse, "stock_qty": 1}],
    })
    ac.insert()
    ac.submit()
    asset = ac.target_asset
    if asset:
        # ERPNext leaves the created Asset as a draft; no depreciation is set for tools, so submit it.
        ad = frappe.get_doc("Asset", asset)
        if ad.docstatus == 0:
            ad.custom_asset_tag_no = tag or asset
            ad.submit()
        frappe.db.set_value("Asset", asset, {
            "custom_asset_tag_no": tag or asset, "custom_custody_status": "In Store",
            "custom_issuing_warehouse": warehouse,
        }, update_modified=False)
    frappe.db.commit()
    return {"result": "created", "operation_id": operation_id,
            "asset_capitalization": ac.name, "asset": asset}
