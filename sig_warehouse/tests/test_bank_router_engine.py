"""The engine on one movement at a time, with a fake context. No Frappe is imported."""
import datetime as dt
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "sig_accounting"))

from bank_router import engine as E  # noqa: E402
from bank_router.text import account_scope, hint_key  # noqa: E402

SCOPE = account_scope("23659568000109")
BANK = "13121"


class Registry:
    def __init__(self, identifiers=None, counterparties=None):
        self.identifiers, self.counterparties = identifiers or {}, counterparties or {}

    def lookup(self, kind, value):
        hit = self.identifiers.get((kind, hint_key(kind, value)))
        return [hit] if hit else []

    def facts(self, cp):
        return self.counterparties.get(cp, {})


class Ledger:
    def __init__(self, docs=None):
        self.docs = docs or []

    def candidates(self, bank_gl, day):
        return [d for d in self.docs if d["bank_account"] == bank_gl]

    def doc(self, doctype, name, bank_gl, marker=None):
        for d in self.docs:
            if (marker and d.get("marker") == marker) or (name and d["name"] == name):
                return d
        return None

    def covers_fee(self, doctype, name, bank_gl, fee_total):
        return any(d["name"] == name and d.get("fee_line") == fee_total for d in self.docs)


class Parties:
    def __init__(self, names=None):
        self.names = names or {}

    def exact(self, party_type, name):
        return self.names.get((party_type, hint_key("NAME", name)), "")


class Ctx:
    def __init__(self, auto=False, registry=None, ledger=None, parties=None, holding_customer="Unidentified Receipts", fail=False):
        self.settings = types.SimpleNamespace(
            scopes={SCOPE: BANK}, company_scopes=frozenset({SCOPE, account_scope("01400010326605")}),
            auto_draft=lambda day: auto, categories={"PROJECT_OPERATING_COST": "5130 - Subcontract"},
            holding_supplier="Collective", holding_customer=holding_customer, default_expense="5126 - Misc",
            fee_account="538", vat_account="", draft_fees=False, billers={})
        self.registry, self.ledger, self.parties = registry or Registry(), ledger or Ledger(), parties or Parties()
        self.claimed, self.created, self.fail = set(), [], fail

    def holding(self, doctype, name):
        return any(d["name"] == name and d.get("holding") for d in self.ledger.docs)

    def create(self, kind, mv, target, fees):
        if self.fail:
            raise RuntimeError("ERP refused the draft")
        name = f"DRAFT-{len(self.created) + 1}"
        self.created.append((kind, target))
        return ("Journal Entry" if "account" in str(target) and "expense_account" in target else "Payment Entry"), name


def movement(amount, narrative, family="IPS_LOCAL", key="K1", day="2026-10-05", **extra):
    source = {"parser_family": family, "transaction_description": "Local transfer", "detail_description": narrative, "reference": "R1"}
    mv = {"name": "m-" + key, "key": key, "amount": amount, "date": dt.date.fromisoformat(day), "scope": SCOPE, "source": source,
          "recognition": {}, "hint": {}, "fees": []}
    mv.update(extra)
    return mv


def doc(name, amount, day, **more):
    d = {"doctype": "Journal Entry", "name": name, "date": day, "docstatus": 1, "amount": amount, "reference": "", "marker": "", "bank_account": BANK}
    d.update(more)
    return d


IPS_OUT = "SAUDI ARABIA SAINMA ACME TRADING ESTABLISHMENT 1234567890123"
IPS_IN = "CITY:Jeddah *****SAUDI ARABIA SAINMA شركة رسوخ المتقدمة للمقاولات 1234567890123456 دفعة"


def test_existing_posted_journal_is_linked_not_drafted():
    ctx = Ctx(auto=True, ledger=Ledger([doc("JV-1", -1000, "2026-10-05")]))
    out = E.process(movement(-1000, IPS_OUT), ctx)
    assert (out["engine_state"], out["decision_type"], out["erp_document"]) == ("NEEDS_YOU", "PICK_DOCUMENT", "")
    assert not ctx.created


def test_draft_found_in_ledger_is_draft_ready_and_marker_wins():
    docs = [doc("JV-1", -1000, "2026-10-05", docstatus=0), doc("JV-2", -1000, "2026-10-05", docstatus=0, marker="K1")]
    out = E.process(movement(-1000, IPS_OUT), Ctx(ledger=Ledger(docs)))
    assert (out["engine_state"], out["erp_document"], out["link_method"]) == ("DRAFT_READY", "JV-2", "MARKER")


def test_several_candidates_ask_for_a_decision():
    docs = [doc("JV-1", -1000, "2026-10-04"), doc("JV-2", -1000, "2026-10-06")]
    out = E.process(movement(-1000, IPS_OUT), Ctx(ledger=Ledger(docs)))
    assert (out["engine_state"], out["decision_type"]) == ("NEEDS_YOU", "PICK_DOCUMENT")
    assert [d["name"] for d in out["candidates"]["documents"]] == ["JV-1", "JV-2"]


def test_two_movements_never_claim_the_same_document():
    ctx = Ctx(ledger=Ledger([doc("JV-1", -1000, "2026-10-05", marker="K1")]))
    first = E.process(movement(-1000, IPS_OUT, key="K1"), ctx)
    second = E.process(movement(-1000, IPS_OUT, key="K2"), ctx)
    assert first["erp_document"] == "JV-1" and second["erp_document"] == ""


def test_drafting_off_leaves_a_decision_and_creates_nothing():
    ctx = Ctx(auto=False)
    out = E.process(movement(-1000, IPS_OUT), ctx)
    assert (out["engine_state"], out["decision_type"], out["kind"]) == ("NEEDS_YOU", "CHOOSE_TREATMENT", "UNKNOWN")
    assert not ctx.created


def test_unknown_payee_stays_unknown_and_never_drafts_to_collective():
    ctx = Ctx(auto=True)
    out = E.process(movement(-1000, IPS_OUT), ctx)
    assert (out["kind"], out["engine_state"], out["decision_type"]) == ("UNKNOWN", "NEEDS_YOU", "CHOOSE_TREATMENT")
    assert not ctx.created


def test_name_only_match_requires_confirmation_even_when_auto_enabled():
    registry = Registry({("NAME", hint_key("NAME", "ACME TRADING ESTABLISHMENT")): ("CP-A", "ACTIVE")},
                        {"CP-A": {"supplier": "SUP-ACME", "default_treatment": "PAYMENT_ENTRY"}})
    ctx = Ctx(auto=True, registry=registry)
    out = E.process(movement(-1000, IPS_OUT, accounting_treatment="PAYMENT_ENTRY"), ctx)
    assert (out["engine_state"], out["decision_type"], out["counterparty"]) == ("NEEDS_YOU", "ROUTE_PARTY", "")
    assert out["candidates"]["counterparties"] == ["CP-A"] and not ctx.created


def test_exact_unique_name_matches_an_erp_party_without_a_rule():
    ctx = Ctx(auto=True, parties=Parties({("Supplier", hint_key("NAME", "ACME TRADING ESTABLISHMENT")): "SUP-X"}))
    out = E.process(movement(-1000, IPS_OUT, accounting_treatment="PAYMENT_ENTRY"), ctx)
    assert (out["route_source"], ctx.created[0][1]["party"]) == ("EXACT_NAME", "SUP-X")


def test_per_movement_treatment_selects_pe_or_je_without_category_forcing_it():
    registry = Registry({}, {"CP-M": {"supplier": "SUP-M"}})
    pe_mv = movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-M", accounting_treatment="PAYMENT_ENTRY")
    pe = E.process(pe_mv, Ctx(auto=True, registry=registry))
    assert pe["kind"] == "SUPPLIER_PAYMENT" and pe["erp_doctype"] == "Payment Entry"

    je_mv = movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-M", accounting_treatment="JOURNAL_ENTRY",
                     accounting_account="5130 - Subcontract")
    je = E.process(je_mv, Ctx(auto=True, registry=registry))
    assert je["kind"] == "EXPENSE_PAYMENT" and je["erp_doctype"] == "Journal Entry"
    assert je["accounting_treatment"] == "JOURNAL_ENTRY" and not Ctx().created


def test_xxsc_purpose_needs_a_per_line_treatment_and_uses_its_configured_je_account():
    ctx = Ctx(auto=True)
    ctx.settings.categories["XXSC"] = "5130 - Subcontract"
    undecided = movement(-1000, IPS_OUT)
    undecided["recognition"] = {"category": "XXSC", "am_category_status": "MATCHED"}
    out = E.process(undecided, ctx)
    assert out["kind"] == "UNKNOWN" and out["decision_type"] == "CHOOSE_TREATMENT" and not ctx.created
    assert out["signals"]["suggested_account"] == "5130 - Subcontract"

    journal = movement(-1000, IPS_OUT, accounting_treatment="JOURNAL_ENTRY")
    journal["recognition"] = {"category": "XXSC", "am_category_status": "MATCHED"}
    ctx_journal = Ctx(auto=True)
    ctx_journal.settings.categories["XXSC"] = "5130 - Subcontract"
    drafted = E.process(journal, ctx_journal)
    assert drafted["erp_doctype"] == "Journal Entry"
    assert ctx_journal.created[0][1]["expense_account"] == "5130 - Subcontract"


def test_remembered_treatment_is_a_default_but_line_override_wins():
    registry = Registry({}, {"CP-M": {"supplier": "SUP-M", "default_treatment": "PAYMENT_ENTRY"}})
    mv = movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-M", accounting_treatment="JOURNAL_ENTRY",
                  accounting_account="5130 - Subcontract")
    out = E.process(mv, Ctx(auto=True, registry=registry))
    assert out["accounting_treatment"] == "JOURNAL_ENTRY" and out["erp_doctype"] == "Journal Entry"


def test_payee_default_is_a_suggestion_until_the_movement_is_reviewed():
    registry = Registry({}, {"CP-M": {"supplier": "SUP-M", "default_treatment": "PAYMENT_ENTRY"}})
    ctx = Ctx(auto=True, registry=registry)
    mv = movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-M")
    out = E.process(mv, ctx)
    assert out["decision_type"] == "CONFIRM_TREATMENT"
    assert out["signals"]["suggested_treatment"] == "PAYMENT_ENTRY" and not ctx.created


def test_finance_handled_line_is_not_drafted():
    mv = movement(-1000, IPS_OUT, accounting_treatment="FINANCE_HANDLES")
    ctx = Ctx(auto=True)
    out = E.process(mv, ctx)
    assert out["engine_state"] == "PENDING" and not ctx.created


def test_sadad_biller_mapping_suggests_expense_je_and_never_guesses_a_supplier():
    ctx = Ctx(auto=True)
    ctx.settings.billers = {"101": "5420 - Electricity Expense"}
    mv = movement(-750, "SADAD BILLER CODE: 101", family="SADAD")
    out = E.process(mv, ctx)
    assert out["kind"] == "EXPENSE_PAYMENT" and out["accounting_treatment"] == "JOURNAL_ENTRY"
    assert out["erp_doctype"] == "Journal Entry"
    assert ctx.created[0][1]["expense_account"] == "5420 - Electricity Expense"


def test_unknown_payer_is_not_drafted_to_a_holding_customer():
    ctx = Ctx(auto=True)
    out = E.process(movement(2500, IPS_IN, family="IPS_LOCAL", key="K9"), ctx)
    assert out["kind"] == "CUSTOMER_RECEIPT" and out["decision_type"] == "CHOOSE_TREATMENT"
    assert out["engine_state"] == "NEEDS_YOU" and not ctx.created


def test_receipt_cannot_be_drafted_without_a_holding_customer():
    out = E.process(movement(2500, IPS_IN, key="K9"), Ctx(auto=True, holding_customer=""))
    assert (out["engine_state"], out["decision_type"]) == ("NEEDS_YOU", "CHOOSE_TREATMENT")


def test_person_payment_is_an_expense_journal_from_the_category():
    mv = movement(-3000, "OTBANK:SABBPERSON NAME", family="LOCAL_OTBANK")
    mv["recognition"] = {"am_beneficiary_mapping": {"route": "JE_PERSON|PROJECT_OPERATING_COST|CONFIRMED|NO_PI", "beneficiary_name": "PERSON NAME"}}
    mv["accounting_treatment"] = "JOURNAL_ENTRY"
    ctx = Ctx(auto=True)
    out = E.process(mv, ctx)
    assert out["kind"] == "EXPENSE_PAYMENT" and ctx.created[0][1]["expense_account"] == "5130 - Subcontract"
    assert out["engine_state"] == "DRAFT_READY"


def test_petty_cash_requires_explicit_employee_confirmation():
    mv = movement(-2000, "1234567890123 BEN ID:555123", family="INTERNAL_BEN_ID")
    mv["recognition"] = {"category": "XXPC", "am_category_status": "MATCHED"}
    assert E.process(mv, Ctx(auto=True))["decision_type"] == "NEEDS_HR_LINK"
    registry = Registry({("BEN_ID", "555123"): ("CP-E", "ACTIVE")}, {"CP-E": {"is_employee": True, "custody_account": "132223 - Adnan"}})
    out = E.process(mv, Ctx(auto=True, registry=registry))
    assert (out["kind"], out["engine_state"], out["decision_type"]) == ("PETTY_CASH", "NEEDS_YOU", "NEEDS_HR_LINK")


def test_own_transfers_tawal_and_other_lines_are_deferred_not_drafted():
    ctx = Ctx(auto=True)
    own = E.process(movement(-5000, "01400010326605 BEN ID:2323429130", family="INTERNAL_BEN_ID", key="A"), ctx)
    tawal = E.process(movement(5000, "TELECOMMUNICATIONS TOWERS COMPANY", family="INCOMING_LOCAL", key="B"), ctx)
    sadad = E.process(movement(-700, "SADAD", family="SADAD", key="C"), ctx)
    assert [o["engine_state"] for o in (own, tawal)] == ["DEFERRED"] * 2
    assert [o["kind"] for o in (own, tawal, sadad)] == ["OWN_TRANSFER", "SPECIALIST", "UNKNOWN"]
    assert sadad["decision_type"] == "CHOOSE_TREATMENT"
    assert not ctx.created


def test_personal_account_transfer_cannot_be_reclassified_by_payee_default():
    registry = Registry({}, {"CP-OWN": {"is_company": True, "default_treatment": "PAYMENT_ENTRY", "supplier": "SUP-OWN"}})
    mv = movement(-5000, "01400010326605 BEN ID:2323429130", family="INTERNAL_BEN_ID", key="OWN",
                  route_source="MANUAL", counterparty="CP-OWN", accounting_treatment="PAYMENT_ENTRY")
    out = E.process(mv, Ctx(auto=True, registry=registry))
    assert out["kind"] == "OWN_TRANSFER" and out["engine_state"] == "DEFERRED"
    assert out["accounting_treatment"] == "" and not Ctx().created


def test_conflicting_identifiers_are_never_resolved_by_the_engine():
    registry = Registry({("BEN_ID", "555123"): ("CP-A", "ACTIVE"), ("ACCOUNT", hint_key("ACCOUNT", "38759875000102")): ("CP-B", "ACTIVE")},
                        {"CP-A": {}, "CP-B": {}})
    out = E.process(movement(-900, "38759875000102 BEN ID:555123", family="INTERNAL_BEN_ID"), Ctx(auto=True, registry=registry))
    assert (out["engine_state"], out["decision_type"]) == ("NEEDS_YOU", "CONFLICT")


def test_a_manual_choice_is_kept_over_identifiers():
    registry = Registry({}, {"CP-M": {"supplier": "SUP-M"}})
    mv = movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-M", accounting_treatment="PAYMENT_ENTRY")
    ctx = Ctx(auto=True, registry=registry)
    out = E.process(mv, ctx)
    assert (out["route_source"], ctx.created[0][1]["party"]) == ("MANUAL", "SUP-M")


def test_a_failing_draft_is_reported_on_the_line_and_stops_nothing():
    registry = Registry({}, {"CP-A": {"supplier": "SUP-A"}})
    out = E.process(movement(-1000, IPS_OUT, route_source="MANUAL", counterparty="CP-A", accounting_treatment="PAYMENT_ENTRY"),
                    Ctx(auto=True, registry=registry, fail=True))
    assert (out["engine_state"], out["decision_type"]) == ("NEEDS_YOU", "CREATE_DRAFT")
    assert "ERP refused" in out["signals"]["error"]


def test_an_existing_link_is_kept_and_a_cancelled_one_is_dropped():
    ledger = Ledger([doc("JV-1", -1000, "2026-10-05", docstatus=0)])
    mv = movement(-1000, IPS_OUT, erp_doctype="Journal Entry", erp_document="JV-1", link_method="MANUAL")
    out = E.process(mv, Ctx(ledger=ledger))
    assert (out["erp_document"], out["link_method"]) == ("JV-1", "MANUAL")
    cancelled = Ledger([doc("JV-1", -1000, "2026-10-05", docstatus=2)])
    gone = E.process(mv, Ctx(ledger=cancelled))
    assert gone["erp_document"] == ""


def test_a_wrong_match_is_never_offered_again():
    mv = movement(-1000, IPS_OUT, candidates={"rejected": ["JV-1"]})
    out = E.process(mv, Ctx(ledger=Ledger([doc("JV-1", -1000, "2026-10-05")])))
    assert out["erp_document"] == "" and out["candidates"]["rejected"] == ["JV-1"]


def test_unknown_statement_account_is_reported_not_guessed():
    mv = movement(-1000, IPS_OUT)
    mv["scope"] = "0" * 64
    out = E.process(mv, Ctx(auto=True))
    assert out["engine_state"] == "DEFERRED" and "not in Bank Router Settings" in out["signals"]["error"]


def test_fee_line_follows_its_main_line_document():
    ledger = Ledger([doc("JV-1", -1000, "2026-10-05", fee_line=1.15)])
    fee = movement(-1.15, "fee", family="BANK_FEE", key="F1")
    fee["parent"] = {"name": "m-K1", "key": "K1", "erp_doctype": "Journal Entry", "erp_document": "JV-1", "docstatus": 1, "fee_total": 1.15}
    out = E.process(fee, Ctx(ledger=ledger))
    assert (out["kind"], out["engine_state"], out["erp_document"], out["parent_movement"]) == ("BANK_CHARGE", "POSTED", "JV-1", "m-K1")
    orphan = E.process(movement(-1.15, "fee", family="FEE_VAT", key="F2"), Ctx())
    assert orphan["engine_state"] == "DEFERRED"


def test_rerun_returns_identical_values():
    ctx = Ctx(ledger=Ledger([doc("JV-1", -1000, "2026-10-05")]))
    first = E.process(movement(-1000, IPS_OUT), ctx)
    again = E.process(movement(-1000, IPS_OUT, erp_doctype=first["erp_doctype"], erp_document=first["erp_document"], link_method=first["link_method"]), Ctx(ledger=ctx.ledger))
    assert {k: first[k] for k in ("engine_state", "erp_document", "kind")} == {k: again[k] for k in ("engine_state", "erp_document", "kind")}


def test_a_wrong_am_link_is_flagged_so_the_sync_can_correct_it():
    ledger = Ledger([doc("JV-OLD", -3193242.19, "2026-08-03"), doc("JV-NEW", -790, "2026-08-03")])
    mv = movement(-790, IPS_OUT, key="K7", day="2026-08-03", erp_doctype="", erp_document="", hint={"linked_doc": "JV-OLD"})
    out = E.process(mv, Ctx(ledger=ledger))
    assert out["erp_document"] == "" and out["decision_type"] == "PICK_DOCUMENT"
    assert [d["name"] for d in out["candidates"]["documents"]] == ["JV-NEW"]


def test_an_accepted_am_link_is_not_flagged():
    ledger = Ledger([doc("JV-1", -1000, "2026-10-05")])
    out = E.process(movement(-1000, IPS_OUT, key="K8", hint={"linked_doc": "JV-1"}), Ctx(ledger=ledger))
    assert out["link_method"] == "AM_LINK" and out["signals"]["am_link_rejected"] is False


def test_petty_cash_manual_confirmation_requires_review_before_draft():
    registry = Registry({}, {"CP-E": {"employee": "EMP-1", "custody_account": "1322 - Custody", "display_name": "Employee"}})
    mv = movement(-2000, "1234567890123 BEN ID:555123", family="INTERNAL_BEN_ID", route_source="MANUAL", counterparty="CP-E")
    mv["recognition"] = {"category": "XXPC", "am_category_status": "MATCHED"}
    review = E.process(mv, Ctx(auto=False, registry=registry))
    assert (review["kind"], review["decision_type"], review["accounting_treatment"]) == ("PETTY_CASH", "CREATE_DRAFT", "JOURNAL_ENTRY")
    ctx = Ctx(auto=True, registry=registry)
    drafted = E.process(mv, ctx)
    assert drafted["engine_state"] == "DRAFT_READY"
    assert ctx.created[0][1]["employee"] == "EMP-1"


def test_reviewed_personal_bank_custody_has_no_employee_assignment():
    registry = Registry({}, {"CP-OWNER": {"employee": "", "custody_account": "1322 - Rajhi", "display_name": "Owner bank"}})
    mv = movement(-20000, "1234567890123 BEN ID:555123", family="INTERNAL_BEN_ID", route_source="MANUAL", counterparty="CP-OWNER", accounting_account="1322 - Rajhi")
    mv["recognition"] = {"category": "XXPC", "am_category_status": "MATCHED"}
    review = E.process(mv, Ctx(auto=False, registry=registry))
    assert review["decision_type"] == "CREATE_DRAFT" and review["accounting_account"] == "1322 - Rajhi"
    ctx = Ctx(auto=True, registry=registry)
    E.process(mv, ctx)
    assert ctx.created[0][1]["employee"] == "" and ctx.created[0][1]["custody_account"] == "1322 - Rajhi"


def test_a_confirmed_employee_payee_is_not_asked_again_on_the_next_line():
    registry = Registry({("BEN_ID", "555123"): ("CP-E", "ACTIVE")},
                        {"CP-E": {"employee": "EMP-1", "custody_account": "1322 - Custody", "display_name": "Employee"}})
    mv = movement(-1500, "1234567890123 BEN ID:555123", family="INTERNAL_BEN_ID")
    mv["recognition"] = {"category": "XXPC", "am_category_status": "MATCHED"}
    out = E.process(mv, Ctx(auto=False, registry=registry))
    assert (out["kind"], out["decision_type"], out["accounting_treatment"]) == ("PETTY_CASH", "CREATE_DRAFT", "JOURNAL_ENTRY")
    unconfirmed = Registry({("BEN_ID", "555123"): ("CP-E", "ACTIVE")}, {"CP-E": {"is_employee": True, "custody_account": "1322 - Custody"}})
    assert E.process(mv, Ctx(auto=False, registry=unconfirmed))["decision_type"] == "NEEDS_HR_LINK"


def test_a_remembered_sadad_bill_is_recognised_and_offers_its_payee_default():
    registry = Registry({("SADAD_CODE", hint_key("SADAD_CODE", "090-2286958091")): ("CP-B", "ACTIVE")},
                        {"CP-B": {"display_name": "Imran iqama", "default_treatment": "JOURNAL_ENTRY", "expense_account": "5155 - Iqama"}})
    mv = movement(-412, "SADAD Payment 090-2286958091 23659568000109 7163894807", family="SADAD")
    mv["source"]["detail_description"] = "090-2286958091 23659568000109 7163894807"
    out = E.process(mv, Ctx(auto=False, registry=registry))
    assert out["counterparty"] == "CP-B"
    assert out["signals"]["suggested_treatment"] == "JOURNAL_ENTRY" and out["signals"]["suggested_account"] == "5155 - Iqama"
    assert out["decision_type"] == "CHOOSE_TREATMENT" and out["engine_state"] == "NEEDS_YOU"


def _bilal_line(day="2026-09-16"):
    mv = movement(-1500, "11100071178405 BEN ID:2472775614 xxpc", family="INTERNAL_BEN_ID", day=day)
    mv["recognition"] = {"category": "XXPC", "am_category_status": "MATCHED",
                         "am_beneficiary_mapping": {"source": "Sheet Am matched beneficiary", "erp_party": "Employee: Bilal | 132210"}}
    mv.update(route_source="MANUAL", counterparty="CP-B")
    return mv


def _bilal_context(docs):
    return Ctx(ledger=Ledger(docs), registry=Registry(counterparties={"CP-B": {"custody_account": "132210 - Bilal"}}))


def test_a_document_of_another_payee_is_never_offered():
    docs = [doc("JV-13", -1500, "2026-09-13", counter={"132210"}), doc("JV-20", -1500, "2026-09-20", counter={"132228"})]
    out = E.process(_bilal_line(), _bilal_context(docs))
    assert out["decision_type"] == "PICK_DOCUMENT"
    assert [d["name"] for d in out["candidates"]["documents"]] == ["JV-13"]        # Imran's custody entry is gone


def test_the_same_day_document_of_this_payee_is_linked_without_asking():
    docs = [doc("JV-13", -1500, "2026-09-13", counter={"132210"}), doc("JV-16", -1500, "2026-09-16", counter={"132210"}),
            doc("JV-20", -1500, "2026-09-20", counter={"132228"})]
    line = _bilal_line()
    line["unique_statement_amount"] = True
    out = E.process(line, _bilal_context(docs))
    assert (out["erp_document"], out["link_method"], out["engine_state"]) == ("JV-16", "LEDGER", "POSTED")
    line["unique_statement_amount"] = False
    assert E.process(line, _bilal_context(docs))["decision_type"] == "PICK_DOCUMENT"
    # the 13 September line finds its own entry, not the neighbour
    earlier = _bilal_line("2026-09-13")
    earlier["unique_statement_amount"] = True
    assert E.process(earlier, _bilal_context(docs))["erp_document"] == "JV-13"


def test_without_payee_evidence_the_old_pick_behaviour_stays():
    mv = movement(-1500, "11100071178405 BEN ID:2472775614", family="INTERNAL_BEN_ID", day="2026-09-16")
    docs = [doc("JV-16", -1500, "2026-09-16", counter={"132210"}), doc("JV-17", -1500, "2026-09-17", counter={"132228"})]
    out = E.process(mv, Ctx(ledger=Ledger(docs)))
    assert out["decision_type"] == "PICK_DOCUMENT" and len(out["candidates"]["documents"]) == 2


def test_a_statement_name_finance_confirmed_identifies_the_payee_next_time():
    from bank_router.identify import identify
    confirmed = lambda kind, value: [("CP-OBED", "CONFIRMED")] if kind == "NAME_IPS_LOCAL" else []
    out = identify([("NAME", "OBED ULLAH"), ("NAME_IPS_LOCAL", "OBED ULLAH")], confirmed)
    assert (out["status"], out["counterparty"]) == ("IDENTIFIED", "CP-OBED")
    seeded = lambda kind, value: [("CP-OBED", "ACTIVE")] if kind == "NAME" else []
    assert identify([("NAME", "OBED ULLAH")], seeded)["status"] == "SUGGESTED"          # an Am name alone still only suggests
    two = lambda kind, value: [("CP-A", "CONFIRMED"), ("CP-B", "CONFIRMED")] if kind == "NAME_IPS_LOCAL" else []
    assert identify([("NAME_IPS_LOCAL", "SAME NAME")], lambda k, v: two(k, v))["status"] == "CONFLICT"


def test_a_salary_advance_is_not_suggested_as_an_expense():
    mv = movement(-500, "SAUDI ARABIA ABDULLAH ALQAHTANI", family="IPS_LOCAL")
    mv["recognition"] = {"category": "XXHR", "am_category_status": "MATCHED"}
    mv["accounting_treatment"] = "JOURNAL_ENTRY"          # as on the live Qahtani line
    ctx = Ctx(auto=False)
    ctx.settings.purpose_accounts = {"XXHR": "1321 - Employee advances"}
    out = E.process(mv, ctx)
    assert out["signals"].get("suggested_account") == "1321 - Employee advances"
    ctx.settings.purpose_accounts = {}
    assert E.process(mv, ctx)["signals"].get("suggested_account", "") != ctx.settings.default_expense


def test_an_untreated_salary_advance_still_gets_the_advance_account_suggested():
    mv = movement(-500, "SAUDI ARABIA ABDULLAH ALQAHTANI", family="IPS_LOCAL")
    mv["recognition"] = {"category": "XXHR", "am_category_status": "MATCHED"}
    ctx = Ctx(auto=False)
    ctx.settings.purpose_accounts = {"XXHR": "1321 - Employee advances"}
    out = E.process(mv, ctx)
    assert out["kind"] == "EMPLOYEE" and out["signals"].get("suggested_account") == "1321 - Employee advances"


def test_untagged_employee_debit_asks_for_purpose_in_the_review_queue():
    registry = Registry({}, {"CP-E": {"is_employee": True, "employee": "EMP-1", "custody_account": "1322 - Custody"}})
    mv = movement(-150, IPS_OUT, route_source="MANUAL", counterparty="CP-E")
    ctx = Ctx(auto=True, registry=registry)
    out = E.process(mv, ctx)
    assert (out["kind"], out["engine_state"], out["decision_type"]) == ("EMPLOYEE", "NEEDS_YOU", "CHOOSE_PURPOSE")
    assert not ctx.created


def test_finance_petty_cash_is_distinct_from_unmatched_tx_tag():
    from sig_warehouse.sig_accounting.bank_router.engine import mined_category

    assert mined_category({"category": "XXPC", "am_category_status": "UNMATCHED"}) == ""
    assert mined_category({"finance_petty_cash": True}) == "XXPC"
    assert mined_category({"finance_petty_cash": "true"}) == ""
    assert mined_category({"category": "XXPC", "am_category_status": "MATCHED", "finance_petty_cash": False}) == ""
    assert mined_category({"category": "XXSC", "am_category_status": "MATCHED", "finance_petty_cash": False}) == "XXSC"
