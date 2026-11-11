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
SORT_MODES = ("newest", "waiting", "attention")
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
    """Worst custom_return_state across outbound DNs. NONE when there is no DN."""
    worst = "NONE"
    for dn in dns:
        state = str(dn.get("custom_return_state") or "PENDING").upper()
        if state not in RETURN_RANK:
            state = "PENDING"
        # PENDING/PARTIAL outrank DECLARED; with no DN the state stays NONE.
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
    if stage == "DISPATCHED" and return_state in ("PENDING", "PARTIAL", "NONE"):
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


def sort_rows(rows, mode="newest"):
    if mode not in SORT_MODES:
        mode = "newest"
    if mode == "waiting":
        waiting = [r for r in rows if r.get("stage") in ("PENDING", "PARTIAL")]
        rest = [r for r in rows if r.get("stage") not in ("PENDING", "PARTIAL")]
        waiting.sort(key=lambda r: (str(r.get("required_by") or "9999-12-31"), str(r.get("created") or "")))
        rest.sort(key=lambda r: str(r.get("created") or ""), reverse=True)
        return waiting + rest
    if mode == "attention":
        def key(r):
            av = 0 if r.get("availability") == "red" else 1
            flag = 0 if "return_blocks_close" in (r.get("flags") or []) else 1
            return (av, flag, -int(r.get("age_days") or 0), str(r.get("name") or ""))
        return sorted(rows, key=key)
    return sorted(rows, key=lambda r: (str(r.get("created") or ""), str(r.get("name") or "")), reverse=True)


def search_haystack(row):
    return " ".join(str(row.get(k) or "") for k in ("name", "mir", "site", "project", "po", "work_type")).lower()


def _day(value):
    return str(value)[:10] if value else None


def _age_days(created, today):
    try:
        from datetime import date
        y, m, d = (int(x) for x in str(created)[:10].split("-"))
        ty, tm, td = (int(x) for x in str(today)[:10].split("-"))
        return max(0, (date(ty, tm, td) - date(y, m, d)).days)
    except Exception:
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


# ---------------------------------------------------------------- endpoints
@frappe.whitelist()
def get_queue(include_closed=0, closed_days=30):
    """All open submitted Material Issue MIRs (plus recently closed on request)."""
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
    headers = frappe.get_list("Material Request", fields=fields, limit_page_length=MAX_ROWS,
                              filters=base + [["custom_dispatch_stage", "in", list(OPEN_STAGES)]],
                              order_by="creation desc")
    if include_closed:
        since = frappe.utils.add_days(today, -closed_days)
        headers += frappe.get_list("Material Request", fields=fields, limit_page_length=MAX_ROWS,
                                   filters=base + [["custom_dispatch_stage", "=", "CLOSED"], ["modified", ">=", since]],
                                   order_by="creation desc")
    complete = len(headers) < MAX_ROWS
    if headers and "custom_dispatch_stage" not in headers[0]:
        frappe.throw("The dispatch stage is not readable for your role (permission level 1).", frappe.PermissionError)
    names = [h["name"] for h in headers]

    lines_by_mr = {}
    for batch in _batches(names):
        for l in frappe.get_list("Material Request Item", parent_doctype="Material Request",
                                 filters={"parent": ["in", batch]}, limit_page_length=0,
                                 fields=["parent", "name", "item_code", "qty", "warehouse", "custom_qty_issued",
                                         "custom_qty_cancelled", "custom_qty_remaining", "custom_cancel_reason"]):
            lines_by_mr.setdefault(l["parent"], []).append(l)

    dn_access = bool(frappe.has_permission("Stock Entry", "read"))
    dns_by_mr = {}
    if dn_access:
        for batch in _batches(names):
            details = frappe.get_list("Stock Entry Detail", parent_doctype="Stock Entry", limit_page_length=0,
                                      filters={"material_request": ["in", batch], "docstatus": 1},
                                      fields=["parent", "material_request"])
            parents = sorted({d["parent"] for d in details})
            meta = {}
            for pb in _batches(parents):
                for se in frappe.get_list("Stock Entry", limit_page_length=0,
                                          filters={"name": ["in", pb], "docstatus": 1, "is_return": 0,
                                                   "purpose": "Material Issue"},
                                          fields=["name", "posting_date", "custom_return_state"]):
                    meta[se["name"]] = se
            seen = set()
            for d in details:
                se = meta.get(d["parent"])
                if se and (d["material_request"], se["name"]) not in seen:
                    seen.add((d["material_request"], se["name"]))
                    dns_by_mr.setdefault(d["material_request"], []).append(se)

    availability_access = bool(frappe.has_permission("Bin", "read"))
    availability = {}
    if availability_access:
        open_lines = [l for ls in lines_by_mr.values() for l in ls
                      if float(l.get("custom_qty_remaining") or 0) > EPS]
        items = sorted({l["item_code"] for l in open_lines})
        bins = []
        for batch in _batches(items):
            bins += frappe.get_list("Bin", filters={"item_code": ["in", batch]}, limit_page_length=0,
                                    fields=["item_code", "warehouse", "actual_qty"])
        availability = classify_availability(open_lines, bins)

    rows = [build_row(h, lines_by_mr.get(h["name"], []), dns_by_mr.get(h["name"], []),
                      availability.get(h["name"]) if availability_access else None, today)
            for h in headers]
    for r in rows:
        if not dn_access:
            r["return"] = None
            r["flags"] = [f for f in r["flags"] if f != "return_blocks_close"]
    return {"generated_at": frappe.utils.now(), "complete": complete,
            "access": {"dn": dn_access, "availability": availability_access, "can_dispatch": _can_act(roles)},
            "summary": summarize(rows), "rows": sort_rows(rows, "newest")}


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
        parents = sorted({d["parent"] for d in frappe.get_list(
            "Stock Entry Detail", parent_doctype="Stock Entry", limit_page_length=0,
            filters={"material_request": mr, "docstatus": 1}, fields=["parent"])})
        for se in (frappe.get_list("Stock Entry", limit_page_length=0, order_by="posting_date asc, name asc",
                                   filters={"name": ["in", parents], "docstatus": 1},
                                   fields=["name", "posting_date", "purpose", "is_return", "custom_return_state"])
                   if parents else []):
            if se.get("is_return"):
                returns.append(se)
            elif se.get("purpose") == "Material Issue":
                se["lines"] = frappe.get_list(
                    "Stock Entry Detail", parent_doctype="Stock Entry", limit_page_length=0,
                    filters={"parent": se["name"], "material_request": mr}, order_by="idx asc",
                    fields=["item_code", "qty", "uom", "custom_qty_returned", "custom_qty_custody",
                            "custom_return_disposition"])
                dns.append(se)
    availability_access = bool(frappe.has_permission("Bin", "read"))
    availability = None
    if availability_access:
        items = sorted({l["item_code"] for l in lines})
        bins = frappe.get_list("Bin", filters={"item_code": ["in", items]}, limit_page_length=0,
                               fields=["item_code", "warehouse", "actual_qty"]) if items else []
        availability = classify_availability(lines, bins).get(mr)
    row = build_row(header, lines, dns, availability, frappe.utils.today())
    if not dn_access:
        row["return"] = None
        row["flags"] = [f for f in row["flags"] if f != "return_blocks_close"]
    return {"row": row, "lines": lines, "dns": dns, "returns": returns,
            "access": {"dn": dn_access, "availability": availability_access, "can_dispatch": _can_act(roles)}}
