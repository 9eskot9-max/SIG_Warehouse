import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "tawal_plan", os.path.join(os.path.dirname(__file__), "..", "sig_accounting", "bank_router", "tawal_plan.py"))
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)

SETTINGS = {"legacy_before": "2026-01-01", "allow_bank_reference": True}
RECV = "1331 - مدينون - SIG"
NUM = "202601001526"


def pay(**kw):
    base = {"payment_number": "202602717192", "payment_date": "2026-07-28", "amount": 371977.61, "portal_status": "Cleared",
            "invoice_raw": "SIG-SINV-26-068R", "remit_account": "23659568000109", "reconcile": {"verdict": "RECONCILED"}}
    base.update(kw)
    return base


def credit(**kw):
    base = {"name": "C1", "event_date": "2026-07-29", "amount": 371977.61, "tail": "0109", "text": "", "erp_document": ""}
    base.update(kw)
    return base


def erp(name, outstanding, total=None, **kw):
    return {"name": name, "docstatus": 1, "customer": tp.TAWAL_CUSTOMER, "debit_to": RECV, "outstanding_amount": outstanding,
            "grand_total": total or outstanding, **kw}


INDEX = {"SIG-SINV-26-068": erp("SIG-SINV-26-068", 371977.61)}


def plan(payment, credits=None, entries=(), invoices=(), index=INDEX, settings=SETTINGS):
    return tp.plan_payment(payment, list(invoices), index, credits if credits is not None else [credit()], list(entries),
                           settings=settings, default_receivable=RECV)


def test_canonical_names():
    assert tp.canonical_invoice("SIG-SINV-26-068R") == "SIG-SINV-26-068"
    assert tp.canonical_invoice("SIG-SINV-24-029 / Revised PAC") == "SIG-SINV-24-029"
    assert tp.canonical_invoice("INV_SIG__0088-1") == "INV_SIG__0088"
    assert tp.canonical_invoice("SIG_TWL_0097 / Revised FAC") == "SIG_TWL_0097"


def test_bank_reference_is_exact_not_substring():
    assert tp.references_payment(f"CRF:{NUM} BB:Buying Goods", NUM)
    assert not tp.references_payment(f"CRF:1{NUM}9", NUM)
    assert not tp.references_payment("CRF:2026001", "2026001")


def test_reference_widens_window_and_breaks_ties():
    p = pay(payment_number=NUM, amount=306972.96, payment_date="2026-11-11", invoice_raw="Multiple")
    late = credit(name="REF", amount=306972.96, event_date="2026-12-20", text=f"CRF:{NUM}")
    assert tp.match_credit(p, [late])[0]["name"] == "REF"
    assert tp.match_credit(p, [{**late, "text": "x"}])[2] == "NO_BANK_CREDIT"
    other = credit(name="OTHER", amount=306972.96, event_date="2026-11-12")
    got, by_ref, _ = tp.match_credit(p, [other, credit(name="REF", amount=306972.96, event_date="2026-11-11", text=f"CRF:{NUM}")])
    assert got["name"] == "REF" and by_ref
    assert tp.match_credit(p, [other, {**other, "name": "O2"}])[2] == "BANK_CREDIT_AMBIGUOUS"


def test_single_invoice_in_erp_is_a_ready_allocated_draft():
    row = plan(pay())
    assert row["state"] == tp.READY and row["mode"] == "allocated" and row["credit"] == "C1"
    assert row["body"]["references"][0]["reference_name"] == "SIG-SINV-26-068"
    assert row["body"]["paid_from"] == RECV and row["body"]["paid_to_gl"] == "13121"
    assert row["body"]["reference_no"] == "202602717192"


def test_bank_gl_comes_from_the_credit_account_not_the_remit_fallback():
    row = plan(pay(remit_account="81300000023605"), credits=[credit(tail="0109")])
    assert row["body"]["paid_to_gl"] == "13121"
    row = plan(pay(remit_account="01400010326605"), credits=[credit(tail="6605")])
    assert row["body"]["paid_to_gl"] == "13123"


def test_multi_invoice_joins_the_invoice_export_and_retention_nets_into_its_invoice():
    invoices = [
        {"invoice_number": "SIG-SINV-26-077", "canonical": "SIG-SINV-26-077", "amount": 709232.60, "payment_number": "P9", "type": "Standard"},
        {"invoice_number": "SIG-SINV-26-078 / Retention", "canonical": "SIG-SINV-26-078", "amount": -10000.0, "payment_number": "P9", "type": "Standard"},
        {"invoice_number": "SIG-SINV-26-078", "canonical": "SIG-SINV-26-078", "amount": 89098.27, "payment_number": "P9", "type": "Standard"},
    ]
    index = {"SIG-SINV-26-077": erp("SIG-SINV-26-077", 709232.60), "SIG-SINV-26-078": erp("SIG-SINV-26-078", 89098.27)}
    p = pay(payment_number="P9" * 1, invoice_raw="Multiple", amount=788330.87, payment_date="2026-09-20", reconcile={"verdict": "RECONCILED"})
    row = plan(p, credits=[credit(amount=788330.87, event_date="2026-09-21")], invoices=invoices, index=index)
    assert row["state"] == tp.READY
    refs = {r["reference_name"]: r["allocated_amount"] for r in row["body"]["references"]}
    assert refs == {"SIG-SINV-26-077": 709232.60, "SIG-SINV-26-078": 79098.27}
    assert "retention" in row["body"]["remarks"]


def test_unlabelled_credit_is_a_penalty_held_for_review():
    invoices = [{"invoice_number": "SIG-SINV-25-163", "canonical": "SIG-SINV-25-163", "amount": 213591.0, "payment_number": "P8", "type": "Standard"},
                {"invoice_number": "SIG-SINV-25-163", "canonical": "SIG-SINV-25-163", "amount": -42718.2, "payment_number": "P8", "type": "Standard"}]
    index = {"SIG-SINV-25-163": erp("SIG-SINV-25-163", 213591.0)}
    p = pay(payment_number="P8", invoice_raw="Multiple", amount=170872.8)
    row = plan(p, credits=[credit(amount=170872.8)], invoices=invoices, index=index)
    assert row["state"] == tp.HOLD_REVIEW and row["reason"] == "PENALTY_CREDIT_NOTE_REVIEW" and not row["can_draft"]


def test_invoices_not_in_erp_give_an_unlinked_draft_naming_them():
    invoices = [{"invoice_number": "INV_SIG__0234 / Revised FAC", "canonical": "INV_SIG__0234", "amount": 109741.60, "payment_number": "P7", "type": "Standard"}]
    p = pay(payment_number="P7", invoice_raw="INV_SIG__0234 / Revised FAC", amount=109741.60)
    row = plan(p, credits=[credit(amount=109741.60)], invoices=invoices, index={})
    assert row["state"] == tp.UNLINKED_READY and row["mode"] == "unlinked" and row["body"]["references"] == []
    assert "invoice(s) not present in ERP: INV_SIG__0234" in row["body"]["remarks"]
    assert row["paid_from"] == RECV


def test_mixed_children_with_some_invoices_missing_still_draft_unlinked_to_avoid_a_partial_allocation():
    invoices = [{"invoice_number": "SIG-SINV-26-068", "canonical": "SIG-SINV-26-068", "amount": 1000.0, "payment_number": "P6", "type": "Standard"},
                {"invoice_number": "SIG_TWL_0097", "canonical": "SIG_TWL_0097", "amount": 2000.0, "payment_number": "P6", "type": "Standard"}]
    p = pay(payment_number="P6", invoice_raw="Multiple", amount=3000.0)
    row = plan(p, credits=[credit(amount=3000.0)], invoices=invoices)
    assert row["state"] == tp.UNLINKED_READY and "SIG_TWL_0097" in row["body"]["remarks"]


def test_invoice_already_settled_is_held():
    row = plan(pay(), index={"SIG-SINV-26-068": erp("SIG-SINV-26-068", 0.0, total=371977.61)})
    assert row["state"] == tp.HOLD_REVIEW and row["reason"] == "INVOICE_ALREADY_SETTLED"


def _entry(name, ref, **kw):
    return {"name": name, "reference_no": ref, "docstatus": 1, "unallocated_amount": 0, "paid_amount": 371977.61, "posting_date": "2026-07-29", **kw}


def test_existing_entry_wins_and_flags_unallocated_money():
    row = plan(pay(), entries=[_entry("ACC-PAY-1", "202602717192", unallocated_amount=5000)])
    assert row["state"] == tp.UNALLOCATED and row["entry"] == "ACC-PAY-1" and row["entry_match"] == "reference" and not row["can_draft"]
    row = plan(pay(), entries=[_entry("ACC-PAY-2", "202602717192", docstatus=0)])
    assert row["state"] == tp.DRAFT and row["reason"] == ""
    assert plan(pay(), entries=[_entry("ACC-PAY-3", "202602717192")])["state"] == tp.POSTED


def test_old_entry_with_a_bank_reference_is_claimed_by_amount_and_date():
    row = plan(pay(), entries=[_entry("ACC-OLD", "5566", unallocated_amount=371977.61)])
    assert row["state"] == tp.UNALLOCATED and row["entry"] == "ACC-OLD" and row["entry_match"] == "amount_date"


def test_two_equal_candidates_are_reviewed_not_guessed():
    row = plan(pay(), entries=[_entry("ACC-A", "1"), _entry("ACC-B", "2")])
    assert row["state"] == tp.POSSIBLE_EXISTING and sorted(row["possible_entries"]) == ["ACC-A", "ACC-B"] and not row["can_draft"]


def test_legacy_void_and_waiting_bank():
    assert plan(pay(payment_date="2025-12-01"))["state"] == tp.LEGACY
    assert plan(pay(portal_status="Voided"))["state"] == tp.VOID
    waiting = plan(pay(), credits=[])
    assert waiting["state"] == tp.WAITING_BANK and waiting["reason"] == "NO_BANK_CREDIT"


def test_negotiable_with_a_referencing_credit_drafts_only_when_the_setting_allows():
    p = pay(payment_number=NUM, amount=306972.96, payment_date="2026-11-11", invoice_raw="SIG-SINV-26-068", portal_status="Negotiable", reconcile=None)
    c = credit(name="REF", amount=306972.96, event_date="2026-11-11", text=f"CRF:{NUM}")
    index = {"SIG-SINV-26-068": erp("SIG-SINV-26-068", 306972.96)}
    assert plan(p, credits=[c], index=index)["state"] == tp.READY
    held = plan(p, credits=[c], index=index, settings={**SETTINGS, "allow_bank_reference": False})
    assert held["state"] == tp.BANK_RECEIVED and held["reason"] == "PORTAL_NOT_CLEARED" and held["credit"] == "REF"
    # without the reference the portal gate still applies
    assert plan(p, credits=[{**c, "text": "x"}], index=index)["state"] == tp.BANK_RECEIVED


def test_a_credit_is_never_offered_to_two_payments():
    a = pay(payment_number="AAAAAAAA1", payment_date="2026-07-28", invoice_raw="SIG-SINV-26-068")
    b = pay(payment_number="BBBBBBBB2", payment_date="2026-07-29", invoice_raw="SIG-SINV-26-068")
    rows = tp.plan_all([b, a], [], INDEX, [credit()], [], settings=SETTINGS, default_receivable=RECV)
    assert [r["state"] for r in rows] == [tp.READY, tp.WAITING_BANK] and rows[0]["payment_number"] == "AAAAAAAA1"


def test_a_credit_already_linked_to_a_document_is_not_reused():
    assert plan(pay(), credits=[credit(erp_document="ACC-PAY-9")])["state"] == tp.WAITING_BANK
