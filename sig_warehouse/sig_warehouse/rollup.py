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

    total_requested = 0.0
    total_capped = 0.0
    line_states = []
    for mri in mr_items:
        qty = float(mri.qty or 0)
        issued = float(dispatched.get(str(mri.name), 0))
        remaining = qty - issued
        if remaining < EPS:
            remaining = 0.0
            state = "DISPATCHED"
        elif issued > EPS:
            state = "PARTIAL"
        else:
            state = "PENDING"
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

    if not line_states:
        stage = "PENDING"
    elif all(s == "DISPATCHED" for s in line_states):
        stage = "DISPATCHED"
    elif any(s in ("PARTIAL", "DISPATCHED") for s in line_states):
        stage = "PARTIAL"
    else:
        stage = "PENDING"
    legacy = {"DISPATCHED": "DISPATCHED", "PARTIAL": "PARTIALLY_DISPATCHED"}.get(stage, "PARTIALLY_CONFIRMED")

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
