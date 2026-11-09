"""Bank Router API: ingestion, the routing engine, the inbox and the owner's routing actions.

The engine (bank_router/) decides; this module is permissions, locking, audit and the page's data. Nothing here
submits an accounting document.
"""
import hashlib
import json
import re

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from sig_warehouse.sig_accounting.bank_router import runtime
from sig_warehouse.sig_accounting.bank_router.classify import CUSTOMER_RECEIPT, DRAFTABLE, EXPENSE_PAYMENT, SUPPLIER_PAYMENT
from sig_warehouse.sig_accounting.bank_router.text import hint_key, normalize_text

DOCTYPE = "SNB Movement Review"
COUNTERPARTY = "Bank Counterparty"
IDENTIFIER = "Bank Counterparty Identifier"
TABS = {
    "needs": ["NEEDS_YOU"],
    "drafts": ["DRAFT_READY"],
    "posted": ["POSTED"],
    "deferred": ["DEFERRED", "PENDING"],
}
PARTY_DOCTYPES = {"Customer", "Supplier"}
PARTY_LABEL = {"Customer": "customer_name", "Supplier": "supplier_name"}
# Defaults for a party created from the router, matching what TX Manager and the existing masters use.
NEW_PARTY_DEFAULTS = {"Supplier": {"supplier_group": "Local", "supplier_type": "Company"},
                      "Customer": {"customer_group": "Commercial", "territory": "Saudi Arabia", "customer_type": "Company"}}


def _data(value):
    return frappe.parse_json(value) if isinstance(value, str) else value


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _require(permission):
    if frappe.session.user == "Guest" or not frappe.has_permission(DOCTYPE, permission):
        frappe.throw(_("You do not have permission for bank movement review."), frappe.PermissionError)


def _integration_only():
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the configured movement integration owner may run this."), frappe.PermissionError)


def _check_link(doctype, name):
    if name:
        frappe.get_doc(doctype, name).check_permission("read")


# ---- ingestion ---------------------------------------------------------------------------------------------
DERIVED = ("related_fee_rows", "related_main_key", "related_main_id", "category", "am_category_status", "transfer_request", "am_beneficiary_mapping")


@frappe.whitelist(methods=["POST"])
def ingest(items):
    """Import statement evidence, preserving previous decisions. Exact repeats are idempotent; changed evidence is reported, never overwritten."""
    _require("create")
    _integration_only()
    rows = _data(items)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        frappe.throw(_("Send between 1 and 100 movements per request."))
    results = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("source"), dict):
            frappe.throw(_("Invalid movement item."))
        source = item["source"]
        key = str(item.get("id") or "").strip()
        if not key or len(key) > 140 or source.get("direction") not in ("CREDIT", "DEBIT") or not source.get("event_date"):
            frappe.throw(_("Movement identity, date, and direction are required."))
        source_json = _json(source)
        if len(source_json) > 50000:
            frappe.throw(_("Movement evidence exceeds the size limit."))
        scope = str(item.get("account_scope_hash") or "").lower()
        if scope and not re.fullmatch(r"[0-9a-f]{64}", scope):
            frappe.throw(_("Invalid account scope fingerprint."))
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        if frappe.db.exists(DOCTYPE, name):
            frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (name,))
            doc = frappe.get_doc(DOCTYPE, name)
            doc.check_permission("read")
            if doc.source_key != key or doc.source_json != source_json:
                results.append({"id": key, "status": "SOURCE_CONFLICT", "name": name})
                continue
            changed, scope_changed = False, False
            if scope:
                if doc.account_scope_hash and doc.account_scope_hash != scope:
                    results.append({"id": key, "status": "ACCOUNT_SCOPE_CONFLICT", "name": name})
                    continue
                if not doc.account_scope_hash:
                    doc.account_scope_hash, scope_changed = scope, True
            old = _data(doc.recognition_json) or {}
            new = item.get("recognition") or {}
            for field in DERIVED:
                if field in new and old.get(field) != new[field]:
                    old[field], changed = new[field], True
            if changed:
                doc.recognition_json = _json(old)
            hint = _data(doc.erp_hint_json) or {}
            incoming = str(((item.get("erp") or {}).get("linked_doc")) or "").strip()
            current = str(hint.get("linked_doc") or "").strip()
            if current and incoming and current != incoming:
                results.append({"id": key, "status": "HINT_CONFLICT", "name": name})
                continue
            if incoming and not current:
                hint.update({"linked_doc": incoming, "readback_status": "NEEDS_LIVE_READBACK"})
                doc.erp_hint_json = _json(hint)
                status = "HINT_UPDATED"
            elif changed or scope_changed:
                status = "DERIVED_UPDATED" if changed else "ACCOUNT_SCOPE_UPDATED"
            else:
                results.append({"id": key, "status": "EXISTS", "name": name})
                continue
            doc.flags.snb_router_write = True
            doc.save()
            results.append({"id": key, "status": status, "name": name})
            continue
        doc = frappe.new_doc(DOCTYPE)
        doc.update({"source_hash": name, "source_key": key, "event_date": source["event_date"],
                    "source_account_tail": str(source.get("account_tail") or "")[-4:], "account_scope_hash": scope,
                    "direction": source["direction"], "amount": flt(source.get("signed_amount")), "currency": source.get("currency") or "SAR",
                    "source_json": source_json, "recognition_json": _json(item.get("recognition") or {}),
                    "erp_hint_json": _json(item.get("erp") or {}), "review_status": "PENDING", "engine_state": "PENDING"})
        doc.flags.snb_router_write = True
        doc.insert()
        results.append({"id": key, "status": "CREATED", "name": name})
    return results


# ---- engine ------------------------------------------------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def sync_counterparties(rows):
    """Seed the counterparty registry from the Am beneficiary list. Idempotent; never overwrites a filled field."""
    _integration_only()
    from sig_warehouse.sig_accounting.bank_router import seed
    rows = _data(rows)
    if not isinstance(rows, list) or len(rows) > 500:
        frappe.throw(_("Send up to 500 beneficiaries per request."))
    return seed.apply(rows)


@frappe.whitelist(methods=["POST"])
def run_engine(phase="main", start=0, limit=120):
    """Route one batch of movements. The sync calls 'main' until it reports no more, then 'fees'."""
    _integration_only()
    if phase not in ("main", "fees"):
        frappe.throw(_("Unknown phase."))
    return runtime.run(phase, max(0, int(start)), min(300, max(1, int(limit))))


@frappe.whitelist()
def list_links(start=0, limit=200):
    """Document links ERP holds, for the sync to write back to Sheet Am. Identity and document name only."""
    _integration_only()
    start, limit = max(0, int(start)), min(500, max(1, int(limit)))
    rows = frappe.get_all(DOCTYPE, filters={"erp_document": ["!=", ""]},
                          fields=["source_key", "erp_doctype", "erp_document", "link_method", "signals_json"], order_by="name asc", start=start, page_length=limit)
    return {"rows": [{"source_key": r.source_key, "erp_doctype": r.erp_doctype, "erp_document": r.erp_document, "link_method": r.link_method,
                      "am_link_rejected": bool((_data(r.signals_json) or {}).get("am_link_rejected"))} for r in rows],
            "has_more": len(rows) == limit, "next_start": start + len(rows)}


@frappe.whitelist()
def engine_status():
    _require("read")
    settings = runtime.Settings()
    counts = {row.engine_state: row.n for row in frappe.db.sql(
        "select engine_state, count(*) n from `tabSNB Movement Review` group by engine_state", as_dict=True)}
    return {"auto_draft": settings._enabled, "auto_draft_from": str(settings._from or ""), "banks_configured": len(settings.scopes),
            "holding_customer": bool(settings.holding_customer), "counts": counts}


# ---- inbox -------------------------------------------------------------------------------------------------
def _doc_status(rows):
    """Current docstatus of every linked document, read fresh so Finance's own submits show at once."""
    by_type = {}
    for r in rows:
        if r.get("erp_document"):
            by_type.setdefault(r["erp_doctype"], set()).add(r["erp_document"])
    out = {}
    for doctype, names in by_type.items():
        if doctype not in ("Payment Entry", "Journal Entry") or not frappe.has_permission(doctype, "read"):
            continue
        for d in frappe.get_all(doctype, filters={"name": ["in", list(names)]}, fields=["name", "docstatus"], limit_page_length=0):
            out[(doctype, d.name)] = d.docstatus
    return out


def _payload(doc, fees=None, statuses=None):
    source = _data(doc.source_json) or {}
    recognition = _data(doc.recognition_json) or {}
    signals = _data(doc.signals_json) or {}
    statuses = statuses or {}
    mapping = recognition.get("am_beneficiary_mapping") or {}
    return {
        "name": doc.name, "modified": str(doc.modified), "event_date": str(doc.event_date), "amount": flt(doc.amount), "currency": doc.currency,
        "account_tail": doc.source_account_tail, "bank": str(source.get("bank") or "SNB"), "direction": doc.direction,
        "engine_state": doc.engine_state, "decision_type": doc.decision_type or "", "kind": doc.kind or "",
        "counterparty": doc.counterparty or "", "counterparty_name": frappe.db.get_value(COUNTERPARTY, doc.counterparty, "display_name") if doc.counterparty else "",
        "display_name": (signals.get("display_name") or mapping.get("beneficiary_name") or "")[:140],
        "route_source": doc.route_source or "", "erp_doctype": doc.erp_doctype or "", "erp_document": doc.erp_document or "",
        "doc_status": statuses.get((doc.erp_doctype, doc.erp_document)), "link_method": doc.link_method or "",
        "category": recognition.get("category") if recognition.get("am_category_status") == "MATCHED" else "",
        "signals": signals, "candidates": _data(doc.candidates_json) or {}, "reference": source.get("reference", ""),
        "narrative": "\n".join(str(source.get(k) or "") for k in ("transaction_description", "detail_description", "extra_description", "remarks") if source.get(k)),
        "fees": fees or [], "notes": doc.notes or "", "parent_movement": doc.parent_movement or "",
    }


def _fees_for(names):
    if not names:
        return {}
    out = {}
    for r in frappe.get_all(DOCTYPE, filters={"parent_movement": ["in", names]},
                            fields=["name", "parent_movement", "amount", "source_json", "erp_doctype", "erp_document"], limit_page_length=0):
        family = (_data(r.source_json) or {}).get("parser_family", "")
        out.setdefault(r.parent_movement, []).append({"name": r.name, "amount": flt(r.amount), "family": family,
                                                      "erp_doctype": r.erp_doctype or "", "erp_document": r.erp_document or ""})
    return out


@frappe.whitelist()
def list_inbox(tab="needs", bank="ALL", search="", start=0, limit=50):
    _require("read")
    if tab not in TABS:
        frappe.throw(_("Unknown tab."))
    start, limit = max(0, int(start)), min(100, max(1, int(limit)))
    filters = {"engine_state": ["in", TABS[tab]]}
    if tab == "deferred":
        filters["kind"] = ["!=", "BANK_CHARGE"]
    or_filters = None
    term = str(search or "").strip()
    if term:
        like = f"%{term}%"
        or_filters = [["source_json", "like", like], ["erp_document", "like", like], ["counterparty", "like", like]]
    rows = frappe.get_list(DOCTYPE, filters=filters, or_filters=or_filters, fields=["name"], order_by="event_date desc, name asc",
                           start=start, page_length=limit)
    docs = [frappe.get_doc(DOCTYPE, r.name) for r in rows]
    fees = _fees_for([d.name for d in docs])
    statuses = _doc_status([{"erp_doctype": d.erp_doctype, "erp_document": d.erp_document} for d in docs] +
                           [{"erp_doctype": f["erp_doctype"], "erp_document": f["erp_document"]} for v in fees.values() for f in v])
    items = []
    for d in docs:
        d.check_permission("read")
        p = _payload(d, [{**f, "doc_status": statuses.get((f["erp_doctype"], f["erp_document"]))} for f in fees.get(d.name, [])], statuses)
        if bank == "ALL" or p["bank"].upper() == bank:
            items.append(p)
    counts = {t: frappe.db.count(DOCTYPE, {"engine_state": ["in", states]}) for t, states in TABS.items()}
    return {"items": items, "counts": counts, "has_more": len(rows) == limit}


@frappe.whitelist()
def get_movement(name):
    _require("read")
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("read")
    fees = _fees_for([name])
    statuses = _doc_status([{"erp_doctype": doc.erp_doctype, "erp_document": doc.erp_document}] +
                           [{"erp_doctype": f["erp_doctype"], "erp_document": f["erp_document"]} for f in fees.get(name, [])])
    return _payload(doc, [{**f, "doc_status": statuses.get((f["erp_doctype"], f["erp_document"]))} for f in fees.get(name, [])], statuses)


# ---- parties and accounts ----------------------------------------------------------------------------------
@frappe.whitelist()
def search_parties(doctype, query=""):
    _require("read")
    if doctype not in PARTY_DOCTYPES or not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You do not have permission to search this party type."), frappe.PermissionError)
    term = str(query or "").strip()
    if len(term) < 2:
        return []
    field = PARTY_LABEL[doctype]
    rows = frappe.get_list(doctype, filters={"disabled": 0}, or_filters={"name": ["like", f"%{term}%"], field: ["like", f"%{term}%"]},
                           fields=["name", field], order_by=f"{field} asc", page_length=30)
    return [{"name": r.name, "label": f"{r.get(field) or r.name} · {r.name}"} for r in rows]


@frappe.whitelist()
def search_expense_accounts(query=""):
    _require("read")
    term = str(query or "").strip()
    if len(term) < 1:
        return []
    rows = frappe.get_list("Account", filters={"root_type": "Expense", "is_group": 0, "disabled": 0, "company": runtime.documents.COMPANY},
                           or_filters={"name": ["like", f"%{term}%"], "account_number": ["like", f"{term}%"]},
                           fields=["name"], order_by="account_number asc", page_length=30)
    return [{"name": r.name, "label": r.name} for r in rows]


def _new_party(doctype, name, vat=""):
    """Create a Customer or Supplier only when no enabled party already carries that exact name."""
    name = str(name or "").strip()
    if len(name) < 3 or len(name) > 140:
        frappe.throw(_("Enter the party's full name."))
    field = PARTY_LABEL[doctype]
    same = [r for r in frappe.get_all(doctype, filters={"disabled": 0}, fields=["name", field], limit_page_length=0)
            if normalize_text(r.get(field)) == normalize_text(name)]
    if same:
        frappe.throw(_("{0} already exists: {1}. Select it instead.").format(doctype, ", ".join(r.name for r in same)))
    if not frappe.has_permission(doctype, "create"):
        # Live permissions: Accounts User can create Customers but not Suppliers. Say so plainly, not as a raw Frappe error.
        frappe.throw(_("You cannot create a new {0}. Ask an Accounts Manager, or choose an existing one.").format(doctype), frappe.PermissionError)
    values = {"doctype": doctype, field: name, **NEW_PARTY_DEFAULTS[doctype]}
    if vat:
        values["tax_id"] = str(vat).strip()[:30]
    doc = frappe.get_doc(values)
    doc.insert()
    return doc.name


# ---- routing actions ---------------------------------------------------------------------------------------
def _lock(name, modified):
    frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (name,))
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw(_("This movement changed since you opened it. Refresh and try again."))
    return doc


def _ensure_counterparty(doc, label):
    if doc.counterparty and frappe.db.exists(COUNTERPARTY, doc.counterparty):
        return frappe.get_doc(COUNTERPARTY, doc.counterparty)
    cp = frappe.get_doc({"doctype": COUNTERPARTY, "display_name": (label or "Unnamed counterparty")[:140], "status": "ACTIVE"})
    # The movement was permission-checked by the caller. The registry itself is owner-maintained, so it is written
    # as the integration owner and the acting user is recorded in the movement's audit instead.
    cp.flags.bank_router_write = True
    cp.insert(ignore_permissions=True)
    return cp


def _learn_identifiers(doc, cp):
    """Attach this line's identifiers to the counterparty. An identifier held by someone else moves here (the owner decided)."""
    signals = _data(doc.signals_json) or {}
    for kind, value in signals.get("identifiers") or []:
        key = runtime.identity_key(kind, value)
        existing = frappe.db.exists(IDENTIFIER, key)
        if existing:
            ident = frappe.get_doc(IDENTIFIER, key)
            if ident.counterparty != cp.name or ident.status != "ACTIVE":
                ident.counterparty, ident.status, ident.source = cp.name, "ACTIVE", "ROUTER"
                ident.flags.bank_router_write = True
                ident.save(ignore_permissions=True)
            continue
        ident = frappe.get_doc({"doctype": IDENTIFIER, "identity_key": key, "counterparty": cp.name, "kind": kind, "value": str(value)[:140],
                                "normalized": hint_key(kind, value), "status": "ACTIVE", "source": "ROUTER", "first_seen": frappe.utils.nowdate()})
        ident.flags.bank_router_write = True
        ident.insert(ignore_permissions=True)


def _retarget_draft(doc, kind, target, cp):
    """Change the party or account on a draft this system created. A converted draft is deleted and rebuilt by the engine."""
    if not doc.erp_document or doc.link_method != "AUTO_DRAFT":
        return
    stored = frappe.db.get_value(doc.erp_doctype, doc.erp_document, ["docstatus"], as_dict=True)
    if not stored or stored.docstatus != 0:
        return
    key = (_data(doc.source_json) or {}).get("statement_key") or doc.source_key
    if doc.erp_doctype == "Payment Entry" and kind in (SUPPLIER_PAYMENT, CUSTOMER_RECEIPT) and target.get("party"):
        from erpnext.accounts.party import get_party_account
        pe = frappe.get_doc("Payment Entry", doc.erp_document)
        if pe.get("custom_snb_idempotency_key") != key:
            return
        account = get_party_account(target["party_type"], target["party"], pe.company)
        pe.party_type, pe.party = target["party_type"], target["party"]
        pe.party_name = frappe.db.get_value(target["party_type"], target["party"], PARTY_LABEL[target["party_type"]])
        if pe.payment_type == "Pay":
            pe.paid_to = account
        else:
            pe.paid_from = account
        pe.set("references", [])
        pe.custom_linkage_agent = "Done"
        pe.flags.ignore_permissions = True
        pe.save()
    elif doc.erp_doctype == "Journal Entry" and kind == EXPENSE_PAYMENT and target.get("account"):
        je = frappe.get_doc("Journal Entry", doc.erp_document)
        if je.get("custom_pc_statement_key") != key or not je.accounts:
            return
        je.accounts[0].account = target["account"]
        je.flags.ignore_permissions = True
        je.save()
    else:
        marker_field = "custom_snb_idempotency_key" if doc.erp_doctype == "Payment Entry" else "custom_pc_statement_key"
        if frappe.db.get_value(doc.erp_doctype, doc.erp_document, marker_field) == key:
            frappe.delete_doc(doc.erp_doctype, doc.erp_document, ignore_permissions=True, force=True)
            doc.erp_doctype = doc.erp_document = doc.link_method = ""


@frappe.whitelist(methods=["POST"])
def route_movement(name, modified, target):
    """The owner's one decision for a line.

    target: {"type": "PARTY", "party_type", "party"} | {"type": "NEW_PARTY", "party_type", "name", "vat"} |
            {"type": "EXPENSE", "account"} | {"type": "HOLDING"}
    The line's identifiers are remembered, so the same payer is recognised next time and every waiting line is re-routed.
    """
    _require("write")
    target = _data(target)
    doc = _lock(name, modified)
    if doc.kind not in DRAFTABLE:
        frappe.throw(_("This kind of movement is not routed to a party here."))
    signals = _data(doc.signals_json) or {}
    label = signals.get("display_name") or ""
    kind_type = target.get("type")
    resolved = {}
    cp = _ensure_counterparty(doc, label)
    if kind_type in ("PARTY", "NEW_PARTY"):
        party_type = target.get("party_type")
        if party_type not in PARTY_DOCTYPES or (doc.kind == CUSTOMER_RECEIPT) != (party_type == "Customer"):
            frappe.throw(_("Incoming receipts take a Customer; outgoing payments take a Supplier."))
        party = _new_party(party_type, target.get("name"), target.get("vat")) if kind_type == "NEW_PARTY" else str(target.get("party") or "")
        _check_link(party_type, party)
        if frappe.db.get_value(party_type, party, "disabled"):
            frappe.throw(_("Select an enabled party."))
        cp.set("customer" if party_type == "Customer" else "supplier", party)
        resolved = {"party_type": party_type, "party": party}
    elif kind_type == "EXPENSE":
        account = str(target.get("account") or "")
        if frappe.db.get_value("Account", account, ["root_type", "is_group"], as_dict=True) in (None,) or \
                frappe.db.get_value("Account", account, "root_type") != "Expense" or frappe.db.get_value("Account", account, "is_group"):
            frappe.throw(_("Choose an expense account that is not a group."))
        cp.expense_account = account
        resolved = {"account": account}
    elif kind_type == "HOLDING":
        resolved = {}
    else:
        frappe.throw(_("Unknown routing choice."))
    if kind_type != "HOLDING":
        cp.flags.bank_router_write = True
        cp.save(ignore_permissions=True)
        _learn_identifiers(doc, cp)
        doc.counterparty, doc.route_source = cp.name, "MANUAL"
        _retarget_draft(doc, doc.kind, resolved, cp)
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json({"counterparty": doc.counterparty}),
                         "decision_json": _json({"routed": target})})
    doc.flags.snb_router_write = True
    doc.save()
    waiting = [r.name for r in frappe.get_all(DOCTYPE, filters={"engine_state": ["in", ["NEEDS_YOU", "PENDING"]]}, fields=["name"], limit_page_length=300)]
    runtime.run("main", 0, 300, names=waiting + [doc.name])
    return {"movement": get_movement(name), "rerouted": len(waiting)}


@frappe.whitelist(methods=["POST"])
def unlink_movement(name, modified):
    """The automatic link is wrong: remember that and look again. The document is never offered for this line again."""
    _require("write")
    doc = _lock(name, modified)
    if not doc.erp_document:
        frappe.throw(_("This movement has no linked document."))
    cands = _data(doc.candidates_json) or {}
    cands.setdefault("rejected", [])
    cands["rejected"] = sorted(set(cands["rejected"]) | {doc.erp_document})
    doc.candidates_json = _json(cands)
    doc.erp_doctype = doc.erp_document = doc.link_method = ""
    doc.engine_state = "PENDING"
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json({"unlinked": cands["rejected"][-1]}), "decision_json": "{}"})
    doc.flags.snb_router_write = True
    doc.save()
    runtime.run("main", 0, 5, names=[doc.name])
    return get_movement(name)


@frappe.whitelist(methods=["POST"])
def pick_document(name, modified, doctype, document):
    """Choose one of the offered candidates for a line with several plausible documents."""
    _require("write")
    doc = _lock(name, modified)
    offered = {(c["doctype"], c["name"]) for c in (_data(doc.candidates_json) or {}).get("documents", [])}
    if (doctype, document) not in offered:
        frappe.throw(_("That document was not offered for this movement."))
    doc.erp_doctype, doc.erp_document, doc.link_method = doctype, document, "MANUAL"
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": "{}", "decision_json": _json({"linked": document})})
    doc.flags.snb_router_write = True
    doc.save()
    runtime.run("main", 0, 5, names=[doc.name])
    return get_movement(name)


@frappe.whitelist(methods=["POST"])
def save_note(name, modified, notes):
    _require("write")
    doc = _lock(name, modified)
    doc.notes = str(notes or "").strip()[:2000]
    doc.flags.snb_router_write = True
    doc.save()
    return get_movement(name)


@frappe.whitelist()
def list_counterparties(query="", start=0, limit=50):
    _require("read")
    term = str(query or "").strip()
    return frappe.get_list(COUNTERPARTY, or_filters={"display_name": ["like", f"%{term}%"]} if term else None,
                           fields=["name", "display_name", "status", "supplier", "customer", "expense_account", "is_company", "is_employee", "handler"],
                           order_by="display_name asc", start=max(0, int(start)), page_length=min(100, max(1, int(limit))))


@frappe.whitelist()
def get_supplier_payment_references(name, supplier, company):
    """Permission-filtered submitted SAR PO/PI references for one debit (unchanged from the earlier release)."""
    _require("read")
    movement = frappe.get_doc(DOCTYPE, name)
    movement.check_permission("read")
    if movement.direction != "DEBIT":
        frappe.throw(_("Payment references are available only for outgoing bank movements."))
    supplier, company = str(supplier or "").strip(), str(company or "").strip()
    if not supplier or not company:
        return {"purchase_orders": [], "purchase_invoices": []}
    _check_link("Supplier", supplier)
    _check_link("Company", company)
    common = {"supplier": supplier, "company": company, "currency": movement.currency, "docstatus": 1}
    orders = frappe.get_list("Purchase Order", filters=common, fields=["name", "transaction_date", "currency", "grand_total", "advance_paid", "status"],
                             order_by="transaction_date desc", page_length=100)
    invoices = frappe.get_list("Purchase Invoice", filters={**common, "outstanding_amount": [">", 0]},
                               fields=["name", "posting_date", "currency", "grand_total", "outstanding_amount", "status"],
                               order_by="posting_date desc", page_length=100)
    return {"purchase_orders": orders, "purchase_invoices": invoices}
