"""Frappe side of the routing engine: settings, registry, ledger, draft creation and the batch runner.

Everything decision-related lives in engine.py; this module only loads data and writes results.
"""
import collections
import datetime as dt
import hashlib
import json
import re

import frappe
from frappe.utils import cint, flt, getdate, now_datetime

from . import documents, engine
from .classify import EXPENSE_PAYMENT
from .text import DEFAULT_COMPANY_SCOPES, hint_key, normalize_text

DOCTYPE = "SNB Movement Review"
SETTINGS = "Bank Router Settings"
IDENTIFIER = "Bank Counterparty Identifier"
COUNTERPARTY = "Bank Counterparty"
FEE_FILTERS = ('%"parser_family":"BANK_FEE"%', '%"parser_family":"FEE_VAT"%')
ROUTING_FIELDS = ("engine_state", "decision_type", "kind", "counterparty", "route_source", "erp_doctype", "erp_document",
                  "link_method", "parent_movement")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def identity_key(kind, value):
    return hashlib.sha256(f"{kind}|{hint_key(kind, value)}".encode("utf-8")).hexdigest()


class Settings:
    def __init__(self):
        doc = frappe.get_cached_doc(SETTINGS)
        self.doc = doc
        self.scopes = {row.account_scope_hash: row.gl_account for row in doc.bank_accounts or [] if row.account_scope_hash}
        self.company_scopes = frozenset(set(self.scopes) | set(DEFAULT_COMPANY_SCOPES))
        self.categories = {str(row.code).upper(): row.expense_account for row in doc.categories or [] if row.expense_account}
        self.holding_supplier = doc.holding_supplier or ""
        self.holding_customer = doc.holding_customer or ""
        self.default_expense = doc.default_expense_account or ""
        self.fee_account = doc.fee_account or ""
        self.vat_account = doc.vat_account or ""
        self.draft_fees = bool(cint(doc.draft_fees))
        self.own_names = {normalize_text(n) for n in str(doc.own_names or "").splitlines() if normalize_text(n)}
        self._enabled = bool(cint(doc.auto_draft_enabled))
        self._from = getdate(doc.auto_draft_from) if doc.auto_draft_from else None

    def auto_draft(self, day):
        return bool(self._enabled and self._from and getdate(day) >= self._from)


class Registry:
    def __init__(self):
        self.ids = {r.name: (r.counterparty, r.status) for r in frappe.get_all(
            IDENTIFIER, fields=["name", "counterparty", "status"], filters={"status": ["!=", "REVOKED"]}, limit_page_length=0)}
        self.cps = {r.name: r for r in frappe.get_all(
            COUNTERPARTY, fields=["name", "display_name", "status", "is_company", "handler", "is_employee", "custody_account", "employee",
                                  "customer", "supplier", "expense_account", "category"], limit_page_length=0)}

    def lookup(self, kind, value):
        hit = self.ids.get(identity_key(kind, value))
        if hit and (self.cps.get(hit[0]) or {}).get("status") == "ACTIVE":
            return [hit]
        return []

    def facts(self, counterparty):
        cp = self.cps.get(counterparty)
        return dict(cp) if cp else {}


class Parties:
    def __init__(self):
        self.index = {}
        for party_type, field in (("Customer", "customer_name"), ("Supplier", "supplier_name")):
            names = collections.defaultdict(set)
            for row in frappe.get_all(party_type, fields=["name", field], filters={"disabled": 0}, limit_page_length=0):
                names[normalize_text(row.get(field))].add(row.name)
            self.index[party_type] = names

    def exact(self, party_type, name):
        found = self.index.get(party_type, {}).get(normalize_text(name), set())
        return next(iter(found)) if len(found) == 1 and normalize_text(name) else ""


class Ledger:
    """Documents that touch our bank accounts around the dates being routed, loaded once per run."""

    def __init__(self, settings, start, end):
        self.settings = settings
        gls = tuple(sorted(set(settings.scopes.values()))) or ("",)
        window = {"s": start - dt.timedelta(days=7), "e": end + dt.timedelta(days=7), "gl": gls}
        self.rows, self.by_name, self.by_marker, self.pe_party = [], collections.defaultdict(list), {}, {}
        for r in frappe.db.sql("""select name, posting_date, docstatus, paid_from, paid_to, paid_amount, received_amount, reference_no,
                custom_snb_idempotency_key marker, party from `tabPayment Entry`
                where docstatus < 2 and posting_date between %(s)s and %(e)s and (paid_from in %(gl)s or paid_to in %(gl)s)""", window, as_dict=True):
            self.pe_party[r.name] = r.party
            out = r.paid_from in gls
            self._add({"doctype": "Payment Entry", "name": r.name, "date": r.posting_date, "docstatus": r.docstatus,
                       "amount": -flt(r.paid_amount) if out else flt(r.received_amount), "reference": r.reference_no or "",
                       "marker": r.marker or "", "bank_account": r.paid_from if out else r.paid_to})
        for r in frappe.db.sql("""select je.name, je.posting_date, je.docstatus, je.custom_pc_statement_key marker, jea.account,
                jea.debit_in_account_currency d, jea.credit_in_account_currency c
                from `tabJournal Entry Account` jea join `tabJournal Entry` je on je.name = jea.parent
                where je.docstatus < 2 and je.posting_date between %(s)s and %(e)s and jea.account in %(gl)s""", window, as_dict=True):
            self._add({"doctype": "Journal Entry", "name": r.name, "date": r.posting_date, "docstatus": r.docstatus,
                       "amount": flt(r.d) - flt(r.c), "reference": "", "marker": r.marker or "", "bank_account": r.account})

    def _add(self, candidate):
        self.rows.append(candidate)
        self.by_name[candidate["name"]].append(candidate)
        if candidate["marker"]:
            self.by_marker[candidate["marker"]] = candidate

    def register(self, doctype, name, day, amount, bank_account, marker, party=""):
        self._add({"doctype": doctype, "name": name, "date": day, "docstatus": 0, "amount": amount, "reference": "",
                   "marker": marker, "bank_account": bank_account})
        if party:
            self.pe_party[name] = party

    def candidates(self, bank_gl, day):
        return [r for r in self.rows if r["bank_account"] == bank_gl]

    def doc(self, doctype, name, bank_gl, marker=None):
        if marker:
            return self.by_marker.get(marker)
        for r in self.by_name.get(name, []):
            if r["bank_account"] == bank_gl:
                return r
        if not name:
            return None
        return self._fetch(doctype, name, bank_gl)

    def _fetch(self, doctype, name, bank_gl):
        """A document outside the loaded window (for example an Am link to an older draft), measured on our bank account."""
        if doctype == "Payment Entry":
            r = frappe.db.get_value("Payment Entry", name, ["posting_date", "docstatus", "paid_from", "paid_to", "paid_amount", "received_amount",
                                                           "reference_no", "custom_snb_idempotency_key", "party"], as_dict=True)
            if not r:
                return None
            out = r.paid_from == bank_gl
            if not out and r.paid_to != bank_gl:
                return None
            self.pe_party[name] = r.party
            doc = {"doctype": doctype, "name": name, "date": r.posting_date, "docstatus": r.docstatus,
                   "amount": -flt(r.paid_amount) if out else flt(r.received_amount), "reference": r.reference_no or "",
                   "marker": r.custom_snb_idempotency_key or "", "bank_account": bank_gl}
        else:
            head = frappe.db.get_value("Journal Entry", name, ["posting_date", "docstatus", "custom_pc_statement_key"], as_dict=True)
            if not head:
                return None
            net = frappe.db.sql("""select sum(debit_in_account_currency - credit_in_account_currency) from `tabJournal Entry Account`
                where parent=%s and account=%s""", (name, bank_gl))
            if not net or net[0][0] is None:
                return None
            doc = {"doctype": doctype, "name": name, "date": head.posting_date, "docstatus": head.docstatus, "amount": flt(net[0][0]),
                   "reference": "", "marker": head.custom_pc_statement_key or "", "bank_account": bank_gl}
        self._add(doc)
        return doc

    def covers_fee(self, doctype, name, bank_gl, fee_total):
        return any(r["bank_account"] == bank_gl and abs(r["amount"] + fee_total) <= 0.005 for r in self.by_name.get(name, []))


class Context:
    def __init__(self, start, end):
        self.settings = Settings()
        self.registry = Registry()
        self.parties = Parties()
        self.ledger = Ledger(self.settings, start, end)
        self.claimed = {r.erp_document for r in frappe.get_all(DOCTYPE, fields=["erp_document"], filters={"erp_document": ["!=", ""]}, limit_page_length=0)}

    def holding(self, doctype, name):
        if doctype != "Payment Entry":
            return False
        return self.ledger.pe_party.get(name) in {self.settings.holding_supplier, self.settings.holding_customer} - {""}

    # ---- drafts ----------------------------------------------------------------------------------------------
    def _existing(self, doctype, field, key):
        found = frappe.db.get_value(doctype, {field: key, "docstatus": ["<", 2]}, "name")
        return found

    def create(self, kind, mv, target, fees):
        s = self.settings
        movement = {"key": mv["key"], "amount": mv["amount"], "date": mv["date"], "reference": mv["source"].get("reference", "")}
        bank_gl = s.scopes[mv["scope"]]
        use_fees = fees if s.draft_fees else []
        if kind == EXPENSE_PAYMENT:
            existing = self._existing("Journal Entry", "custom_pc_statement_key", mv["key"])
            if existing:
                return "Journal Entry", existing
            body = documents.expense_journal(movement, target["expense_account"], bank_gl, use_fees, s.fee_account, s.vat_account, target["label"], kind)
            doc = frappe.get_doc(body)
            doc.insert()
            self.ledger.register("Journal Entry", doc.name, mv["date"], -abs(flt(mv["amount"])), bank_gl, mv["key"])
            return "Journal Entry", doc.name
        existing = self._existing("Payment Entry", "custom_snb_idempotency_key", mv["key"])
        if existing:
            return "Payment Entry", existing
        from erpnext.accounts.party import get_party_account
        party_account = get_party_account(target["party_type"], target["party"], documents.COMPANY)
        body = documents.payment_entry(movement, target["party_type"], target["party"], party_account, bank_gl, target["label"], kind,
                                       target["holding"], target.get("intended", ""))
        doc = frappe.get_doc(body)
        doc.insert()
        self.ledger.register("Payment Entry", doc.name, mv["date"], flt(mv["amount"]), bank_gl, mv["key"], target["party"])
        return "Payment Entry", doc.name

    def create_fee_journal(self, mv, fees):
        s = self.settings
        if not (s.fee_account and fees):
            return None
        marker = mv["key"] + documents.FEE_MARKER_SUFFIX
        if self._existing("Journal Entry", "custom_pc_statement_key", marker):
            return None
        movement = {"key": mv["key"], "amount": mv["amount"], "date": mv["date"], "reference": mv["source"].get("reference", "")}
        bank_gl = s.scopes[mv["scope"]]
        doc = frappe.get_doc(documents.fee_journal(movement, fees, bank_gl, s.fee_account, s.vat_account))
        doc.insert()
        total = sum(abs(flt(f["amount"])) for f in fees)
        self.ledger.register("Journal Entry", doc.name, mv["date"], -total, bank_gl, marker)
        return doc.name


# ---- movement <-> engine dict --------------------------------------------------------------------------------
def load_index():
    """Light view of every movement: name -> dict, plus fee children by main movement."""
    rows = frappe.get_all(DOCTYPE, fields=["name", "source_key", "event_date", "amount", "account_scope_hash", "source_json", "recognition_json",
                                           "erp_hint_json", "engine_state", "kind", "counterparty", "route_source", "erp_doctype",
                                           "erp_document", "link_method", "candidates_json", "parent_movement", "modified"], limit_page_length=0)
    index = {}
    for r in rows:
        source = json.loads(r.source_json or "{}")
        recognition = json.loads(r.recognition_json or "{}")
        index[r.name] = {"row": r, "source": source, "recognition": recognition, "family": source.get("parser_family", "")}
    children = collections.defaultdict(list)
    for name, entry in index.items():
        main_id = entry["recognition"].get("related_main_id")
        if main_id and entry["family"] in ("BANK_FEE", "FEE_VAT"):
            parent = hashlib.sha256(main_id.encode("utf-8")).hexdigest()
            if parent in index:
                entry["parent_name"] = parent
                children[parent].append({"name": name, "amount": flt(entry["row"].amount), "family": entry["family"]})
    return index, children


def to_engine(name, index, children, ctx):
    entry = index[name]
    r = entry["row"]
    source = entry["source"]
    mv = {"name": name, "key": source.get("statement_key") or r.source_key, "amount": flt(r.amount), "date": getdate(r.event_date),
          "scope": r.account_scope_hash or "", "source": source, "recognition": entry["recognition"],
          "hint": json.loads(r.erp_hint_json or "{}"), "route_source": r.route_source or "", "counterparty": r.counterparty or "",
          "erp_doctype": r.erp_doctype or "", "erp_document": r.erp_document or "", "link_method": r.link_method or "",
          "candidates": json.loads(r.candidates_json or "{}"), "fees": children.get(name, [])}
    parent_name = entry.get("parent_name")
    if parent_name:
        p = index[parent_name]["row"]
        mv["parent"] = {"name": parent_name, "key": index[parent_name]["source"].get("statement_key") or p.source_key,
                        "erp_doctype": p.erp_doctype or "", "erp_document": p.erp_document or "",
                        "docstatus": (ctx.ledger.doc(p.erp_doctype, p.erp_document, ctx.settings.scopes.get(p.account_scope_hash), None) or {}).get("docstatus", 0)
                        if p.erp_document else 0, "fee_total": sum(abs(c["amount"]) for c in children.get(parent_name, []))}
    return mv


def apply(name, out, user=None):
    """Store engine output when it differs from what is saved. Returns True when the movement was changed."""
    doc = frappe.get_doc(DOCTYPE, name)
    values = {f: out.get(f, "") or "" for f in ROUTING_FIELDS}
    values["parent_movement"] = out.get("parent_movement", "") or ""
    values["signals_json"] = _json(out.get("signals") or {})
    values["candidates_json"] = _json(out.get("candidates") or {})
    changed = [f for f, v in values.items() if str(doc.get(f) or "") != str(v)]
    if not changed:
        return False
    previous = {f: doc.get(f) for f in ROUTING_FIELDS}
    for f, v in values.items():
        doc.set(f, v)
    doc.processed_at = now_datetime()
    if any(f in changed for f in ("engine_state", "erp_document", "counterparty", "kind")):
        doc.append("audit", {"reviewer": user or frappe.session.user, "reviewed_at": now_datetime(),
                             "previous_json": _json(previous), "decision_json": _json({f: values[f] for f in ROUTING_FIELDS})})
    doc.flags.snb_router_write = True
    doc.save()
    return True


def run(phase="main", start=0, limit=120, names=None):
    """Route a batch. Phase 'main' handles every line except bank charges; 'fees' handles those after their main lines."""
    like = "or".join([" source_json like %s "] * 2)
    rows = frappe.db.sql(f"""select name, event_date from `tab{DOCTYPE}` where {'(' if phase == 'fees' else 'not ('}{like}) order by event_date, name""", FEE_FILTERS, as_dict=True)
    if names:
        rows = [r for r in rows if r.name in set(names)]
    total = len(rows)
    batch = rows[start:start + limit]
    result = {"phase": phase, "processed": 0, "changed": 0, "errors": 0, "total": total, "has_more": start + limit < total,
              "next_start": start + limit, "states": collections.Counter()}
    if not rows:
        return result
    days = [getdate(r.event_date) for r in rows]
    ctx = Context(min(days), max(days))
    index, children = load_index()
    for r in batch:
        try:
            mv = to_engine(r.name, index, children, ctx)
            out = engine.process(mv, ctx)
            if apply(r.name, out):
                result["changed"] += 1
                entry = index[r.name]["row"]
                for f in ("erp_doctype", "erp_document"):
                    entry[f] = out.get(f, "")
            result["states"][out["engine_state"]] += 1
        except Exception:
            result["errors"] += 1
            frappe.log_error(title="Bank router could not route a movement", message=f"{r.name}\n{frappe.get_traceback()}")
        result["processed"] += 1
    result["states"] = dict(result["states"])
    return result
