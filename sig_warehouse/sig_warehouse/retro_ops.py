"""Retrospective metadata writer (9A.13 / 9A.14 step 1).

Server-side only, because REST cannot do these writes: the derived MR fields are permlevel 1 and the
Stock Entry link / voucher fields are not ``allow_on_submit``.  Every operation is METADATA ONLY - no
Stock Entry is created, cancelled or re-submitted, and no ledger row is written.  Each call:

* defaults to a DRY RUN (``dry_run=1``) and returns exactly what it would change;
* returns a before-image of every value it changes (the caller saves it) and leaves an audit comment;
* is idempotent (re-applying the same request changes nothing);
* only touches documents that are explicitly marked as retrospective / test material.

Actions (``sig_retro_apply(action, payload, dry_run)``):

LINK       tie Stock Entry Detail rows to Material Request Item rows, so the rollup counts them as issued.
DECLARE    close the undeclared remainder of a Stock Entry's lines as consumed (the same effect as the
           dialog's "Close as Consumed"), which lets the lifecycle close a fully dispatched MR.
DISMISS    set a line's cancelled quantity to an absolute target with a waiver reason
           (SMALL_VALUE_WAIVED / DELTA_DISMISSED / WH_CLOSED), which resolves the line like a dispatch.
RENAME_DN  rename an ERP-era DN voucher to its X form, keeping the original in ``custom_legacy_dn``.
RECOMPUTE  re-run ERPNext's ordered/indented bookkeeping and the lifecycle rollup for one MR (also repairs an MR that
           was linked before that bookkeeping was added).
"""
import json
import re

import frappe

from sig_warehouse.sig_warehouse import rollup

ALLOWED_ROLES = ("Stock Manager", "System Manager")
# An MR is only eligible if its source note carries one of these markers (set by the retrospective import
# and by the throwaway test MRs).  Live, ordinary MRs are therefore never touched by this module.
RETRO_MARKERS = ("Retrospective WH import", "9A.13")
REASONS = ("SMALL_VALUE_WAIVED", "DELTA_DISMISSED", "WH_CLOSED")
EPS = 1e-6

# ERP-era vouchers that may be renamed (16-23 Sep 2026, DN26-1035 .. DN26-1048), plus 9901/9902 reserved
# for the writer's own throwaway tests.
RENAME_ALLOWED = set(range(1035, 1049)) | {9901, 9902}
_OLD_VOUCHER = re.compile(r"^DN26-(\d{4})$")
_NEW_VOUCHER = re.compile(r"^DN26-(\d{4})X\d*$")


# --------------------------------------------------------------------------- pure helpers (unit-tested)
def parse_old_voucher(value):
    """'DN26-1043' -> 1043, anything else -> None."""
    m = _OLD_VOUCHER.match(str(value or "").strip())
    return int(m.group(1)) if m else None


def valid_rename(old, new):
    """The rename rule: old is a plain in-range voucher, new is that same number followed by X (or X<n>)."""
    n = parse_old_voucher(old)
    if n is None or n not in RENAME_ALLOWED:
        return False, "OLD_VOUCHER_NOT_ELIGIBLE"
    m = _NEW_VOUCHER.match(str(new or "").strip())
    if not m or int(m.group(1)) != n:
        return False, "NEW_VOUCHER_FORMAT"
    return True, ""


# Unit names that mean the same counting/length unit.  The 2026-05..09 backfilled Stock Entry lines carry `Nos`
# (3,294 lines) and `Meter` (1,072), always at conversion factor 1, while MRs created from WH use `Pcs`, `String`
# and `Mtr`.  A link across these names is accepted only when the conversion factor is exactly 1.
UOM_GROUPS = (
    frozenset({"nos", "pcs", "unit", "each", "string", "strings"}),
    frozenset({"meter", "mtr", "m"}),
)


def uom_compatible(a, b):
    """Same unit name, or two names in the same equivalence group.  Anything else (Box vs Pcs, Set vs Nos, ...) is not."""
    a, b = str(a or "").strip().lower(), str(b or "").strip().lower()
    if not a or not b:
        return False
    return a == b or any(a in g and b in g for g in UOM_GROUPS)


def is_retro_note(note):
    note = str(note or "")
    return any(note.startswith(m) for m in RETRO_MARKERS)


def _truthy_dry(dry_run):
    return str(dry_run).strip().lower() not in ("0", "false", "no", "off")


# --------------------------------------------------------------------------- guards
def _authorize():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not authenticated", frappe.PermissionError)
    if not any(r in ALLOWED_ROLES for r in frappe.get_roles(user)):
        frappe.throw("Not authorized for retrospective metadata writes", frappe.PermissionError)


def _fail(why, **extra):
    """Refusal payload.  The first argument is named `why` (not `reason`) so callers can pass a `reason=`
    extra without colliding with it; use `given_reason` for a caller-supplied value to avoid the clash."""
    return {"result": "refused", "reason": why, **extra}


def _load_mr(mr, mir):
    """Return (row, error).  The MR must be submitted, a Material Issue, carry this MIR number and a
    retrospective/test marker."""
    if not mr or not mir:
        return None, _fail("MR_AND_MIR_REQUIRED")
    row = frappe.db.get_value(
        "Material Request", mr,
        ["name", "docstatus", "material_request_type", "custom_mir_number", "custom_source_confirmed_by"],
        as_dict=True,
    )
    if not row:
        return None, _fail("UNKNOWN_MR", mr=mr)
    if row.docstatus != 1 or row.material_request_type != "Material Issue":
        return None, _fail("MR_NOT_SUBMITTED_MATERIAL_ISSUE", mr=mr)
    if str(row.custom_mir_number or "").strip() != str(mir).strip():
        return None, _fail("MIR_MISMATCH", mr=mr, expected=str(mir), found=row.custom_mir_number)
    if not is_retro_note(row.custom_source_confirmed_by):
        return None, _fail("MR_NOT_MARKED_RETROSPECTIVE", mr=mr)
    return row, None


def _load_se(se):
    row = frappe.db.get_value(
        "Stock Entry", se,
        ["name", "docstatus", "purpose", "is_return", "custom_source_id", "custom_legacy_dn"],
        as_dict=True,
    )
    return row


def _audit(doctype, name, action, before, after):
    """Best-effort audit comment on the document; never fails the write."""
    try:
        text = "SIG retro writer %s by %s. before=%s after=%s" % (
            action, frappe.session.user, json.dumps(before, default=str)[:900], json.dumps(after, default=str)[:900])
        frappe.get_doc(doctype, name).add_comment("Comment", text)
    except Exception:
        pass


def _clear(doctype, name):
    frappe.clear_document_cache(doctype, name)


def _bin_indented(mr_name):
    """{(item, warehouse): Bin.indented_qty} for the MR's own item/warehouse pairs (audit only)."""
    out = {}
    for r in frappe.get_all("Material Request Item", filters={"parent": mr_name}, fields=["item_code", "warehouse"]):
        v = frappe.db.get_value("Bin", {"item_code": r.item_code, "warehouse": r.warehouse}, "indented_qty")
        out["%s @ %s" % (r.item_code, r.warehouse)] = v
    return out


def _erp_sync(mr_name):
    """Bring ERPNext's own bookkeeping in line after lines were linked.

    ERPNext keeps `Material Request Item.ordered_qty` (= sum of linked, submitted Stock Entry Detail transfer_qty) and,
    from it, `Bin.indented_qty` (= for open Material Issue MRs: sum of stock_qty - ordered_qty, subtracted).  Both are
    normally refreshed when a linked Stock Entry is submitted.  Linking after the fact bypasses that, so without this
    the issued quantity would stay counted as outstanding demand and Projected Qty would be understated.  Uses
    ERPNext's own methods, so the maths is exactly what a normal submit would produce.
    """
    doc = frappe.get_doc("Material Request", mr_name)
    doc.update_completed_qty(update_modified=False)
    doc.update_requested_qty()
    try:
        doc.set_status(update=True, update_modified=False)
    except Exception:
        pass
    _clear("Material Request", mr_name)


# --------------------------------------------------------------------------- actions
def _link(p, apply):
    mr_row, err = _load_mr(p.get("mr"), p.get("mir"))
    if err:
        return err
    se = _load_se(p.get("stock_entry"))
    if not se or se.docstatus != 1 or se.purpose != "Material Issue" or se.is_return:
        return _fail("STOCK_ENTRY_NOT_ELIGIBLE", stock_entry=p.get("stock_entry"))
    lines = p.get("lines") or []
    if not lines:
        return _fail("NO_LINES")
    changes, before = [], []
    linked_qty = {}
    for ln in lines:
        sed = frappe.db.get_value(
            "Stock Entry Detail", ln.get("sed"),
            ["name", "parent", "item_code", "qty", "uom", "conversion_factor", "material_request",
             "material_request_item"], as_dict=True)
        mri = frappe.db.get_value(
            "Material Request Item", ln.get("mri"), ["name", "parent", "item_code", "qty", "uom"], as_dict=True)
        if not sed or sed.parent != se.name:
            return _fail("SED_NOT_ON_STOCK_ENTRY", sed=ln.get("sed"))
        if not mri or mri.parent != mr_row.name:
            return _fail("MRI_NOT_ON_MR", mri=ln.get("mri"))
        if sed.item_code != mri.item_code:
            return _fail("ITEM_MISMATCH", sed=sed.name, mri=mri.name, sed_item=sed.item_code, mri_item=mri.item_code)
        uom_note = ""
        if sed.uom != mri.uom:
            factor = float(sed.conversion_factor or 1)
            if not uom_compatible(sed.uom, mri.uom) or abs(factor - 1) > EPS:
                return _fail("UOM_MISMATCH", sed=sed.name, sed_uom=sed.uom, mri_uom=mri.uom, conversion_factor=factor)
            uom_note = "%s treated as %s (same unit, conversion factor 1)" % (sed.uom, mri.uom)
        if sed.material_request_item and sed.material_request_item != mri.name:
            return _fail("SED_ALREADY_LINKED_ELSEWHERE", sed=sed.name, linked_to=sed.material_request_item)
        if sed.material_request_item == mri.name and sed.material_request == mr_row.name:
            changes.append({"sed": sed.name, "mri": mri.name, "change": "none (already linked)"})
            continue
        already = frappe.db.sql(
            """select coalesce(sum(d.qty),0) from `tabStock Entry Detail` d
               join `tabStock Entry` s on s.name = d.parent
               where d.material_request_item = %s and s.docstatus = 1 and d.name != %s""",
            (mri.name, sed.name))[0][0]
        linked_qty[mri.name] = linked_qty.get(mri.name, float(already)) + float(sed.qty)
        if linked_qty[mri.name] - float(mri.qty) > EPS:
            return _fail("CAP_EXCEEDED", mri=mri.name, mr_qty=float(mri.qty), would_be_issued=linked_qty[mri.name])
        before.append({"sed": sed.name, "material_request": sed.material_request,
                       "material_request_item": sed.material_request_item})
        changes.append({"sed": sed.name, "mri": mri.name, "change": "link", "qty": float(sed.qty), "uom_note": uom_note})
    if apply:
        for c in changes:
            if c["change"] == "link":
                frappe.db.set_value("Stock Entry Detail", c["sed"],
                                    {"material_request": mr_row.name, "material_request_item": c["mri"]},
                                    update_modified=False)
                _clear("Stock Entry Detail", c["sed"])
        _clear("Stock Entry", se.name)
        indented_before = _bin_indented(mr_row.name)
        _erp_sync(mr_row.name)
        state = rollup.recompute_mr_lifecycle_state(mr_row.name)
        frappe.db.commit()
        indented_after = _bin_indented(mr_row.name)
        _audit("Stock Entry", se.name, "LINK", before, changes)
        return {"result": "applied", "changes": changes, "before_image": before, "mr_state": state,
                "bin_indented_before": indented_before, "bin_indented_after": indented_after}
    return {"result": "dry_run", "changes": changes}


def _declare(p, apply):
    mr_row, err = _load_mr(p.get("mr"), p.get("mir"))
    if err:
        return err
    se = _load_se(p.get("stock_entry"))
    if not se or se.docstatus != 1 or se.purpose != "Material Issue" or se.is_return:
        return _fail("STOCK_ENTRY_NOT_ELIGIBLE", stock_entry=p.get("stock_entry"))
    rows = frappe.get_all(
        "Stock Entry Detail", filters={"parent": se.name, "parenttype": "Stock Entry"},
        fields=["name", "qty", "material_request", "custom_qty_returned", "custom_qty_custody", "custom_return_closed"])
    if not rows or not any(r.material_request == mr_row.name for r in rows):
        return _fail("STOCK_ENTRY_NOT_LINKED_TO_MR", stock_entry=se.name, mr=mr_row.name)
    changes, before = [], []
    for r in rows:
        undeclared = float(r.qty or 0) - float(r.custom_qty_returned or 0) - float(r.custom_qty_custody or 0)
        if not r.custom_return_closed and undeclared > EPS:
            before.append({"sed": r.name, "custom_return_closed": 0})
            changes.append({"sed": r.name, "change": "close as consumed", "undeclared_qty": undeclared})
    header_before = frappe.db.get_value("Stock Entry", se.name, "custom_return_state")
    if apply:
        for c in changes:
            frappe.db.set_value("Stock Entry Detail", c["sed"], "custom_return_closed", 1, update_modified=False)
        state = rollup.recompute_return_state(se.name)
        lifecycle = {m: rollup.recompute_mr_lifecycle_state(m) for m in {mr_row.name}}
        frappe.db.commit()
        _audit("Stock Entry", se.name, "DECLARE", {"lines": before, "custom_return_state": header_before}, changes)
        return {"result": "applied", "changes": changes, "before_image": before,
                "custom_return_state_before": header_before, "return_state": state, "mr_lifecycle": lifecycle}
    return {"result": "dry_run", "changes": changes, "custom_return_state_now": header_before}


def _dismiss(p, apply):
    mr_row, err = _load_mr(p.get("mr"), p.get("mir"))
    if err:
        return err
    lines = p.get("lines") or []
    if not lines:
        return _fail("NO_LINES")
    changes, before = [], []
    for ln in lines:
        reason = str(ln.get("reason") or "")
        if reason not in REASONS:
            return _fail("REASON_NOT_ALLOWED", mri=ln.get("mri"), given_reason=reason, allowed=list(REASONS))
        try:
            target = float(ln.get("cancelled_qty"))
        except (TypeError, ValueError):
            return _fail("BAD_QTY", mri=ln.get("mri"))
        mri = frappe.db.get_value(
            "Material Request Item", ln.get("mri"),
            ["name", "parent", "qty", "custom_qty_issued", "custom_qty_cancelled", "custom_cancel_reason"], as_dict=True)
        if not mri or mri.parent != mr_row.name:
            return _fail("MRI_NOT_ON_MR", mri=ln.get("mri"))
        issued = float(mri.custom_qty_issued or 0)
        if target < 0 or target > float(mri.qty) - issued + EPS:
            return _fail("QTY_OUT_OF_RANGE", mri=mri.name, mr_qty=float(mri.qty), issued=issued, target=target)
        if abs(float(mri.custom_qty_cancelled or 0) - target) < EPS and (mri.custom_cancel_reason or "") == reason:
            changes.append({"mri": mri.name, "change": "none (already set)"})
            continue
        before.append({"mri": mri.name, "custom_qty_cancelled": mri.custom_qty_cancelled,
                       "custom_cancel_reason": mri.custom_cancel_reason})
        changes.append({"mri": mri.name, "change": "dismiss", "cancelled_qty": target, "reason": reason})
    if apply:
        for c in changes:
            if c["change"] == "dismiss":
                frappe.db.set_value("Material Request Item", c["mri"],
                                    {"custom_qty_cancelled": c["cancelled_qty"], "custom_cancel_reason": c["reason"]},
                                    update_modified=False)
                _clear("Material Request Item", c["mri"])
        state = rollup.recompute_mr_lifecycle_state(mr_row.name)
        frappe.db.commit()
        _audit("Material Request", mr_row.name, "DISMISS", before, changes)
        return {"result": "applied", "changes": changes, "before_image": before, "mr_state": state}
    return {"result": "dry_run", "changes": changes}


def _rename_dn(p, apply):
    se = _load_se(p.get("stock_entry"))
    if not se or se.purpose != "Material Issue":
        return _fail("STOCK_ENTRY_NOT_ELIGIBLE", stock_entry=p.get("stock_entry"))
    new = str(p.get("new_voucher") or "").strip()
    old = str(se.custom_source_id or "").strip()
    if old == new and se.custom_legacy_dn:
        return {"result": "dry_run" if not apply else "applied",
                "changes": [{"stock_entry": se.name, "change": "none (already renamed)"}]}
    ok, why = valid_rename(old, new)
    if not ok:
        return _fail(why, stock_entry=se.name, old=old, new=new)
    if se.custom_legacy_dn:
        return _fail("LEGACY_DN_ALREADY_SET", stock_entry=se.name, custom_legacy_dn=se.custom_legacy_dn)
    clash = frappe.db.exists("Stock Entry", {"custom_source_id": new})
    if clash:
        return _fail("NEW_VOUCHER_ALREADY_USED", new=new, by=clash)
    change = {"stock_entry": se.name, "change": "rename", "from": old, "to": new}
    before = {"custom_source_id": old, "custom_legacy_dn": se.custom_legacy_dn}
    if apply:
        frappe.db.set_value("Stock Entry", se.name, {"custom_source_id": new, "custom_legacy_dn": old},
                            update_modified=False)
        _clear("Stock Entry", se.name)
        frappe.db.commit()
        _audit("Stock Entry", se.name, "RENAME_DN", before, change)
        return {"result": "applied", "changes": [change], "before_image": before}
    return {"result": "dry_run", "changes": [change]}


def _recompute(p, apply):
    mr_row, err = _load_mr(p.get("mr"), p.get("mir"))
    if err:
        return err
    if apply:
        indented_before = _bin_indented(mr_row.name)
        _erp_sync(mr_row.name)
        state = rollup.recompute_mr_lifecycle_state(mr_row.name)
        frappe.db.commit()
        return {"result": "applied", "mr_state": state, "bin_indented_before": indented_before,
                "bin_indented_after": _bin_indented(mr_row.name)}
    return {"result": "dry_run", "changes": [{"mr": mr_row.name, "change": "recompute + ERPNext ordered/indented sync",
                                              "bin_indented_now": _bin_indented(mr_row.name)}]}


_ACTIONS = {"LINK": _link, "DECLARE": _declare, "DISMISS": _dismiss, "RENAME_DN": _rename_dn, "RECOMPUTE": _recompute}


@frappe.whitelist(methods=["POST"])
def sig_retro_apply(action, payload=None, dry_run=1):
    """Single entry point.  ``payload`` is a JSON object (string or dict).  Dry run by default."""
    _authorize()
    action = str(action or "").upper()
    fn = _ACTIONS.get(action)
    if not fn:
        return _fail("UNKNOWN_ACTION", allowed=sorted(_ACTIONS))
    if isinstance(payload, str):
        try:
            payload = json.loads(payload or "{}")
        except ValueError:
            return _fail("BAD_PAYLOAD_JSON")
    payload = payload or {}
    result = fn(payload, apply=not _truthy_dry(dry_run))
    result["action"] = action
    return result
