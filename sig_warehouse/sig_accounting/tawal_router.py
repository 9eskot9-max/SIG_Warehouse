"""Tawal tab of the bank router: staged portal evidence, one row per portal payment, drafts for the accountant to post.

The router is the master. The local PC agent only exports the portal and stages it here (stage_rows / stage_reconcile);
recognition, linking and draft creation all happen on the server from ERP data (list_tawal / create_draft / process).
Nothing here ever submits a document.
"""
import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime

from sig_warehouse.sig_accounting.bank_router import tawal_plan as tp
from sig_warehouse.sig_accounting.bank_router.snb_financing import classify_movement

MOVEMENT = "SNB Movement Review"
PAYMENT = "SIG Tawal Payment"
INVOICE = "SIG Tawal Invoice"
SETTINGS = "Bank Router Settings"
PAGE_SIZE = 100
AUTO_DRAFT_BATCH = 25
STALE_HOURS = 72  # no portal export staged for this long raises an alert
GROUPS = {
    "action": tp.ACTION_STATES,  # includes UNALLOCATED: a receipt exists but still needs allocating
    "waiting": {tp.WAITING_BANK},
    "drafts": {tp.DRAFT},
    "posted": {tp.POSTED},
    "legacy": {tp.LEGACY, tp.VOID},
}


def _data(value):
    return frappe.parse_json(value) if isinstance(value, str) else value


def _integration_only():
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER

    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the configured integration owner may run this."), frappe.PermissionError)


def _require_access():
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    for doctype in (MOVEMENT, "Payment Entry", "Sales Invoice"):
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(_("Tawal receipts need read access to {0}.").format(doctype), frappe.PermissionError)


def _settings():
    s = frappe.get_cached_doc(SETTINGS)
    return {"legacy_before": str(s.get("tawal_legacy_before") or "2026-01-01")[:10],
            "allow_bank_reference": bool(s.get("tawal_allow_bank_reference", 1)),
            "auto_draft_enabled": bool(s.get("auto_draft_enabled")),
            "auto_draft_from": str(s.get("auto_draft_from") or "")[:10]}


# ---- staging (written by the local PC agent) -----------------------------------------------------------------
def _write(doc):
    doc.flags.tawal_router_write = True
    doc.flags.ignore_permissions = True
    doc.save()


def _upsert(doctype, name, values, watch=()):
    """Insert or update one staged row; only touches the database when something changed. Returns inserted|updated|unchanged."""
    stamp = now_datetime()
    if not frappe.db.exists(doctype, name):
        doc = frappe.get_doc({"doctype": doctype, **values, "last_seen_at": stamp, "first_seen_at": stamp})
        doc.flags.tawal_router_write = True
        doc.flags.ignore_permissions = True
        doc.insert()
        return "inserted"
    doc = frappe.get_doc(doctype, name)
    def differs(k, v):
        if isinstance(v, float):
            return abs(flt(doc.get(k)) - v) >= 0.005
        return str(doc.get(k) or "") != str(v or "")

    changed = {k: v for k, v in values.items() if differs(k, v)}
    if not changed:
        frappe.db.set_value(doctype, name, "last_seen_at", stamp, update_modified=False)
        return "unchanged"
    if "portal_status" in changed:
        changed["status_changed_at"] = stamp
    doc.update(changed)
    doc.last_seen_at = stamp
    _write(doc)
    return "updated"


@frappe.whitelist(methods=["POST"])
def stage_rows(section, rows, capture_run=""):
    """Upsert one portal export section. Status changes on existing rows are applied (the old sheet hub skipped them)."""
    _integration_only()
    rows = _data(rows)
    if section not in ("payments", "invoices") or not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        frappe.throw(_("Send 1 to 200 payments or invoices per request."))
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for r in rows:
        if section == "payments":
            number = str(r.get("source_record_id") or "").strip()
            if not number:
                frappe.throw(_("A payment row has no payment number."))
            raw = _data(r.get("raw_json")) or {}
            values = {"payment_number": number, "payment_date": str(r.get("event_date") or "")[:10] or None, "amount": flt(r.get("amount")),
                      "portal_status": str(r.get("portal_status") or ""), "invoice_raw": str(r.get("source_line_id") or ""),
                      "remit_account": "".join(c for c in str(raw.get("Remit-to Account") or "") if c.isdigit()),
                      "payment_type": str(raw.get("Payment Type") or ""), "capture_run": capture_run,
                      "raw_json": json.dumps(raw, ensure_ascii=False)}
            counts[_upsert(PAYMENT, number, values)] += 1
        else:
            key = str(r.get("idempotency_key") or "").strip()
            if not key:
                frappe.throw(_("An invoice row has no key."))
            label = str(r.get("source_record_id") or "")
            values = {"row_key": key, "invoice_number": label, "canonical": tp.canonical_invoice(label),
                      "invoice_date": str(r.get("event_date") or "")[:10] or None, "invoice_type": str(_data(r.get("raw_json") or "{}").get("Type") or "Standard"),
                      "amount": flt(r.get("amount")), "invoice_status": str(r.get("portal_status") or ""), "paid_status": str(r.get("paid_status") or ""),
                      "payment_number": str(r.get("payment_number") or ""), "capture_run": capture_run}
            counts[_upsert(INVOICE, key, values)] += 1
    frappe.db.set_single_value(SETTINGS, "tawal_last_capture_at", now_datetime())
    return counts


@frappe.whitelist(methods=["POST"])
def stage_reconcile(entries):
    """Store the portal's reconcile verdict and its invoice allocation rows against staged payments."""
    _integration_only()
    entries = _data(entries)
    if not isinstance(entries, dict) or len(entries) > 500:
        frappe.throw(_("Send at most 500 reconcile entries."))
    stored = 0
    for number, verdict in entries.items():
        if frappe.db.exists(PAYMENT, number):
            payload = {k: verdict.get(k) for k in ("verdict", "hold_code", "parent_amount", "reconciled_total", "allocation_rows", "children", "checked_at")}
            frappe.db.set_value(PAYMENT, number, "reconcile_json", json.dumps(payload, ensure_ascii=False), update_modified=False)
            stored += 1
    return {"stored": stored}


@frappe.whitelist()
def staged_rows(section):
    """Staged rows in the shape the local agent's reconcile step already reads."""
    if frappe.session.user == "Guest" or not frappe.has_permission(PAYMENT, "read"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if section == "payments":
        rows = frappe.get_list(PAYMENT, fields=["payment_number", "payment_date", "amount", "portal_status", "invoice_raw", "raw_json", "payment_entry"],
                               limit_page_length=0)
        return {"ok": True, "rows": [{"source_record_id": r.payment_number, "source_line_id": r.invoice_raw, "event_date": str(r.payment_date or ""),
                                      "amount": r.amount, "portal_status": r.portal_status, "erp_doc": r.payment_entry or "", "raw_json": r.raw_json,
                                      "idempotency_key": "TAWAL|PAYMENT|" + r.payment_number} for r in rows]}
    rows = frappe.get_list(INVOICE, fields=["row_key", "invoice_number", "invoice_date", "amount", "invoice_status", "paid_status", "payment_number", "invoice_type"],
                           limit_page_length=0)
    return {"ok": True, "rows": [{"source_record_id": r.invoice_number, "event_date": str(r.invoice_date or ""), "amount": r.amount, "portal_status": r.invoice_status,
                                  "paid_status": r.paid_status, "payment_number": r.payment_number, "portal_type": r.invoice_type, "idempotency_key": r.row_key}
                                 for r in rows]}


# ---- context + rows -------------------------------------------------------------------------------------------
def _erp_index():
    rows = frappe.get_list("Sales Invoice", filters={"customer": tp.TAWAL_CUSTOMER, "docstatus": 1, "company": tp.COMPANY},
                           fields=["name", "docstatus", "customer", "debit_to", "outstanding_amount", "grand_total"], limit_page_length=0)
    index = {}
    for r in rows:
        key = tp.canonical_invoice(r.name)
        prev = index.get(key)
        if prev is None or (prev["outstanding_amount"] <= 0.005 < r.outstanding_amount):
            index[key] = dict(r)
    return index


def _credit_text(source):
    return " ".join(str(source.get(k) or "") for k in ("detail_description", "transaction_description", "extra_description", "remarks", "reference", "description"))


def _context():
    settings = _settings()
    payments = []
    for p in frappe.get_list(PAYMENT, fields=["payment_number", "payment_date", "amount", "portal_status", "invoice_raw", "remit_account", "reconcile_json",
                                              "bank_movement", "payment_entry"], limit_page_length=0):
        payments.append({"payment_number": p.payment_number, "payment_date": str(p.payment_date or ""), "amount": flt(p.amount),
                         "portal_status": p.portal_status, "invoice_raw": p.invoice_raw, "remit_account": p.remit_account,
                         "reconcile": _data(p.reconcile_json) if p.reconcile_json else None})
    invoices = [{"invoice_number": i.invoice_number, "canonical": i.canonical or tp.canonical_invoice(i.invoice_number), "amount": flt(i.amount),
                 "payment_number": i.payment_number, "type": i.invoice_type}
                for i in frappe.get_list(INVOICE, fields=["invoice_number", "canonical", "amount", "payment_number", "invoice_type"], limit_page_length=0)]
    earliest = min((p["payment_date"] for p in payments if p["payment_date"]), default=settings["legacy_before"])
    credits = []
    for c in frappe.get_list(MOVEMENT, filters={"direction": "CREDIT", "event_date": [">=", add_days(earliest, -tp.REFERENCED_WINDOW_DAYS)]},
                             fields=["name", "event_date", "amount", "source_account_tail", "erp_doctype", "erp_document", "source_json", "modified"], limit_page_length=0):
        text = _credit_text(_data(c.source_json) or {})
        if c.source_account_tail == "3605":
            identified = classify_movement({"account_tail": "3605", "direction": "CREDIT", "description": text}) == "TAWAL_RECEIPT"
            exact_portal = any(tp.references_payment(text, p["payment_number"])
                               and abs(p["amount"] - flt(c.amount)) <= 0.005 for p in payments)
            if not (identified or exact_portal):
                continue
        credits.append({"name": c.name, "event_date": str(c.event_date), "amount": flt(c.amount), "tail": c.source_account_tail,
                        "text": text, "erp_document": c.erp_document or "", "modified": str(c.modified)})
    # A posted bank debit can already represent a TAWAL receipt via a legacy
    # journal or combined entry. Hold a credible existing posting for review.
    financing_credits = [c for c in credits if c["tail"] == "3605" and not c["erp_document"]]
    if financing_credits:
        posting_days = [c["event_date"] for c in financing_credits]
        if frappe.has_permission("GL Entry", "read") and frappe.has_permission("Account", "read"):
            accounts = frappe.get_list("Account", filters={"account_number": "13124", "company": tp.COMPANY,
                                                         "is_group": 0}, fields=["name"], limit_page_length=2)
        else:
            accounts = []
        if len(accounts) != 1:
            for credit in financing_credits:
                credit["erp_document"] = "BANK_LEDGER_REVIEW_REQUIRED"
        else:
            ledger = frappe.get_list("GL Entry", filters={"account": accounts[0].name, "company": tp.COMPANY,
                "is_cancelled": 0, "debit": [">", 0],
                "posting_date": ["between", [add_days(min(posting_days), -3), add_days(max(posting_days), 3)]]},
                fields=["posting_date", "debit", "remarks"], limit_page_length=0)
            for credit in financing_credits:
                day = getdate(credit["event_date"])
                if any(abs((getdate(line.posting_date) - day).days) <= 3
                       and abs(flt(line.debit) - flt(credit["amount"])) <= 0.005 for line in ledger):
                    credit["erp_document"] = "POSSIBLE_EXISTING_BANK_POSTING"
    entries = [dict(e) for e in frappe.get_list("Payment Entry", filters={"party_type": "Customer", "party": tp.TAWAL_CUSTOMER, "docstatus": ["<", 2],
                                                                           "payment_type": "Receive", "company": tp.COMPANY},
                                                fields=["name", "reference_no", "docstatus", "paid_amount", "unallocated_amount", "posting_date"], limit_page_length=0)]
    receivable = frappe.db.get_value("Company", tp.COMPANY, "default_receivable_account") or ""
    return {"settings": settings, "payments": payments, "invoices": invoices, "index": _erp_index(), "credits": credits, "entries": entries,
            "receivable": receivable}


def _rows(ctx, manual_receipts=None):
    rows = tp.plan_all(ctx["payments"], ctx["invoices"], ctx["index"], ctx["credits"], ctx["entries"], settings=ctx["settings"],
                       default_receivable=ctx["receivable"], manual_receipts=manual_receipts)
    by_credit = {c["name"]: c for c in ctx["credits"]}
    linked = {c["name"] for c in ctx["credits"] if c["erp_document"]}
    payments = {p["payment_number"]: p for p in ctx["payments"]}
    for row in rows:
        # An entry that exists but whose bank credit is not linked yet: offer the credit so the accountant can link it.
        if row["entry"] and row["state"] in (tp.POSTED, tp.DRAFT, tp.UNALLOCATED):
            credit, _ref, _issue = tp.match_credit(payments[row["payment_number"]], [c for c in ctx["credits"] if c["name"] not in linked])
            row["credit_to_link"] = credit["name"] if credit else ""
        row["credit_date"] = by_credit[row["credit"]]["event_date"] if row["credit"] in by_credit else ""
    return rows


def _public(row, payments):
    p = payments.get(row["payment_number"]) or {}
    return {"payment_number": row["payment_number"], "payment_date": row["payment_date"], "amount": row["amount"], "portal_status": row["portal_status"],
            "invoice": row["invoice_raw"], "state": row["state"], "reason": row["reason"], "credit": row["credit"], "credit_date": row.get("credit_date", ""),
            "by_reference": row["by_reference"], "entry": row["entry"], "credit_to_link": row.get("credit_to_link", ""), "mode": row["mode"],
            "can_draft": row["can_draft"], "missing_invoices": row["missing_invoices"], "possible_entries": row["possible_entries"],
            "remarks": (row["body"] or {}).get("remarks", ""), "references": [r["reference_name"] for r in ((row["body"] or {}).get("references") or [])],
            "reconciled": bool((p.get("reconcile") or {}).get("verdict") == "RECONCILED")}


@frappe.whitelist()
def list_tawal(group="action", search="", start=0, limit=PAGE_SIZE):
    _require_access()
    if group not in GROUPS:
        frappe.throw(_("Unknown group."))
    ctx = _context()
    rows = _rows(ctx)
    payments = {p["payment_number"]: p for p in ctx["payments"]}
    counts = {g: sum(1 for r in rows if r["state"] in states) for g, states in GROUPS.items()}
    term = str(search or "").strip().lower()
    chosen = [r for r in rows if r["state"] in GROUPS[group]
              and (not term or term in " ".join([r["payment_number"], r["invoice_raw"], str(r["entry"] or ""), str(r["credit"] or "")]).lower())]
    chosen.sort(key=lambda r: (r["payment_date"], r["payment_number"]), reverse=True)
    start, limit = max(0, int(start)), min(200, max(1, int(limit)))
    page = chosen[start:start + limit]
    settings = ctx["settings"]
    stale = _staleness()
    return {"rows": [_public(r, payments) for r in page], "counts": counts, "has_more": start + limit < len(chosen), "next_start": start + limit,
            "settings": {"forward_from": settings["legacy_before"], "auto_draft": settings["auto_draft_enabled"], "auto_draft_from": settings["auto_draft_from"],
                         "accept_bank_reference": settings["allow_bank_reference"]},
            "freshness": stale}


# ---- draft creation ------------------------------------------------------------------------------------------
def _account_for_gl(number):
    name = frappe.db.get_value("Account", {"account_number": number, "company": tp.COMPANY, "is_group": 0, "disabled": 0}, "name")
    if not name:
        frappe.throw(_("Bank account {0} is not set up in ERP.").format(number))
    return name


def _verify_draft(entry, body):
    entry.reload()
    refs = {(r.reference_name, round(flt(r.allocated_amount), 2)) for r in entry.references}
    want = {(r["reference_name"], round(r["allocated_amount"], 2)) for r in body["references"]}
    if entry.docstatus != 0 or entry.reference_no != body["reference_no"] or abs(flt(entry.paid_amount) - body["paid_amount"]) > 0.01 or refs != want:
        frappe.throw(_("The draft read back differently from the plan; it was not linked. Review {0}.").format(entry.name))


def _create(row, credit_modified):
    body = dict(row["body"])
    frappe.db.sql("SELECT name FROM `tabSIG Tawal Payment` WHERE name=%s FOR UPDATE", (row["payment_number"],))
    existing = frappe.db.get_value(PAYMENT, row["payment_number"], "payment_entry")
    if existing or frappe.db.exists("Payment Entry", {"company": tp.COMPANY, "payment_type": "Receive", "reference_no": body["reference_no"], "docstatus": ["<", 2]}):
        frappe.throw(_("A receipt for this Tawal payment already exists. Refresh the list."))
    gl = body.pop("paid_to_gl")
    body["paid_to"] = _account_for_gl(gl)
    body["paid_from"] = row["paid_from"]
    if not row["credit"]:
        entry = frappe.get_doc(body)
        entry.insert()
        _verify_draft(entry, body)
        frappe.db.set_value(PAYMENT, row["payment_number"], {"payment_entry": entry.name}, update_modified=False)
        return entry.name
    movement = frappe.get_doc(MOVEMENT, row["credit"])
    frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (movement.name,))
    movement.reload()
    if movement.erp_document or (credit_modified and str(movement.modified) != str(credit_modified)):
        frappe.throw(_("The bank credit changed or is already linked. Refresh and try again."))
    entry = frappe.get_doc(body)
    entry.insert()  # permission-checked: the user needs Payment Entry create access
    _verify_draft(entry, body)
    movement.erp_doctype, movement.erp_document, movement.link_method = "Payment Entry", entry.name, "TAWAL"
    movement.business_route = "client_receipt"
    movement.engine_state, movement.decision_type = "DRAFT_READY", ""
    movement.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": "{}",
                              "decision_json": json.dumps({"tawal_payment": row["payment_number"], "draft": entry.name, "mode": row["mode"],
                                                           "by_reference": row["by_reference"]}, ensure_ascii=False)})
    movement.flags.snb_router_write = True
    movement.save()
    if frappe.db.exists(PAYMENT, row["payment_number"]):
        frappe.db.set_value(PAYMENT, row["payment_number"], {"payment_entry": entry.name, "bank_movement": movement.name}, update_modified=False)
    return entry.name


def _row_for(payment_number, ctx=None, confirm_possible=False, manual_receipt=None):
    ctx = ctx or _context()
    if confirm_possible:
        first = next((r for r in _rows(ctx) if r["payment_number"] == payment_number), None)
        if first and first["state"] == tp.POSSIBLE_EXISTING:
            ctx["entries"] = [e for e in ctx["entries"] if e["name"] not in first["possible_entries"]]
    row = next((r for r in _rows(ctx, {payment_number: manual_receipt} if manual_receipt else None) if r["payment_number"] == payment_number), None)
    if not row:
        frappe.throw(_("Payment {0} is not staged.").format(payment_number))
    return row, ctx


@frappe.whitelist(methods=["POST"])
def create_draft(payment_number, confirm_possible=0, bank_tail=None, receipt_date=None):
    """Create ONE draft Receive Payment Entry from a fresh plan (never from what the page showed). The accountant posts it."""
    _require_access()
    if not frappe.has_permission("Payment Entry", "create") or not frappe.has_permission(MOVEMENT, "write"):
        frappe.throw(_("You need permission to create a Payment Entry and update bank movements."), frappe.PermissionError)
    payment_number = str(payment_number).strip()
    frappe.db.sql("SELECT name FROM `tabSIG Tawal Payment` WHERE name=%s FOR UPDATE", (payment_number,))
    manual_receipt = None
    if bank_tail or receipt_date:
        if str(bank_tail) not in tp.BANK_GL_BY_TAIL or not receipt_date:
            frappe.throw(_("Choose a bank account and receipt date."))
        if _staleness()["stale"]:
            frappe.throw(_("Refresh the Tawal portal export before creating this draft."))
        last_seen = frappe.db.get_value(PAYMENT, payment_number, "last_seen_at")
        if not last_seen or (now_datetime() - last_seen).total_seconds() > STALE_HOURS * 3600:
            frappe.throw(_("This payment was not present in a recent Tawal export."))
        manual_receipt = {"tail": str(bank_tail), "date": str(getdate(receipt_date))}
    row, ctx = _row_for(payment_number, confirm_possible=bool(int(confirm_possible or 0)), manual_receipt=manual_receipt)
    if not row["can_draft"]:
        frappe.throw(_("This payment cannot be drafted now: {0} ({1}).").format(row["state"], row["reason"] or "-"))
    name = _create(row, next((c["modified"] for c in ctx["credits"] if c["name"] == row["credit"]), ""))
    return {"entry": name, "mode": row["mode"]}


@frappe.whitelist(methods=["POST"])
def link_entry(payment_number):
    """Link a Payment Entry that already exists for this payment to its bank credit (no new document)."""
    _require_access()
    if not frappe.has_permission(MOVEMENT, "write"):
        frappe.throw(_("You need permission to update bank movements."), frappe.PermissionError)
    row, ctx = _row_for(str(payment_number).strip())
    if not row["entry"] or not row.get("credit_to_link"):
        frappe.throw(_("There is no unlinked bank credit to link for this payment."))
    movement = frappe.get_doc(MOVEMENT, row["credit_to_link"])
    frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (movement.name,))
    movement.reload()
    if movement.erp_document:
        frappe.throw(_("That bank credit is already linked."))
    if frappe.db.exists(MOVEMENT, {"erp_doctype": "Payment Entry", "erp_document": row["entry"]}):
        frappe.throw(_("That Payment Entry is already linked to another bank credit."))
    movement.erp_doctype, movement.erp_document, movement.link_method = "Payment Entry", row["entry"], "TAWAL"
    movement.business_route = "client_receipt"
    movement.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": "{}",
                              "decision_json": json.dumps({"tawal_payment": row["payment_number"], "linked": row["entry"]}, ensure_ascii=False)})
    movement.flags.snb_router_write = True
    movement.save()
    if frappe.db.exists(PAYMENT, row["payment_number"]):
        frappe.db.set_value(PAYMENT, row["payment_number"], {"payment_entry": row["entry"], "bank_movement": movement.name}, update_modified=False)
    return {"entry": row["entry"], "movement": movement.name}


# ---- scheduled processing, alerts, run report ---------------------------------------------------------------
def _alert(key, text):
    if frappe.db.exists("ToDo", {"reference_type": SETTINGS, "description": ["like", "[%s]%%" % key], "status": "Open"}):
        return
    from sig_warehouse.sig_warehouse.field_feed import _alert_user

    frappe.get_doc({"doctype": "ToDo", "allocated_to": _alert_user({}), "status": "Open", "priority": "High", "reference_type": SETTINGS,
                    "reference_name": SETTINGS, "description": "[%s] %s" % (key, text)}).insert(ignore_permissions=True)


def _close_alert(key):
    for n in frappe.get_all("ToDo", filters={"description": ["like", "[%s]%%" % key], "status": "Open"}, pluck="name"):
        frappe.db.set_value("ToDo", n, "status", "Closed")


def _staleness():
    last = frappe.db.get_single_value(SETTINGS, "tawal_last_capture_at")
    hours = (now_datetime() - last).total_seconds() / 3600 if last else None
    return {"last_capture_at": str(last or ""), "hours": round(hours, 1) if hours is not None else None, "stale": hours is None or hours > STALE_HOURS}


def process(create=None):
    """Recognise, link and (only when the owner switched auto-drafting on) draft. Safe to run any time; never submits."""
    ctx = _context()
    rows = _rows(ctx)
    settings = ctx["settings"]
    auto = settings["auto_draft_enabled"] and settings["auto_draft_from"] if create is None else bool(create)
    drafted = linked = failed = 0
    for row in rows:
        if row["entry"] and frappe.db.exists(PAYMENT, row["payment_number"]):
            if frappe.db.get_value(PAYMENT, row["payment_number"], "payment_entry") != row["entry"]:
                frappe.db.set_value(PAYMENT, row["payment_number"], "payment_entry", row["entry"], update_modified=False)
                linked += 1
    if auto:
        floor = settings["auto_draft_from"] or settings["legacy_before"]
        for row in [r for r in rows if r["can_draft"] and r["payment_date"] >= floor][:AUTO_DRAFT_BATCH]:
            try:
                _create(row, next((c["modified"] for c in ctx["credits"] if c["name"] == row["credit"]), ""))
                drafted += 1
            except Exception:
                frappe.db.rollback()
                frappe.log_error(title="Tawal auto-draft failed", message="Payment " + row["payment_number"] + "\n" + frappe.get_traceback())
                failed += 1
    stale = _staleness()
    if stale["stale"]:
        _alert("SIG-TAWAL-STALE", "No Tawal portal export has been staged for over %d hours (last: %s). Check the Tawal Chrome login on the PC." % (STALE_HOURS, stale["last_capture_at"] or "never"))
    else:
        _close_alert("SIG-TAWAL-STALE")
    frappe.db.commit()
    return {"rows": len(rows), "linked": linked, "drafted": drafted, "failed": failed,
            "states": {s: sum(1 for r in rows if r["state"] == s) for s in {r["state"] for r in rows}}}


def run_scheduled():
    process()


@frappe.whitelist(methods=["POST"])
def run_process(create=None):
    _integration_only()
    return process(None if create is None else int(create))


@frappe.whitelist()
def status():
    """Cheap preflight for the PC agent: is the server side ready and how fresh is the staged evidence."""
    _integration_only()
    s = _settings()
    return {"staged_payments": frappe.db.count(PAYMENT), "staged_invoices": frappe.db.count(INVOICE), "freshness": _staleness(),
            "auto_draft": s["auto_draft_enabled"], "auto_draft_from": s["auto_draft_from"], "forward_from": s["legacy_before"]}


@frappe.whitelist(methods=["POST"])
def report_run(status, error="", detail=""):
    """The PC agent reports each run; a failed or login-waiting run raises one deduplicated ToDo, a good run clears it."""
    _integration_only()
    status = str(status)[:60]
    frappe.db.set_single_value(SETTINGS, {"tawal_last_run_status": status + " " + str(now_datetime())[:16], "tawal_last_run_error": str(error)[:900]})
    if status in ("failed", "waiting_login"):
        _alert("SIG-TAWAL-RUN", "The Tawal PC run %s. %s %s" % (status, str(error)[:200], str(detail)[:200]))
    elif status == "ok":
        _close_alert("SIG-TAWAL-RUN")
    return {"status": status}
