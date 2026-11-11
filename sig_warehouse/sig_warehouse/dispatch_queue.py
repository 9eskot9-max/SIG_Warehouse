"""Read model for the app-owned Dispatch Queue page (``/app/dispatch-queue``).

Replaces the Kanban decoration of Material Request. Read-only: it never writes
``custom_dispatch_stage`` (derived by ``rollup``), never moves stock and never
bypasses permissions. Every user-facing read goes through ``frappe.get_list`` /
``has_permission``. Pure helpers at the top are unit-tested without Frappe.
"""
import frappe

EPS = 1e-6
STAGES = ("PENDING", "PARTIAL", "DISPATCHED", "CLOSED")
OPEN_STAGES = ("PENDING", "PARTIAL", "DISPATCHED")
VIEW_ROLES = ("System Manager", "Stock Manager", "Stock User", "Warehouse Manager")
ACT_ROLES = ("System Manager", "Stock Manager")  # same as dispatch_operation.ALLOWED_DISPATCH_ROLES
MAX_ROWS = 5000
BATCH = 400
CLOSED_CANDIDATES = 1000  # CLOSED MIRs inspected for the recently-closed window
RETURN_RANK = {"NONE": 0, "DECLARED": 1, "PENDING": 2, "PARTIAL": 3}


# ---------------------------------------------------------------- pure helpers
def classify_availability(open_lines, bins):
    """Stock traffic light per MR.

    ``open_lines``: dicts with parent, item_code, warehouse, custom_qty_remaining.
    ``bins``: dicts with item_code, warehouse, actual_qty.
    Returns {mr: "green"|"yellow"|"red"}; an MR with no open line is omitted.
    green: every open line covered by its own warehouse; yellow: short locally but
    every short line is covered by another warehouse; red: some line is covered nowhere.
    """
    by_item_wh, by_item = {}, {}
    for b in bins:
        qty = float(b.get("actual_qty") or 0)
        by_item_wh[(b.get("item_code"), b.get("warehouse"))] = qty
        by_item.setdefault(b.get("item_code"), {})[b.get("warehouse")] = qty
    by_mr = {}
    for r in open_lines:
        if float(r.get("custom_qty_remaining") or 0) > EPS:
            by_mr.setdefault(r.get("parent"), []).append(r)
    result = {}
    for mr, rows in by_mr.items():
        local = elsewhere = True
        for r in rows:
            remaining = float(r.get("custom_qty_remaining") or 0)
            if by_item_wh.get((r.get("item_code"), r.get("warehouse")), 0.0) + EPS >= remaining:
                continue
            local = False
            best_other = max((q for wh, q in by_item.get(r.get("item_code"), {}).items()
                              if wh != r.get("warehouse")), default=0.0)
            if best_other + EPS < remaining:
                elsewhere = False
        result[mr] = "green" if local else ("yellow" if elsewhere else "red")
    return result


def worst_return_state(dns):
    """Worst custom_return_state across outbound DNs. NONE when there is no DN.

    Returns None (unknown) when any DN row does not carry the field at all, which is what
    Frappe does for a permission-level-1 field the caller cannot read. Unknown must never be
    shown as "pending".
    """
    worst = "NONE"
    for dn in dns:
        if "custom_return_state" not in dn:
            return None
        state = str(dn.get("custom_return_state") or "PENDING").upper()
        if state not in RETURN_RANK:
            state = "PENDING"
        if RETURN_RANK[state] > RETURN_RANK[worst]:
            worst = state
    return worst


def row_flags(stage, lines, return_state):
    """Derived exceptions. Never written back."""
    flags = []
    open_lines = [l for l in lines if float(l.get("custom_qty_remaining") or 0) > EPS]
    operator_cancel = any(
        float(l.get("custom_qty_cancelled") or 0) > EPS
        and str(l.get("custom_cancel_reason") or "") not in ("SMALL_VALUE_WAIVED", "DELTA_DISMISSED", "WH_CLOSED")
        for l in lines)
    issued = any(float(l.get("custom_qty_issued") or 0) > EPS for l in lines)
    if stage == "PARTIAL" and operator_cancel and issued:
        flags.append("cancelled_partial")
    # Only a real outbound DN with an undeclared return blocks closure. An MIR with no DN
    # record (dispatched before cutover) must not be flagged from absence of data.
    if stage == "DISPATCHED" and return_state in ("PENDING", "PARTIAL"):
        flags.append("return_blocks_close")
    if stage in ("PENDING", "PARTIAL") and lines and not open_lines:
        flags.append("no_open_lines_but_open_stage")
    return flags


def summarize(rows):
    out = {"PENDING": 0, "PARTIAL": 0, "DISPATCHED": 0, "CLOSED_RECENT": 0,
           "return_pending": 0, "red": 0, "yellow": 0}
    for r in rows:
        stage = r.get("stage")
        if stage == "CLOSED":
            out["CLOSED_RECENT"] += 1
        elif stage in out:
            out[stage] += 1
        if "return_blocks_close" in (r.get("flags") or []):
            out["return_pending"] += 1
        if stage != "CLOSED" and r.get("availability") in ("red", "yellow"):
            out[r["availability"]] += 1
    return out


def closed_on(header, dns):
    """When a CLOSED MIR was closed: the latest return-declaration stamp on its outbound DNs.

    The rollup writes CLOSED with update_modified=False, so ``modified`` does not move on
    closure and cannot be used. An MIR cancelled with nothing issued has no DN; fall back
    to ``modified`` for it.
    """
    stamps = [str(d.get("custom_return_closed_on") or "") for d in dns if d.get("custom_return_closed_on")]
    return max(stamps) if stamps else str(header.get("modified") or "")


def _day(value):
    return str(value)[:10] if value else None


def _age_days(created, today):
    from datetime import date
    try:
        return max(0, (date.fromisoformat(str(today)[:10]) - date.fromisoformat(str(created)[:10])).days)
    except ValueError:
        return 0


def build_row(header, lines, dns, availability, today):
    stage = str(header.get("custom_dispatch_stage") or "PENDING").upper()
    ret = worst_return_state(dns)
    qty = {"requested": 0.0, "issued": 0.0, "cancelled": 0.0, "remaining": 0.0}
    for l in lines:
        qty["requested"] += float(l.get("qty") or 0)
        qty["issued"] += float(l.get("custom_qty_issued") or 0)
        qty["cancelled"] += float(l.get("custom_qty_cancelled") or 0)
        qty["remaining"] += float(l.get("custom_qty_remaining") or 0)
    open_n = sum(1 for l in lines if float(l.get("custom_qty_remaining") or 0) > EPS)
    last = max(dns, key=lambda d: (str(d.get("posting_date") or ""), str(d.get("name") or "")), default=None)
    return {
        "name": header.get("name"),
        "mir": header.get("custom_mir_number") or "",
        "site": header.get("custom_site") or "",
        "project": header.get("custom_project") or "",
        "po": header.get("custom_po_number") or "",
        "work_type": header.get("custom_work_type") or "",
        "requested_on": _day(header.get("transaction_date")),
        "required_by": _day(header.get("schedule_date")),
        "created": str(header.get("creation") or ""),
        "age_days": _age_days(header.get("creation"), today),
        "stage": stage,
        "lines": {"total": len(lines), "open": open_n,
                  "issued": sum(1 for l in lines if float(l.get("custom_qty_issued") or 0) > EPS),
                  "cancelled": sum(1 for l in lines if float(l.get("custom_qty_cancelled") or 0) > EPS)},
        "qty": qty,
        "availability": availability,
        "dn": {"count": len(dns), "last": last.get("name") if last else None,
               "last_date": _day(last.get("posting_date")) if last else None},
        "return": ret,
        "flags": row_flags(stage, lines, ret),
    }


# ------------------------------------------------------------------- access
def _require_view():
    user = frappe.session.user
    roles = set(frappe.get_roles(user)) if user != "Guest" else set()
    if user == "Guest" or not roles.intersection(VIEW_ROLES) or not frappe.has_permission("Material Request", "read"):
        frappe.throw("You need a warehouse role and Material Request read access to view the Dispatch Queue.",
                     frappe.PermissionError)
    return roles


def _can_act(roles):
    return bool(set(roles).intersection(ACT_ROLES))


def _batches(names):
    names = list(names)
    for i in range(0, len(names), BATCH):
        yield names[i:i + BATCH]


def _fetch_lines(names):
    lines_by_mr = {}
    for batch in _batches(names):
        for l in frappe.get_list("Material Request Item", parent_doctype="Material Request",
                                 filters={"parent": ["in", batch]}, limit_page_length=0,
                                 fields=["parent", "name", "item_code", "qty", "warehouse", "custom_qty_issued",
                                         "custom_qty_cancelled", "custom_qty_remaining", "custom_cancel_reason"]):
            lines_by_mr.setdefault(l["parent"], []).append(l)
    return lines_by_mr


# DN summary reads use ``get_all`` on purpose. A DN's Employee link fields (dispatched to,
# approved by, initiated by, requestor PM) are covered by each user's Employee User
# Permission, so ``get_list`` would hide DNs addressed to other people and make the queue
# differ per user; and the return state is a permission-level-1 field on Stock Entry that
# Stock User cannot read. The scope is held elsewhere: callers pass only MIR names that came
# from a permission-filtered Material Request ``get_list``, require Stock Entry read, and
# the fields requested here are workflow status only (no employee, party or amount fields).
DN_SUMMARY_FIELDS = ["name", "posting_date", "custom_return_state", "custom_return_closed_on"]
DN_LINE_FIELDS = ["item_code", "qty", "uom", "custom_qty_returned", "custom_qty_custody",
                  "custom_return_disposition"]


def _fetch_dns(names):
    """Outbound (non-return) Material Issue DNs per MIR, de-duplicated. See the note above."""
    dns_by_mr = {}
    for batch in _batches(names):
        details = frappe.get_all("Stock Entry Detail",
                                 filters={"material_request": ["in", batch], "docstatus": 1},
                                 fields=["parent", "material_request"])
        meta = {}
        for pb in _batches(sorted({d["parent"] for d in details})):
            for se in frappe.get_all("Stock Entry",
                                     filters={"name": ["in", pb], "docstatus": 1, "is_return": 0,
                                              "purpose": "Material Issue"},
                                     fields=DN_SUMMARY_FIELDS):
                meta[se["name"]] = se
        seen = set()
        for d in details:
            se = meta.get(d["parent"])
            if se and (d["material_request"], se["name"]) not in seen:
                seen.add((d["material_request"], se["name"]))
                dns_by_mr.setdefault(d["material_request"], []).append(se)
    return dns_by_mr


def _fetch_bins(lines):
    """Stock per item/warehouse for availability.

    Deliberately ``get_all`` (guarded by a Bin read check in the caller): the classification
    must see stock in *other* warehouses, which a warehouse-scoped user could not otherwise
    see. This matches ``sig_kanban_availability_status``; only an aggregate colour leaves the
    server, never a quantity.
    """
    bins = []
    for batch in _batches(sorted({l["item_code"] for l in lines})):
        bins += frappe.get_all("Bin", filters={"item_code": ["in", batch]},
                               fields=["item_code", "warehouse", "actual_qty"])
    return bins


def _strip_dn_fields(row):
    row["return"] = None
    row["flags"] = [f for f in row["flags"] if f != "return_blocks_close"]


# ---------------------------------------------------------------- endpoints
@frappe.whitelist()
def get_queue(include_closed=0, closed_days=30):
    """All open submitted Material Issue MIRs (plus recently closed on request).

    Rows come back newest first; the page owns any other ordering.
    """
    roles = _require_view()
    include_closed = str(include_closed) in ("1", "true", "True")
    try:
        closed_days = max(1, min(365, int(closed_days)))
    except (TypeError, ValueError):
        closed_days = 30
    today = frappe.utils.today()

    fields = ["name", "custom_mir_number", "custom_site", "custom_project", "custom_po_number",
              "custom_work_type", "transaction_date", "schedule_date", "creation", "modified",
              "custom_dispatch_stage"]
    base = [["docstatus", "=", 1], ["material_request_type", "=", "Material Issue"]]
    open_headers = frappe.get_list("Material Request", fields=fields, limit_page_length=MAX_ROWS,
                                   filters=base + [["custom_dispatch_stage", "in", list(OPEN_STAGES)]],
                                   order_by="creation desc")
    closed_headers = []
    if include_closed:
        closed_headers = frappe.get_list("Material Request", fields=fields, limit_page_length=CLOSED_CANDIDATES,
                                         filters=base + [["custom_dispatch_stage", "=", "CLOSED"]],
                                         order_by="creation desc")
    complete = len(open_headers) < MAX_ROWS and len(closed_headers) < CLOSED_CANDIDATES
    if (open_headers or closed_headers) and "custom_dispatch_stage" not in (open_headers or closed_headers)[0]:
        frappe.throw("The dispatch stage is not readable for your role (permission level 1).", frappe.PermissionError)

    dn_access = bool(frappe.has_permission("Stock Entry", "read"))
    all_names = [h["name"] for h in open_headers + closed_headers]
    dns_by_mr = _fetch_dns(all_names) if dn_access else {}

    if closed_headers:
        since = frappe.utils.add_days(today, -closed_days)
        closed_headers = [h for h in closed_headers
                          if closed_on(h, dns_by_mr.get(h["name"], []))[:10] >= str(since)[:10]]
    headers = open_headers + closed_headers
    names = [h["name"] for h in headers]
    lines_by_mr = _fetch_lines(names)

    availability_access = bool(frappe.has_permission("Bin", "read"))
    availability = {}
    if availability_access:
        open_lines = [l for h in open_headers for l in lines_by_mr.get(h["name"], [])
                      if float(l.get("custom_qty_remaining") or 0) > EPS]
        availability = classify_availability(open_lines, _fetch_bins(open_lines))

    rows = [build_row(h, lines_by_mr.get(h["name"], []), dns_by_mr.get(h["name"], []),
                      availability.get(h["name"]) if availability_access else None, today)
            for h in headers]
    if not dn_access:
        for r in rows:
            _strip_dn_fields(r)
    rows.sort(key=lambda r: (r["created"], r["name"]), reverse=True)
    return {"generated_at": frappe.utils.now(), "complete": complete,
            "access": {"dn": dn_access, "availability": availability_access, "can_dispatch": _can_act(roles)},
            "summary": summarize(rows), "rows": rows}


@frappe.whitelist()
def get_mr_detail(mr):
    """One MIR with its lines, outbound DNs and returns, for the side panel and row refresh."""
    roles = _require_view()
    if not mr or not frappe.has_permission("Material Request", "read", doc=mr):
        frappe.throw("Not permitted to read this Material Request.", frappe.PermissionError)
    header = frappe.get_list("Material Request", limit_page_length=1, filters={"name": mr},
                             fields=["name", "custom_mir_number", "custom_site", "custom_project", "custom_po_number",
                                     "custom_work_type", "transaction_date", "schedule_date", "creation", "modified",
                                     "custom_dispatch_stage", "docstatus", "material_request_type"])
    if not header:
        frappe.throw("Material Request not found.", frappe.DoesNotExistError)
    header = header[0]
    if "custom_dispatch_stage" not in header:
        frappe.throw("The dispatch stage is not readable for your role (permission level 1).", frappe.PermissionError)
    lines = frappe.get_list("Material Request Item", parent_doctype="Material Request", limit_page_length=0,
                            filters={"parent": mr}, order_by="idx asc",
                            fields=["name", "parent", "item_code", "item_name", "qty", "uom", "warehouse",
                                    "custom_qty_issued", "custom_qty_cancelled", "custom_qty_remaining",
                                    "custom_line_status", "custom_cancel_reason"])
    dn_access = bool(frappe.has_permission("Stock Entry", "read"))
    dns, returns = [], []
    if dn_access:
        # `mr` passed the document-level read check above; see the note on DN_SUMMARY_FIELDS.
        parents = sorted({d["parent"] for d in frappe.get_all(
            "Stock Entry Detail", filters={"material_request": mr, "docstatus": 1}, fields=["parent"])})
        for se in (frappe.get_all("Stock Entry", order_by="posting_date asc, name asc",
                                  filters={"name": ["in", parents], "docstatus": 1},
                                  fields=DN_SUMMARY_FIELDS + ["purpose", "is_return"])
                   if parents else []):
            if se.get("is_return"):
                returns.append(se)
            elif se.get("purpose") == "Material Issue":
                se["lines"] = frappe.get_all(
                    "Stock Entry Detail", filters={"parent": se["name"], "material_request": mr},
                    order_by="idx asc", fields=DN_LINE_FIELDS)
                dns.append(se)
    availability_access = bool(frappe.has_permission("Bin", "read"))
    availability = None
    if availability_access:
        items = sorted({l["item_code"] for l in lines})
        availability = classify_availability(lines, _fetch_bins(lines)).get(mr) if items else None
    row = build_row(header, lines, dns, availability, frappe.utils.today())
    if not dn_access:
        _strip_dn_fields(row)
    return {"row": row, "lines": lines, "dns": dns, "returns": returns,
            "access": {"dn": dn_access, "availability": availability_access, "can_dispatch": _can_act(roles)}}
