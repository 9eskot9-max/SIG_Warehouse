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


def _return_source_names(stock_entry_doc):
    """Return original DNs that this ERP return can identify without guessing."""
    if not getattr(stock_entry_doc, "is_return", 0):
        return set()
    names = set()
    header_source = (
        getattr(stock_entry_doc, "custom_return_against_se", None)
        or getattr(stock_entry_doc, "return_against", None)
    )
    if header_source:
        names.add(header_source)
    for row in getattr(stock_entry_doc, "items", []) or []:
        for fieldname in ("custom_original_stock_entry", "against_stock_entry"):
            source = getattr(row, fieldname, None)
            if source:
                names.add(source)
        for fieldname in ("custom_original_se_detail", "ste_detail"):
            detail = getattr(row, fieldname, None)
            if detail:
                parent = frappe.db.get_value("Stock Entry Detail", detail, "parent")
                if parent:
                    names.add(parent)
    return names


def _apply_return_event(source_se, stock_entry_doc, direction):
    """Apply one submitted/cancelled return event to one original DN.

    Exact source detail links are preferred. Legacy header-linked rows may be
    distributed only across duplicate item/UOM lines that share the same
    site/project/MIR identity. Ambiguous rows leave counters untouched.
    """
    source_rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"parent": source_se, "parenttype": "Stock Entry"},
        fields=["name", "item_code", "qty", "uom", "custom_site", "project",
                "material_request", "custom_row_key", "custom_qty_custody", "custom_qty_returned",
                "custom_return_closed"],
        order_by="idx asc, name asc",
    )
    if not source_rows:
        return {"updated": False, "reason": "SOURCE_LINES_MISSING"}
    source_by_name = {str(row.name): row for row in source_rows}
    changes = {name: 0.0 for name in source_by_name}
    fallback_by_key = {}
    header_source = (
        getattr(stock_entry_doc, "custom_return_against_se", None)
        or getattr(stock_entry_doc, "return_against", None)
    )
    if header_source and header_source != source_se:
        return {"updated": False, "reason": "RETURN_HEADER_SOURCE_MISMATCH"}
    matched = False
    for row in getattr(stock_entry_doc, "items", []) or []:
        linked_source = row.get("custom_original_stock_entry") or row.get("against_stock_entry")
        linked_detail = row.get("custom_original_se_detail") or row.get("ste_detail")
        if linked_detail:
            detail = source_by_name.get(str(linked_detail))
            if not detail:
                return {"updated": False, "reason": "RETURN_DETAIL_NOT_ON_SOURCE", "line": row.name}
            if linked_source and linked_source != source_se:
                return {"updated": False, "reason": "RETURN_SOURCE_MISMATCH", "line": row.name}
            if direction > 0 and getattr(detail, "custom_return_closed", 0):
                return {"updated": False, "reason": "RETURN_SOURCE_LINE_CLOSED", "line": row.name}
            changes[str(detail.name)] += direction * float(row.qty or 0)
            matched = True
            continue
        if linked_source and linked_source != source_se:
            continue
        if header_source and header_source != source_se and linked_source != source_se:
            continue
        if header_source != source_se and linked_source != source_se:
            continue
        key = (str(row.item_code or ""), str(row.uom or "").strip().casefold())
        fallback_by_key[key] = fallback_by_key.get(key, 0.0) + float(row.qty or 0)
        matched = True

    if not matched:
        return {"updated": False, "reason": "RETURN_SOURCE_LINK_MISSING"}

    for (item_code, uom), qty in fallback_by_key.items():
        candidates = [
            row for row in source_rows
            if str(row.item_code or "") == item_code and str(row.uom or "").strip().casefold() == uom
        ]
        if not candidates:
            return {"updated": False, "reason": "RETURN_LINE_UNMATCHED", "item_code": item_code, "uom": uom}
        if direction > 0 and any(getattr(row, "custom_return_closed", 0) for row in candidates):
            return {
                "updated": False, "reason": "RETURN_LINE_CLOSED_LINK_REQUIRED",
                "item_code": item_code, "uom": uom,
            }
        # Mapping can split one ERP item into separate CUCs. Do not allocate
        # an unlinked historical return across such source lines by accident.
        identities = {
            (row.custom_site, row.project, row.material_request, row.custom_row_key)
            for row in candidates
        }
        if len(identities) != 1:
            return {"updated": False, "reason": "RETURN_LINE_AMBIGUOUS", "item_code": item_code, "uom": uom}
        remaining = qty
        ordered = candidates if direction > 0 else list(reversed(candidates))
        for row in ordered:
            name = str(row.name)
            current = float(row.custom_qty_returned or 0) + changes[name]
            if direction > 0:
                capacity = max(0.0, float(row.qty or 0) - float(row.custom_qty_custody or 0) - current)
            else:
                capacity = max(0.0, current)
            allocated = min(capacity, remaining)
            changes[name] += direction * allocated
            remaining -= allocated
        if remaining > 1e-6:
            return {"updated": False, "reason": "RETURN_QTY_DOES_NOT_MATCH_SOURCE", "item_code": item_code, "uom": uom}

    for row in source_rows:
        name = str(row.name)
        returned = float(row.custom_qty_returned or 0) + changes[name]
        if returned < -1e-6 or returned + float(row.custom_qty_custody or 0) > float(row.qty or 0) + 1e-6:
            return {"updated": False, "reason": "RETURN_ALLOCATION_INVALID", "line": name}

    changed = 0
    for name, delta in changes.items():
        if abs(delta) <= 1e-6:
            continue
        current = float(source_by_name[name].custom_qty_returned or 0)
        frappe.db.set_value("Stock Entry Detail", name, "custom_qty_returned", current + delta, update_modified=False)
        frappe.clear_document_cache("Stock Entry Detail", name)
        changed += 1
    return {"updated": True, "lines": changed}


def _sync_returned_stock_entry(doc, direction):
    results = {}
    for source_se in sorted(_return_source_names(doc)):
        # Serialize native ERP returns with the disposition endpoint and the
        # daily expiry job, both of which lock this source DN before allocation.
        locked = frappe.db.sql(
            "select name from `tabStock Entry` where name = %s for update",
            (source_se,),
        )
        if not locked:
            result = {"updated": False, "reason": "RETURN_SOURCE_MISSING"}
            results[source_se] = result
            frappe.throw(f"Return source {source_se} no longer exists; stock return was not reconciled.")
        result = _apply_return_event(source_se, doc, direction)
        results[source_se] = result
        if result.get("updated"):
            recompute_return_state(source_se)
            source_doc = frappe.get_doc("Stock Entry", source_se)
            for mr_name in _linked_mr_names(source_doc):
                recompute_mr_lifecycle_state(mr_name)
        else:
            frappe.throw(
                f"Return could not be reconciled to source DN {source_se} ({result.get('reason')}). "
                "No Stock Entry return was posted or cancelled."
            )
    return results


def on_stock_entry_submit(doc, method=None):
    if getattr(doc, "is_return", 0):
        _sync_returned_stock_entry(doc, direction=1)
    for mr_name in _linked_mr_names(doc):
        recompute_mr_dispatch_state(mr_name)
    # Do not commit inside the document hook. Dispatch/return endpoints must
    # commit the Stock Entry, counters, and operation record as one transaction.


def on_stock_entry_cancel(doc, method=None):
    if getattr(doc, "is_return", 0):
        _sync_returned_stock_entry(doc, direction=-1)
    for mr_name in _linked_mr_names(doc):
        recompute_mr_dispatch_state(mr_name)
    # The caller owns the transaction so cancellation and rollups stay atomic.


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
