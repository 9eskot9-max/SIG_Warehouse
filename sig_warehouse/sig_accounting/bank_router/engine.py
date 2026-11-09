"""The routing engine for one movement. No Frappe imports: everything it needs comes through `ctx`.

ctx must provide:
  settings        object with scopes {fingerprint: bank GL}, company_scopes, auto_draft(date) -> bool, categories {code: account},
                  holding_supplier, holding_customer, default_expense, fee_account, vat_account, draft_fees
  registry        lookup(kind, value) -> [(counterparty, status)], facts(counterparty) -> dict
  parties         exact(party_type, name) -> party id or ""
  ledger          candidates(bank_gl, day) -> [doc candidates]; doc(doctype, name, bank_gl) -> candidate or None
  claimed         set of document names already linked to a movement
  create(kind, mv, target, fees) -> (doctype, name)   creates one draft; may raise
  holding(doctype, name) -> bool                      is this draft sitting on a holding party

`route(mv, ctx)` returns the field values to store. It never writes anything itself, so a rerun that finds
nothing new returns the same values and the caller saves nothing.
"""
from . import classify as K
from . import reconcile
from .adapters import snb
from .identify import identify

HOLDING = "HOLDING"
PERSON_CATEGORY_POSITION = 1


def mined_category(mined):
    """TX Manager's category for this line, only when its request matched uniquely."""
    return mined.get("category") if mined.get("am_category_status") == "MATCHED" else ""


def mined_route(mined):
    return str((mined.get("am_beneficiary_mapping") or {}).get("route") or "")


def category_account(route, ctx):
    """Expense account for a person payment from Am's route 'JE_PERSON|<CATEGORY>|...'."""
    parts = str(route).split("|")
    if len(parts) > PERSON_CATEGORY_POSITION and parts[0].startswith("JE_PERSON"):
        return ctx.settings.categories.get(parts[PERSON_CATEGORY_POSITION], "")
    return ""


def _label(signals, mined, facts, name=""):
    mapping = mined.get("am_beneficiary_mapping") or {}
    return facts.get("display_name") or signals.get("display_name") or mapping.get("beneficiary_name") or name or ""


def resolve_target(kind, mv, signals, facts, mined, ctx):
    """Where a draft goes. Returns a dict, or None when nothing can be drafted."""
    mapping = mined.get("am_beneficiary_mapping") or {}
    name = signals.get("display_name") or mapping.get("beneficiary_name") or ""
    label = _label(signals, mined, facts, name)
    if kind == K.SUPPLIER_PAYMENT:
        party = facts.get("supplier") or ctx.parties.exact("Supplier", name)
        if party:
            return {"party_type": "Supplier", "party": party, "holding": False, "label": label, "intended": ""}
        return {"party_type": "Supplier", "party": ctx.settings.holding_supplier, "holding": True, "label": label, "intended": name}
    if kind == K.CUSTOMER_RECEIPT:
        party = facts.get("customer") or ctx.parties.exact("Customer", name)
        if party:
            return {"party_type": "Customer", "party": party, "holding": False, "label": label, "intended": ""}
        if not ctx.settings.holding_customer:
            return None
        return {"party_type": "Customer", "party": ctx.settings.holding_customer, "holding": True, "label": label, "intended": name}
    if kind == K.EXPENSE_PAYMENT:
        account = facts.get("expense_account") or category_account(mined_route(mined), ctx) or ctx.settings.default_expense
        return {"expense_account": account, "holding": False, "label": label} if account else None
    return None


def _state_for_document(doc, mv, ctx):
    """Engine state and decision for a linked document."""
    if doc["docstatus"] == 1:
        return "POSTED", ""
    if ctx.holding(doc["doctype"], doc["name"]):
        return "NEEDS_YOU", "ROUTE_PARTY"
    return "DRAFT_READY", ""


def _document_fields(doc, method):
    return {"erp_doctype": doc["doctype"], "erp_document": doc["name"], "link_method": method}


def route(mv, ctx):
    s = ctx.settings
    source, mined = mv["source"], mv.get("recognition") or {}
    direction = "CREDIT" if float(mv["amount"]) > 0 else "DEBIT"
    bank_gl = s.scopes.get(mv["scope"])
    signals = snb.parse(source, s.company_scopes)
    intent, mroute = mined_category(mined), mined_route(mined)
    out = {"signals": {k: v for k, v in signals.items() if k != "reference"} | {"intent": intent, "mined_route": mroute},
           "erp_doctype": "", "erp_document": "", "link_method": "", "counterparty": "", "route_source": "", "decision_type": "",
           "candidates": {"documents": [], "counterparties": [], "rejected": list((mv.get("candidates") or {}).get("rejected", []))}}
    if not bank_gl:
        out.update(kind="OTHER", engine_state="DEFERRED", decision_type="")
        out["signals"]["error"] = "Statement account is not in Bank Router Settings"
        return out

    # Stage 2: identify
    if mv.get("route_source") == "MANUAL" and mv.get("counterparty"):
        ident = {"status": "IDENTIFIED", "counterparty": mv["counterparty"], "candidates": [mv["counterparty"]], "via": "MANUAL"}
    else:
        ident = identify(signals["identifiers"], ctx.registry.lookup)
    cp = ident["counterparty"]
    facts = ctx.registry.facts(cp) if cp else {}
    out["counterparty"] = cp
    out["route_source"] = "MANUAL" if ident["via"] == "MANUAL" else "IDENTIFIER" if cp else ""
    out["candidates"]["counterparties"] = ident["candidates"]

    # Stage 3: classify
    kind = K.classify(direction, source.get("parser_family"), signals, facts, intent, mroute)
    out["kind"] = kind

    # Fee and VAT lines follow their main line and are never matched on amount alone.
    if kind == K.BANK_CHARGE:
        return _route_charge(mv, out, ctx, bank_gl)

    # Stage 4: reconcile
    movement = {"key": mv["key"], "amount": float(mv["amount"]), "date": mv["date"], "reference": signals["reference"], "bank_account": bank_gl}
    existing = None
    if mv.get("erp_document"):
        existing = ctx.ledger.doc(mv["erp_doctype"], mv["erp_document"], bank_gl)
        if existing and existing["docstatus"] != 2 and existing["name"] not in out["candidates"]["rejected"]:
            ctx.claimed.add(existing["name"])
            state, decision = _state_for_document(existing, mv, ctx)
            out.update(_document_fields(existing, mv.get("link_method") or "LEDGER"), engine_state=state, decision_type=decision)
            return out
    hint = None
    linked = str((mv.get("hint") or {}).get("linked_doc") or "").strip()
    if linked:
        kind_name = "Payment Entry" if linked.startswith("ACC-PAY") else "Journal Entry"
        hint = ctx.ledger.doc(kind_name, linked, bank_gl)
    outcome, docs, method = reconcile.pick_document(movement, ctx.ledger.candidates(bank_gl, movement["date"]),
                                                    ctx.claimed, out["candidates"]["rejected"], hint)
    if outcome == "LINK":
        doc = docs[0]
        ctx.claimed.add(doc["name"])
        state, decision = _state_for_document(doc, mv, ctx)
        out.update(_document_fields(doc, method), engine_state=state, decision_type=decision)
        # Am proposed a document and the engine did not accept it (wrong amount, cancelled, or another account).
        out["signals"]["am_link_rejected"] = bool(linked) and method != "AM_LINK"
        return out
    if outcome == "PICK":
        out["candidates"]["documents"] = [{"doctype": d["doctype"], "name": d["name"], "date": str(d["date"]), "docstatus": d["docstatus"]} for d in docs]
        out.update(engine_state="NEEDS_YOU", decision_type="PICK_DOCUMENT")
        return out

    # No document exists. Decide what happens next.
    if ident["status"] == "CONFLICT":
        out.update(engine_state="NEEDS_YOU", decision_type="CONFLICT")
        return out
    if kind in K.DEFERRED_KINDS:
        out.update(engine_state="DEFERRED", decision_type="")
        return out
    if kind in K.IMPORTER_OWNED:
        if kind == K.PETTY_CASH and not facts.get("custody_account"):
            out.update(engine_state="NEEDS_YOU", decision_type="NEEDS_HR_LINK")
        else:
            out.update(engine_state="PENDING", decision_type="")
        return out
    target = resolve_target(kind, mv, signals, facts, mined, ctx)
    if not target:
        out.update(engine_state="NEEDS_YOU", decision_type="ROUTE_PARTY")
        return out
    if ident["status"] == "SUGGESTED":
        out["route_source"] = "SUGGESTED"
    elif not cp and not target["holding"]:
        out["route_source"] = "EXACT_NAME"
    elif target["holding"]:
        out["route_source"] = "HOLDING"
    if not s.auto_draft(mv["date"]):
        out.update(engine_state="NEEDS_YOU", decision_type="ROUTE_PARTY" if target["holding"] else "CREATE_DRAFT")
        return out
    out["_create"] = target
    return out


def _route_charge(mv, out, ctx, bank_gl):
    parent = mv.get("parent")
    if not parent:
        out.update(engine_state="DEFERRED", decision_type="")
        return out
    out["parent_movement"] = parent["name"]
    if parent.get("erp_document"):
        covered = ctx.ledger.covers_fee(parent["erp_doctype"], parent["erp_document"], bank_gl, parent["fee_total"])
        if covered:
            doc = {"doctype": parent["erp_doctype"], "name": parent["erp_document"], "docstatus": parent.get("docstatus", 0)}
            out.update(_document_fields(doc, "LEDGER"), engine_state="POSTED" if doc["docstatus"] == 1 else "DRAFT_READY", decision_type="")
            return out
    fee_doc = ctx.ledger.doc("Journal Entry", "", bank_gl, marker=parent["key"] + "#FEE")
    if fee_doc:
        out.update(_document_fields(fee_doc, "MARKER"), engine_state="POSTED" if fee_doc["docstatus"] == 1 else "DRAFT_READY", decision_type="")
        return out
    out.update(engine_state="PENDING", decision_type="")
    return out


def process(mv, ctx):
    """route() plus draft creation. Returns the values to store; never raises for one bad line."""
    out = route(mv, ctx)
    target = out.pop("_create", None)
    if not target:
        return out
    fees = mv.get("fees") or []
    try:
        doctype, name = ctx.create(out["kind"], mv, target, fees)
    except Exception as error:  # one failing line must not stop the batch
        out["signals"]["error"] = str(error)[:300]
        out.update(engine_state="NEEDS_YOU", decision_type="CREATE_DRAFT")
        return out
    ctx.claimed.add(name)
    out.update(erp_doctype=doctype, erp_document=name, link_method="AUTO_DRAFT", counterparty=out["counterparty"])
    out["engine_state"], out["decision_type"] = ("NEEDS_YOU", "ROUTE_PARTY") if target["holding"] else ("DRAFT_READY", "")
    if fees and doctype == "Payment Entry" and ctx.settings.draft_fees:
        try:
            ctx.create_fee_journal(mv, fees)
        except Exception as error:
            out["signals"]["fee_error"] = str(error)[:300]
    return out
