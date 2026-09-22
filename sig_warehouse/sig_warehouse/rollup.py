"""Single source of truth for Material Request dispatch-state rollup.

Recomputes the derived fields on Material Request / Material Request Item
(custom_dispatch_stage, custom_sync_status, custom_qty_issued,
custom_qty_remaining, custom_line_status) from submitted, non-return Stock
Entry Details actually linked to the MR's own lines. This is the same
algorithm deployed as a sandboxed copy inside register_stock_entry_script.py
(see erpnext_final_implementation_plan.md 9A.9, sentinel SIG-MR-ROLLUP) -
that copy exists only because the live WH VBA mirror endpoint is a Server
Script and can't import this module. Every other caller (sig_dispatch_mr,
sig_declare_disposition, and the doc_events below) calls this directly.

Wired via hooks.py doc_events so a native ERPNext submit/cancel/amendment
recomputes state too, not just the two custom write endpoints - a plain
Stock Entry cancelled from its own form must not leave stale derived fields.
"""
import frappe

EPS = 1e-6
WAIVER_REASONS = ("SMALL_VALUE_WAIVED", "DELTA_DISMISSED", "WH_CLOSED")


def recompute_mr_dispatch_state(mr_name):
    mr_type = frappe.db.get_value("Material Request", mr_name, "material_request_type")
    if not mr_type:
        return None
    fulfilling_purpose = "Material Issue" if mr_type == "Material Issue" else "Material Transfer"

    mr_items = frappe.get_all(
        "Material Request Item",
        filters={"parent": mr_name, "parenttype": "Material Request"},
        fields=["name", "qty", "item_code", "uom"],
    )
    mri_by_name = {str(x.name): x for x in mr_items}
    item_names = list(mri_by_name.keys())

    dispatched = {}
    if item_names:
        details = frappe.get_all(
            "Stock Entry Detail",
            filters={
                "material_request_item": ["in", item_names],
                "parenttype": "Stock Entry",
                "docstatus": 1,
            },
            fields=["material_request_item", "qty", "uom", "parent"],
        )
        parent_names = {str(d.parent) for d in details}
        parent_meta = {
            str(p.name): p
            for p in frappe.get_all(
                "Stock Entry",
                filters={"name": ["in", list(parent_names)]},
                fields=["name", "is_return", "purpose"],
            )
        } if parent_names else {}

        for d in details:
            meta = parent_meta.get(str(d.parent))
            if not meta or meta.is_return or meta.purpose != fulfilling_purpose:
                continue
            item_name = str(d.material_request_item or "")
            qty = float(d.qty or 0)
            mri = mri_by_name.get(item_name)
            line_uom = str(d.uom or "")
            if mri and line_uom and mri.uom and line_uom != mri.uom:
                factor = frappe.db.get_value(
                    "UOM Conversion Detail",
                    {"parent": mri.item_code, "uom": line_uom},
                    "conversion_factor",
                )
                if factor:
                    qty *= float(factor)
            dispatched[item_name] = dispatched.get(item_name, 0) + qty

    cancelled_by_item = {}
    reason_by_item = {}
    if item_names:
        cancelled_rows = frappe.get_all(
            "Material Request Item",
            filters={"name": ["in", item_names]},
            fields=["name", "custom_qty_cancelled", "custom_cancel_reason"],
        )
        cancelled_by_item = {str(r.name): float(r.custom_qty_cancelled or 0) for r in cancelled_rows}
        reason_by_item = {str(r.name): str(r.custom_cancel_reason or "") for r in cancelled_rows}

    total_requested = 0.0
    total_capped = 0.0
    line_states = []
    any_cancelled = False
    # Owner rule 2026-09-21: cancelling the remainder of a partial dispatch never CLOSES the MR.
    # A cancel counts as an *operator* cancel unless its reason is a retrospective waiver
    # (SMALL_VALUE_WAIVED / DELTA_DISMISSED / WH_CLOSED), which resolve the line like a dispatch does.
    any_operator_cancel = False
    any_issued = False
    for mri in mr_items:
        qty = float(mri.qty or 0)
        issued = float(dispatched.get(str(mri.name), 0))
        cancelled = min(cancelled_by_item.get(str(mri.name), 0.0), max(0.0, qty - issued))
        remaining = qty - issued - cancelled
        if remaining < EPS:
            remaining = 0.0
            # A line resolved purely by cancellation (never dispatched at
            # all) is CANCELLED; a line resolved by dispatch - whether or
            # not part of it was separately cancelled first - is DISPATCHED.
            # The header-level distinction between a clean full dispatch and
            # one that involved a cancellation is CLOSED vs DISPATCHED below.
            state = "CANCELLED" if issued < EPS and cancelled > EPS else "DISPATCHED"
        elif issued > EPS or cancelled > EPS:
            state = "PARTIAL"
        else:
            state = "PENDING"
        if cancelled > EPS:
            any_cancelled = True
            if reason_by_item.get(str(mri.name), "") not in WAIVER_REASONS:
                any_operator_cancel = True
        if issued > EPS:
            any_issued = True
        frappe.db.set_value(
            "Material Request Item",
            mri.name,
            {"custom_qty_issued": issued, "custom_qty_remaining": remaining, "custom_line_status": state},
            update_modified=False,
        )
        # A child row fetched directly (e.g. REST GET /api/resource/Material
        # Request Item/<name>) is cached under its OWN (doctype, name) key,
        # separate from the parent Material Request's cache entry - clearing
        # only the parent (below) does not invalidate it. Found live: the
        # parent-only clear alone still served stale child rows.
        frappe.clear_document_cache("Material Request Item", mri.name)
        total_requested += qty
        total_capped += min(issued, qty)
        line_states.append(state)

    resolved = ("DISPATCHED", "CANCELLED")
    if not line_states:
        stage = "PENDING"
    elif all(s in resolved for s in line_states):
        # Every line is done, one way or another. CLOSED (not DISPATCHED)
        # only when at least one line's resolution involved a cancellation -
        # a pure full dispatch keeps the exact prior DISPATCHED behaviour.
        if any_operator_cancel and any_issued:
            stage = "PARTIAL"      # a cancelled partial is never CLOSED
        elif any_cancelled and not any_issued:
            stage = "CLOSED"       # nothing was ever dispatched: fully cancelled
        else:
            stage = "DISPATCHED"   # incl. waived/dismissed remainders; the lifecycle closes it once returns are declared
    elif any(s in ("PARTIAL",) + resolved for s in line_states):
        stage = "PARTIAL"
    else:
        stage = "PENDING"
    legacy = {"DISPATCHED": "DISPATCHED", "CLOSED": "DISPATCHED", "PARTIAL": "PARTIALLY_DISPATCHED"}.get(stage, "PARTIALLY_CONFIRMED")

    frappe.db.set_value(
        "Material Request",
        mr_name,
        {"custom_dispatch_stage": stage, "custom_sync_status": legacy},
        update_modified=False,
    )
    # frappe.db.set_value is a raw SQL write - bypasses the document cache
    # entirely, so a doc already cached (e.g. by an earlier frappe.get_doc/
    # REST read in the same or a prior request) can keep serving stale
    # derived fields indefinitely even though the DB row is correct (found
    # live via raw-SQL-vs-REST comparison, 9A.9 Stage 3). Centralized here
    # so every caller (both endpoints, both doc_events hooks) gets it for
    # free instead of repeating it at each call site.
    frappe.clear_document_cache("Material Request", mr_name)
    return {
        "mr": mr_name,
        "stage": stage,
        "legacy_status": legacy,
        "requested_qty": total_requested,
        "dispatched_qty": total_capped,
    }


def recompute_mr_lifecycle_state(mr_name):
    """Layer the return/declaration lifecycle over an already-issued MR.

    Dispatch arithmetic remains the source of truth for PENDING/PARTIAL and
    whether an MR is fully issued. Once it is fully dispatched, however, the
    operational cycle is not complete until every linked outbound Stock Entry
    has a declared return disposition (returned, custody, or intentionally
    consumed). Only then does the Kanban stage become CLOSED. Reopening a
    consumed close naturally restores DISPATCHED without changing issued qty.
    """
    result = recompute_mr_dispatch_state(mr_name)
    if not result or result["stage"] != "DISPATCHED":
        return result

    fulfilling_purpose = (
        "Material Issue"
        if frappe.db.get_value("Material Request", mr_name, "material_request_type") == "Material Issue"
        else "Material Transfer"
    )
    parent_names = {
        str(row.parent)
        for row in frappe.get_all(
            "Stock Entry Detail",
            filters={"material_request": mr_name, "parenttype": "Stock Entry", "docstatus": 1},
            fields=["parent"],
        )
    }
    outbound = frappe.get_all(
        "Stock Entry",
        filters={"name": ["in", list(parent_names)], "docstatus": 1, "is_return": 0,
                 "purpose": fulfilling_purpose},
        fields=["name", "custom_return_state"],
    ) if parent_names else []

    if not outbound or any(row.custom_return_state != "DECLARED" for row in outbound):
        return result

    frappe.db.set_value(
        "Material Request", mr_name,
        {"custom_dispatch_stage": "CLOSED", "custom_sync_status": "DISPATCHED"},
        update_modified=False,
    )
    frappe.clear_document_cache("Material Request", mr_name)
    result["stage"] = "CLOSED"
    return result


def _linked_mr_names(stock_entry_doc):
    names = set()
    for row in stock_entry_doc.items:
        if row.material_request:
            names.add(row.material_request)
    return names


def on_stock_entry_submit(doc, method=None):
    for mr_name in _linked_mr_names(doc):
        recompute_mr_dispatch_state(mr_name)
    if _linked_mr_names(doc):
        frappe.db.commit()


def on_stock_entry_cancel(doc, method=None):
    for mr_name in _linked_mr_names(doc):
        recompute_mr_dispatch_state(mr_name)
    if _linked_mr_names(doc):
        frappe.db.commit()


def on_material_request_submit(doc, method=None):
    # Initializes the derived fields (remaining=qty, PENDING) the moment the MR
    # itself is submitted - without this, a freshly submitted MR with no prior
    # dispatch activity has never had the rollup run on it at all, and
    # custom_qty_remaining stays at its unset default (0) instead of qty. That
    # gap let a real dispatch's cap-check see remaining=0 on a brand-new MR
    # and refuse every dispatch attempt (found live, Stage 2 proving pack).
    recompute_mr_dispatch_state(doc.name)
    frappe.db.commit()


def on_material_request_cancel(doc, method=None):
    recompute_mr_dispatch_state(doc.name)
    frappe.db.commit()


def set_display_title(doc, method=None):
    # ERPNext's own auto-generated `title` ("Material Issue Request for <item
    # descriptions>") is unusable as a Kanban card / breadcrumb label once a
    # request has more than one or two long item names. custom_display_title
    # is a short "<name> <site>" shown instead (see title_field Property
    # Setter) - runs on every save, draft or submitted, so it's never stale.
    doc.custom_display_title = " ".join(filter(None, [doc.name, doc.get("custom_site")]))


def on_material_request_update_after_submit(doc, method=None):
    recompute_mr_dispatch_state(doc.name)
    frappe.db.commit()


def recompute_return_state(se_name):
    """Recompute per-line custom_return_disposition and the header
    custom_return_state on the ORIGINAL DN (source_se) from its own detail
    rows' custom_qty_returned/custom_qty_custody/custom_return_closed.
    Mirrors WH's own per-row disposition grain (white paper: Source DN Line,
    Qty Return, In-Hand flag, Closed?) rather than a scalar MR-wide sum.
    Called by sig_declare_disposition after every RETURN/CUSTODY/CLOSE."""
    rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"parent": se_name, "parenttype": "Stock Entry"},
        fields=["name", "qty", "custom_qty_returned", "custom_qty_custody", "custom_return_closed"],
    )
    if not rows:
        return None
    line_states = []
    for row in rows:
        qty = float(row.qty or 0)
        returned = float(row.custom_qty_returned or 0)
        custody = float(row.custom_qty_custody or 0)
        closed = bool(row.custom_return_closed)
        allocated = returned + custody
        if closed or allocated + EPS >= qty:
            if closed and allocated < EPS:
                disposition = "CONSUMED_CLOSED"
            elif returned + EPS >= qty and custody < EPS:
                disposition = "RETURNED"
            elif custody + EPS >= qty and returned < EPS:
                disposition = "IN_HAND"
            else:
                disposition = "CONSUMED_CLOSED" if closed else "PARTIAL"
            state = "DECLARED"
        elif allocated > EPS:
            disposition = "PARTIAL"
            state = "PARTIAL"
        else:
            disposition = "PENDING"
            state = "PENDING"
        frappe.db.set_value("Stock Entry Detail", row.name, "custom_return_disposition", disposition, update_modified=False)
        # same child-row cache gap as Material Request Item above - clear
        # each detail row's own cache entry, not just the parent Stock Entry.
        frappe.clear_document_cache("Stock Entry Detail", row.name)
        line_states.append(state)

    has_non_declared = any(s != "DECLARED" for s in line_states)
    has_progress = any(s in ("PARTIAL", "DECLARED") for s in line_states)
    if not has_non_declared:
        header_state = "DECLARED"
    elif has_progress:
        header_state = "PARTIAL"
    else:
        header_state = "PENDING"

    update = {"custom_return_state": header_state}
    if header_state == "DECLARED":
        update["custom_return_closed_by"] = frappe.session.user
        update["custom_return_closed_on"] = frappe.utils.now()
    frappe.db.set_value("Stock Entry", se_name, update, update_modified=False)
    frappe.clear_document_cache("Stock Entry", se_name)  # see recompute_mr_dispatch_state
    return header_state
