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
from sig_warehouse.sig_accounting.bank_router.adapters import snb
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
            old_source = _data(doc.source_json) or {}
            new_source = _data(source_json)
            # The first SNB bridge imported statement rows before parser_family
            # was added to the source payload. Accept only that exact additive
            # enrichment so the deployed engine can classify fee rows; any
            # changed original evidence remains a hard conflict.
            parser_upgrade = (
                isinstance(old_source, dict) and isinstance(new_source, dict)
                and "parser_family" not in old_source and "parser_family" in new_source
                and bool(new_source.get("parser_family"))
                and {k: v for k, v in new_source.items() if k != "parser_family"} == old_source
            )
            if doc.source_key != key or (old_source != new_source and not parser_upgrade):
                results.append({"id": key, "status": "SOURCE_CONFLICT", "name": name})
                continue
            changed, scope_changed = False, False
            if parser_upgrade:
                doc.source_json = source_json
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
            elif changed or scope_changed or parser_upgrade:
                status = "DERIVED_UPDATED" if changed or parser_upgrade else "ACCOUNT_SCOPE_UPDATED"
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
def run_engine(phase="main", start=0, limit=120, review_only=0, bank=""):
    """Route one batch of movements. The sync calls 'main' until it reports no more, then 'fees'."""
    _integration_only()
    if phase not in ("main", "fees"):
        frappe.throw(_("Unknown phase."))
    if bank not in ("", "SNB"):
        frappe.throw(_("Unknown bank."))
    return runtime.run(phase, max(0, int(start)), min(300, max(1, int(limit))), review_only=str(review_only) == "1", bank=bank)


@frappe.whitelist()
def list_links(start=0, limit=200):
    """Verified document links and explicitly rejected Am hints for Sheet Am write-back."""
    _integration_only()
    start, limit = max(0, int(start)), min(500, max(1, int(limit)))
    all_rows = frappe.get_all(DOCTYPE,
                              fields=["name", "source_key", "erp_doctype", "erp_document", "link_method", "signals_json", "candidates_json"],
                              order_by="name asc", limit_page_length=0)
    eligible = []
    for r in all_rows:
        signals = _data(r.signals_json) or {}
        candidates = _data(r.candidates_json) or {}
        rejected = sorted({str(x) for x in candidates.get("rejected", []) if str(x)})
        if r.erp_document or rejected or signals.get("am_link_rejected"):
            eligible.append((r, signals, rejected))
    page = eligible[start:start + limit]
    doc_names = {}
    for r, _, _ in page:
        if r.erp_document and r.erp_doctype in ("Payment Entry", "Journal Entry"):
            doc_names.setdefault(r.erp_doctype, set()).add(r.erp_document)
    doc_statuses = {}
    for doctype, names in doc_names.items():
        for d in frappe.get_all(doctype, filters={"name": ["in", list(names)]}, fields=["name", "docstatus"], limit_page_length=0):
            doc_statuses[(doctype, d.name)] = d.docstatus
    return {"rows": [{"source_key": r.source_key, "erp_doctype": r.erp_doctype or "", "erp_document": r.erp_document or "", "link_method": r.link_method or "",
                      "doc_status": doc_statuses.get((r.erp_doctype, r.erp_document)),
                      "am_link_rejected": bool(signals.get("am_link_rejected")), "rejected_documents": rejected}
                     for r, signals, rejected in page],
            "has_more": start + len(page) < len(eligible), "next_start": start + len(page)}


@frappe.whitelist()
def engine_status():
    _require("read")
    settings = runtime.Settings()
    visible = frappe.get_list(DOCTYPE, fields=["engine_state"], limit_page_length=0)
    counts = {}
    for row in visible:
        counts[row.engine_state] = counts.get(row.engine_state, 0) + 1
    return {"review_only_sync_version": 1, "auto_draft": settings._enabled, "auto_draft_from": str(settings._from or ""), "banks_configured": len(settings.scopes),
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
        for d in frappe.get_list(doctype, filters={"name": ["in", list(names)]}, fields=["name", "docstatus"], limit_page_length=0):
            out[(doctype, d.name)] = d.docstatus
    return out


def _request_supplier(doc, recognition):
    """Offer a unique, readable ERP supplier from a uniquely matched bank request."""
    if doc.direction != "DEBIT" or recognition.get("am_category_status") not in ("MATCHED", "NO_CATEGORY"):
        return ""
    request = recognition.get("transfer_request") or {}
    match = re.fullmatch(r"Supplier:\s*(.+?)\s*", str(request.get("erp_party") or ""), flags=re.I)
    if not match or not frappe.has_permission("Supplier", "read"):
        return ""
    value = match.group(1).strip()
    if not value:
        return ""
    rows = frappe.get_list("Supplier", filters={"disabled": 0},
        or_filters={"name": ["=", value], "supplier_name": ["=", value]},
        fields=["name"], page_length=2)
    return rows[0]["name"] if len(rows) == 1 else ""


def _payload(doc, fees=None, statuses=None):
    source = _data(doc.source_json) or {}
    recognition = _data(doc.recognition_json) or {}
    signals = _data(doc.signals_json) or {}
    statuses = statuses or {}
    mapping = recognition.get("am_beneficiary_mapping") or {}
    cp = frappe.db.get_value(COUNTERPARTY, doc.counterparty, ["display_name", "customer", "supplier"], as_dict=True) if doc.counterparty else None
    party_type = "Customer" if doc.direction == "CREDIT" else "Supplier"
    party = (cp or {}).get(party_type.lower()) or ""
    if party and not frappe.has_permission(party_type, "read", party):
        party = ""
    request_supplier = _request_supplier(doc, recognition)
    candidate_parties = [request_supplier] if request_supplier else []
    for candidate in (_data(doc.candidates_json) or {}).get("counterparties", []):
        candidate_party = frappe.db.get_value(COUNTERPARTY, candidate, party_type.lower())
        if candidate_party and frappe.has_permission(party_type, "read", candidate_party):
            candidate_parties.append(candidate_party)
    return {
        "name": doc.name, "modified": str(doc.modified), "event_date": str(doc.event_date), "amount": flt(doc.amount), "currency": doc.currency,
        "company": runtime.documents.COMPANY, "account_tail": doc.source_account_tail, "bank": str(source.get("bank") or "SNB"), "direction": doc.direction,
        "engine_state": doc.engine_state, "decision_type": doc.decision_type or "", "kind": doc.kind or "",
        "accounting_treatment": doc.accounting_treatment or "", "accounting_account": doc.accounting_account or "",
        "counterparty": doc.counterparty or "", "counterparty_name": (cp or {}).get("display_name") or "",
        "linked_party_type": party_type if party else "", "linked_party": party, "suggested_parties": sorted(set(candidate_parties)),
        "request_supplier": request_supplier, "request_supplier_conflict": bool(party and request_supplier and party != request_supplier),
        "payment_reference_doctype": doc.get("payment_reference_doctype") or "",
        "payment_reference": doc.get("payment_reference") or "",
        "display_name": (signals.get("display_name") or mapping.get("beneficiary_name") or "")[:140],
        "route_source": doc.route_source or "", "erp_doctype": doc.erp_doctype or "", "erp_document": doc.erp_document or "",
        "doc_status": statuses.get((doc.erp_doctype, doc.erp_document)), "link_method": doc.link_method or "",
        "category": recognition.get("category") if recognition.get("am_category_status") == "MATCHED" else "",
        "transfer_request": recognition.get("transfer_request") or {},
        "signals": signals, "candidates": _data(doc.candidates_json) or {}, "reference": source.get("reference", ""),
        "narrative": "\n".join(str(source.get(k) or "") for k in ("transaction_description", "detail_description", "extra_description", "remarks") if source.get(k)),
        "fees": fees or [], "notes": doc.notes or "", "parent_movement": doc.parent_movement or "",
    }


def _fees_for(names):
    if not names:
        return {}
    out = {}
    for r in frappe.get_list(DOCTYPE, filters={"parent_movement": ["in", names]},
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
    if bank not in ("ALL", "SNB", "ALINMA"):
        frappe.throw(_("Unknown bank."))
    filters = {"engine_state": ["in", TABS[tab]]}
    if bank != "ALL":
        filters["source_key"] = ["like", bank + "-%"]
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
    visible_states = frappe.get_list(DOCTYPE, fields=["engine_state"], limit_page_length=0)
    counts = {tab_name: sum(1 for row in visible_states if row.engine_state in states)
              for tab_name, states in TABS.items()}
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


def _new_party(doctype, name, vat="", country=""):
    """Create a Customer or Supplier only when no enabled party already carries that exact name."""
    name = str(name or "").strip()
    if len(name) < 3 or len(name) > 140:
        frappe.throw(_("Enter the party's full name."))
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You need read access to check existing {0} records before creating one.").format(doctype), frappe.PermissionError)
    field = PARTY_LABEL[doctype]
    same = [r for r in frappe.get_list(doctype, filters={"disabled": 0}, fields=["name", field], limit_page_length=0)
            if normalize_text(r.get(field)) == normalize_text(name)]
    if same:
        frappe.throw(_("{0} already exists: {1}. Select it instead.").format(doctype, ", ".join(r.name for r in same)))
    if not frappe.has_permission(doctype, "create"):
        # Live permissions: Accounts User can create Customers but not Suppliers. Say so plainly, not as a raw Frappe error.
        frappe.throw(_("You cannot create a new {0}. Ask an Accounts Manager, or choose an existing one.").format(doctype), frappe.PermissionError)
    values = {"doctype": doctype, field: name, **NEW_PARTY_DEFAULTS[doctype]}
    if doctype == "Customer":
        country = str(country or "").strip()
        if not country or not frappe.db.exists("Country", country):
            frappe.throw(_("Select a valid country for the new Customer."))
        _check_link("Country", country)
        values["custom_country"] = country
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
    """Attach identifiers without silently moving an existing party's hint."""
    signals = _data(doc.signals_json) or {}
    source = _data(doc.get("source_json")) or {}
    if source and str(source.get("bank") or "SNB").upper() == "SNB":
        # Reparse the immutable evidence so older review rows learn newly
        # supported formats when the user confirms a party.
        parsed = snb.parse(source, runtime.Settings().company_scopes)
        signals.update(parsed)
        doc.signals_json = _json(signals)
    for kind, value in signals.get("identifiers") or []:
        fmt = signals.get("format") or ""
        if kind == "NAME" and fmt in ("IPS_LOCAL", "LARGE_LOCAL", "INTERNAL_SNB"):
            kind = "NAME_" + fmt
        key = runtime.identity_key(kind, value)
        existing = frappe.db.exists(IDENTIFIER, key)
        if existing:
            ident = frappe.get_doc(IDENTIFIER, key)
            if ident.counterparty != cp.name:
                frappe.throw(_("This bank hint is already linked to another counterparty; review the conflict before changing it."))
            if ident.status != "ACTIVE":
                ident.status, ident.source = "ACTIVE", "ROUTER"
                ident.flags.bank_router_write = True
                ident.save(ignore_permissions=True)
            continue
        ident = frappe.get_doc({"doctype": IDENTIFIER, "identity_key": key, "counterparty": cp.name, "kind": kind, "value": str(value)[:140],
                                "normalized": hint_key(kind, value), "status": "ACTIVE", "source": "ROUTER", "first_seen": frappe.utils.nowdate()})
        ident.flags.bank_router_write = True
        ident.insert(ignore_permissions=True)


def _retarget_draft(doc, kind, target, cp, treatment=None):
    """Retarget or safely replace only this router's own unsubmitted draft."""
    if not doc.erp_document or doc.link_method != "AUTO_DRAFT":
        return None
    stored = frappe.db.get_value(doc.erp_doctype, doc.erp_document, ["docstatus"], as_dict=True)
    if not stored or stored.docstatus != 0:
        return None
    key = (_data(doc.source_json) or {}).get("statement_key") or doc.source_key
    desired_doctype = {"PAYMENT_ENTRY": "Payment Entry", "JOURNAL_ENTRY": "Journal Entry"}.get(treatment or doc.get("accounting_treatment"))
    if desired_doctype and desired_doctype != doc.erp_doctype:
        marker_field = "custom_snb_idempotency_key" if doc.erp_doctype == "Payment Entry" else "custom_pc_statement_key"
        old = frappe.get_doc(doc.erp_doctype, doc.erp_document)
        if old.get(marker_field) != key:
            frappe.throw(_("This linked draft does not carry this movement's router marker; it has been kept."))
        if doc.erp_doctype == "Payment Entry" and old.get("references"):
            frappe.throw(_("This Payment Entry has invoice or order allocations. Review them before changing its document type."))
        old.check_permission("write")
        old.check_permission("delete")
        if not frappe.has_permission(desired_doctype, "create"):
            frappe.throw(_("You cannot create the selected {0} draft.").format(desired_doctype), frappe.PermissionError)
        old_name = doc.erp_document
        frappe.delete_doc(doc.erp_doctype, old_name)
        old_doctype = doc.erp_doctype
        doc.erp_doctype, doc.erp_document, doc.link_method = "", "", ""
        return {"doctype": old_doctype, "name": old_name}
    if doc.erp_doctype == "Payment Entry" and kind in (SUPPLIER_PAYMENT, CUSTOMER_RECEIPT) and target.get("party"):
        from erpnext.accounts.party import get_party_account
        pe = frappe.get_doc("Payment Entry", doc.erp_document)
        if pe.get("custom_snb_idempotency_key") != key:
            return
        if pe.get("party") != target["party"] and pe.get("references"):
            frappe.throw(_("This draft has invoice or order allocations. Review them before changing its party."))
        account = get_party_account(target["party_type"], target["party"], pe.company)
        pe.party_type, pe.party = target["party_type"], target["party"]
        pe.party_name = frappe.db.get_value(target["party_type"], target["party"], PARTY_LABEL[target["party_type"]])
        if pe.payment_type == "Pay":
            pe.paid_to = account
        else:
            pe.paid_from = account
        pe.custom_linkage_agent = "Done"
        # Saving the review line does not grant write access to the linked accounting document.
        pe.check_permission("write")
        pe.save()
    elif doc.erp_doctype == "Journal Entry" and kind == EXPENSE_PAYMENT and target.get("account"):
        je = frappe.get_doc("Journal Entry", doc.erp_document)
        if je.get("custom_pc_statement_key") != key or not je.accounts:
            return
        je.accounts[0].account = target["account"]
        je.check_permission("write")
        je.save()
    return None


@frappe.whitelist(methods=["POST"])
def route_movement(name, modified, target):
    """The owner's one decision for a line.

    target: {"type": "PARTY", "party_type", "party"} | {"type": "NEW_PARTY", "party_type", "name", "vat"} |
            {"type": "EXPENSE", "account"} | {"type": "HOLDING"}
    The line's identifiers are remembered for later engine runs; this user action re-processes only the line they reviewed.
    """
    _require("write")
    target = _data(target)
    doc = _lock(name, modified)
    signals = _data(doc.signals_json) or {}
    label = signals.get("display_name") or ""
    kind_type = target.get("type")
    treatment = str(target.get("treatment") or doc.accounting_treatment or "").upper()
    if treatment not in ("PAYMENT_ENTRY", "JOURNAL_ENTRY", "FINANCE_HANDLES"):
        frappe.throw(_("Choose Payment Entry, Journal Entry, or Finance handles this."))
    if doc.kind not in ("UNKNOWN", "SUPPLIER_PAYMENT", "EXPENSE_PAYMENT", "CUSTOMER_RECEIPT", "EMPLOYEE"):
        frappe.throw(_("This movement is held for its specialist, petty-cash, own-transfer, or fee workflow."))
    previous = {"counterparty": doc.counterparty or "", "accounting_treatment": doc.accounting_treatment or "",
                "accounting_account": doc.get("accounting_account") or ""}
    if doc.get("erp_document") and (target.get("sales_invoice") or target.get("reference_name") or doc.get("payment_reference")):
        frappe.throw(_("This movement has an existing draft. Review invoice allocations on that Payment Entry before changing its route."))
    resolved = {}
    if treatment == "FINANCE_HANDLES":
        _retarget_draft(doc, doc.kind, {}, None, treatment)
        doc.accounting_treatment = treatment
        doc.accounting_account = ""
        doc.payment_reference_doctype = doc.payment_reference = ""
        doc.payment_reference_amount = 0
        doc.flags.snb_router_write = True
        doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json(previous),
                             "decision_json": _json({"accounting_treatment": treatment})})
        doc.save()
        runtime.run("main", 0, 1, names=[doc.name])
        return {"movement": get_movement(name), "rerouted": 0}
    cp = _ensure_counterparty(doc, label)
    if treatment == "PAYMENT_ENTRY" and kind_type in ("PARTY", "NEW_PARTY"):
        party_type = target.get("party_type")
        expected_party = "Customer" if doc.direction == "CREDIT" else "Supplier"
        if party_type != expected_party:
            frappe.throw(_("Incoming receipts take a Customer; outgoing payments take a Supplier."))
        party = _new_party(party_type, target.get("name"), target.get("vat"), target.get("country")) if kind_type == "NEW_PARTY" else str(target.get("party") or "")
        _check_link(party_type, party)
        if frappe.db.get_value(party_type, party, "disabled"):
            frappe.throw(_("Select an enabled party."))
        reference_name = str(target.get("reference_name") or target.get("sales_invoice") or "").strip()
        reference_type = str(target.get("reference_doctype") or ("Sales Invoice" if target.get("sales_invoice") else "")).strip()
        if reference_name:
            allowed = ("Sales Invoice",) if party_type == "Customer" else ("Purchase Invoice", "Purchase Order")
            if reference_type not in allowed:
                frappe.throw(_("Choose a supported reference for this party."))
            reference = frappe.get_doc(reference_type, reference_name)
            reference.check_permission("read")
            expected_party = reference.customer if party_type == "Customer" else reference.supplier
            if (reference.docstatus != 1 or reference.company != runtime.documents.COMPANY or reference.currency != "SAR"
                    or expected_party != party):
                frappe.throw(_("Choose a submitted SAR reference for this party and company."))
            available = (flt(reference.grand_total) - flt(reference.get("advance_paid"))) if reference_type == "Purchase Order" else flt(reference.outstanding_amount)
            if available <= 0:
                frappe.throw(_("The selected reference has no outstanding amount."))
            doc.payment_reference_doctype, doc.payment_reference = reference_type, reference_name
            doc.payment_reference_amount = min(abs(flt(doc.amount)), available)
        else:
            doc.payment_reference_doctype = doc.payment_reference = ""
            doc.payment_reference_amount = 0
        cp.set("customer" if party_type == "Customer" else "supplier", party)
        if not cp.get("display_name") or cp.get("display_name") == "Unnamed counterparty":
            cp.display_name = frappe.db.get_value(party_type, party, PARTY_LABEL[party_type]) or party
        doc.accounting_account = ""
        resolved = {"party_type": party_type, "party": party}
    elif treatment == "JOURNAL_ENTRY" and kind_type == "EXPENSE" and doc.direction == "DEBIT":
        account = str(target.get("account") or "")
        _check_link("Account", account)
        details = frappe.db.get_value("Account", account, ["root_type", "is_group", "disabled", "company"], as_dict=True)
        if (not details or details.get("root_type") != "Expense" or details.get("is_group")
                or details.get("disabled") or details.get("company") != runtime.documents.COMPANY):
            frappe.throw(_("Choose an enabled expense account for this company that is not a group."))
        doc.accounting_account = account
        doc.payment_reference_doctype = doc.payment_reference = ""
        doc.payment_reference_amount = 0
        resolved = {"account": account}
    else:
        frappe.throw(_("Choose a party for Payment Entry or an expense account for Journal Entry."))
    remember = str(target.get("remember_default") or "0") == "1"
    if remember:
        cp.default_treatment = treatment
        if treatment == "JOURNAL_ENTRY":
            cp.expense_account = doc.accounting_account
    cp.flags.bank_router_write = True
    cp.save(ignore_permissions=True)
    _learn_identifiers(doc, cp)
    doc.accounting_treatment = treatment
    doc.counterparty, doc.route_source = cp.name, "MANUAL"
    replaced = _retarget_draft(doc, doc.kind, resolved, cp, treatment)
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json(previous),
                         "decision_json": _json({"routed": target})})
    doc.flags.snb_router_write = True
    doc.save()
    result = runtime.run("main", 0, 1, names=[doc.name], manual_draft=bool(replaced))
    if replaced and (result.get("errors") or not get_movement(name).get("erp_document")):
        frappe.throw(_("The replacement draft could not be created. The original draft was restored; review the movement and try again."))
    return {"movement": get_movement(name), "rerouted": 0}


@frappe.whitelist(methods=["POST"])
def create_reviewed_draft(name, modified):
    """Create one draft after the reviewer has explicitly chosen its treatment."""
    _require("write")
    doc = _lock(name, modified)
    if doc.erp_document or doc.decision_type != "CREATE_DRAFT":
        frappe.throw(_("Refresh this movement and resolve its existing document or pending review first."))
    doctype = {"PAYMENT_ENTRY": "Payment Entry", "JOURNAL_ENTRY": "Journal Entry"}.get(doc.accounting_treatment)
    if not doctype or not frappe.has_permission(doctype, "create"):
        frappe.throw(_("An explicit treatment and permission to create the selected document are required."), frappe.PermissionError)
    result = runtime.run("main", 0, 1, names=[name], manual_draft=True)
    if result.get("errors"):
        frappe.throw(_("The draft could not be created. Review the movement and its error details."))
    movement = get_movement(name)
    if not movement.get("erp_document"):
        frappe.throw(_("No draft was created. Review any matching documents and the selected party or account."))
    return movement


@frappe.whitelist(methods=["POST"])
def clear_missing_document(name, modified):
    """Clear only a document proven absent, preserving its identity in the audit."""
    _require("write")
    doc = _lock(name, modified)
    doctype, document = doc.erp_doctype, doc.erp_document
    if doctype not in ("Payment Entry", "Journal Entry") or not document:
        frappe.throw(_("This movement has no supported linked document."))
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You need permission to read the linked document type."), frappe.PermissionError)
    if frappe.db.exists(doctype, document):
        frappe.throw(_("The linked document still exists. Review it before unlinking."))
    candidates = _data(doc.candidates_json) or {}
    candidates["rejected"] = sorted(set(candidates.get("rejected") or []) | {document})
    hint = _data(doc.erp_hint_json) or {}
    if hint.get("linked_doc") == document:
        hint["linked_doc"] = ""
        hint["readback_status"] = "NOT_LINKED"
    doc.candidates_json, doc.erp_hint_json = _json(candidates), _json(hint)
    doc.erp_doctype = doc.erp_document = doc.link_method = ""
    doc.engine_state, doc.decision_type = "PENDING", ""
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(),
                         "previous_json": _json({"missing_document": document, "doctype": doctype}),
                         "decision_json": _json({"cleared_missing_document": True})})
    doc.flags.snb_router_write = True
    doc.save()
    return get_movement(name)


@frappe.whitelist(methods=["POST"])
def bulk_clear_missing_documents(items):
    """Clear an explicit page of absent documents; any unsafe row aborts the request."""
    _require("write")
    rows = _data(items)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        frappe.throw(_("Choose between 1 and 100 movements."))
    names = [str(r.get("name") or "") for r in rows if isinstance(r, dict)]
    if len(names) != len(rows) or any(not n for n in names) or len(set(names)) != len(names):
        frappe.throw(_("Each selected movement must be unique."))
    for item in rows:
        if not item.get("modified"):
            frappe.throw(_("Refresh the movements before clearing links."))
        clear_missing_document(item["name"], item["modified"])
    return {"cleared": len(rows)}


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
    claimed = frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE erp_doctype=%s AND erp_document=%s AND name!=%s FOR UPDATE",
                            (doctype, document, name))
    if claimed:
        frappe.throw(_("This document is already linked to another movement. Refresh and review the match."))
    doc.erp_doctype, doc.erp_document, doc.link_method = doctype, document, "MANUAL"
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": "{}", "decision_json": _json({"linked": document})})
    doc.flags.snb_router_write = True
    doc.save()
    runtime.run("main", 0, 5, names=[doc.name])
    return get_movement(name)


@frappe.whitelist(methods=["POST"])
def bulk_confirm_unique_matches(items):
    """Link only rows already showing exactly one eligible ledger candidate; never create a document."""
    _require("write")
    items = _data(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        frappe.throw(_("Select between 1 and 100 movements."))
    results = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            results.append({"name": "", "status": "INVALID"})
            continue
        doc = frappe.get_doc(DOCTYPE, item["name"])
        doc.check_permission("write")
        candidates = (_data(doc.candidates_json) or {}).get("documents", [])
        if doc.engine_state != "NEEDS_YOU" or doc.decision_type != "PICK_DOCUMENT" or len(candidates) != 1:
            results.append({"name": doc.name, "status": "HELD", "reason": "not a unique offered document"})
            continue
        c = candidates[0]
        try:
            pick_document(doc.name, str(doc.modified), c["doctype"], c["name"])
            results.append({"name": doc.name, "status": "LINKED", "document": c["name"]})
        except Exception as error:
            results.append({"name": doc.name, "status": "FAILED", "reason": str(error)[:220]})
    return {"results": results, "linked": sum(r["status"] == "LINKED" for r in results),
            "held": sum(r["status"] == "HELD" for r in results)}


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
                           fields=["name", "display_name", "status", "supplier", "customer", "expense_account", "default_treatment", "is_company", "is_employee", "handler"],
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
