"""Pure routing stages on realistic SNB narratives. No Frappe is imported."""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "sig_accounting"))

from bank_router import classify as C  # noqa: E402
from bank_router import documents as D  # noqa: E402
from bank_router import reconcile as R  # noqa: E402
from bank_router import seed  # noqa: E402
from bank_router.adapters import snb  # noqa: E402
from bank_router.identify import identify  # noqa: E402
from bank_router.text import account_scope, hint_key, is_company_number, normalize_text  # noqa: E402

OURS = "01400010326605"
OTHER_ACCOUNT = "38759875000102"
OTHER_IBAN = "SA1234567890123456789012"
OUR_IBAN = "SA0380000001400010326605"


def line(direction="CREDIT", family="", desc="", detail="", reference="R1"):
    return {"direction": direction, "parser_family": family, "transaction_description": desc,
            "detail_description": detail, "reference": reference}


# ---- text ---------------------------------------------------------------------------------------------------
def test_normalisation_is_arabic_and_zero_safe():
    assert normalize_text("  أَكْمَة   Co.  ") == "اكمه co"
    assert normalize_text("شركة") == normalize_text("شركه")
    assert hint_key("ACCOUNT", "0038759875000102") == hint_key("ACCOUNT", "38759875000102")
    assert hint_key("NAME", "  Khutut   Buildings ") == "khutut buildings"


def test_own_account_detection_uses_fingerprints_not_numbers():
    assert is_company_number(OURS)
    assert is_company_number("1400010326605"), "a number the sheet stripped of its leading zero"
    assert is_company_number(OUR_IBAN)
    assert not is_company_number(OTHER_ACCOUNT)
    assert account_scope(OURS) == account_scope("1400010326605")


# ---- signals: one test per statement format ----------------------------------------------------------------
def test_internal_debit_gives_ben_id_and_account():
    s = snb.parse(line("DEBIT", "INTERNAL_BEN_ID", detail=f"{OTHER_ACCOUNT} BEN ID:2327037210"))
    assert s["format"] == "INTERNAL_SNB"
    assert s["identifiers"] == [("BEN_ID", "2327037210"), ("ACCOUNT", OTHER_ACCOUNT)]


def test_internal_credit_gives_dep_id_the_sender_id():
    s = snb.parse(line("CREDIT", "INCOMING_LOCAL", "Incoming Internal Transfer", f"{OTHER_ACCOUNT} DEP ID:2323429131 CHNL:SNB Payment Systems"))
    assert s["identifiers"] == [("DEP_ID", "2323429131"), ("ACCOUNT", OTHER_ACCOUNT)]


def test_own_account_transfers_have_no_counterparty_either_way():
    credit = snb.parse(line("CREDIT", "INCOMING_LOCAL", "Incoming Internal Transfer", f"{OURS} DEP ID:2323429130 CHNL:SNB"))
    debit = snb.parse(line("DEBIT", "INTERNAL_BEN_ID", detail=f"{OURS} BEN ID:2323429130"))
    for s in (credit, debit):
        assert s["own_account"] and s["identifiers"] == []


def test_ips_name_drops_the_bank_code_and_the_memo_numbers():
    s = snb.parse(line("CREDIT", "IPS_LOCAL", "Incoming IPS local transfer",
                       "CITY:Jeddah 99999999SAINMAINMA9BXXX99999999999 999999SA *****SAUDI ARABIA SAINMA شركة رسوخ المتقدمة للمقاولات 1234567890123456 دفعة لشركة"))
    assert s["format"] == "IPS_LOCAL"
    assert s["identifiers"] == [("NAME", "شركة رسوخ المتقدمة للمقاولات")]
    assert s["display_name"] == "شركة رسوخ المتقدمة للمقاولات"


def test_ips_english_name_that_starts_with_sa_is_kept():
    assert snb.clean_ips_name("SAUDIA CARGO LTD") == "SAUDIA CARGO LTD"
    assert snb.clean_ips_name("SAINMA ACME TRADING") == "ACME TRADING"
    assert snb.clean_ips_name("ACME TRADING 12345678901") == "ACME TRADING"


def test_larger_local_credit_uses_the_payer_iban_never_ours():
    ok = snb.parse(line("CREDIT", "INCOMING_LOCAL", "Incoming Local transfer", f"SA CHNL: SAEED BIN ZYED ST {OTHER_IBAN} payment"))
    assert ok["format"] == "LARGE_LOCAL" and ok["identifiers"] == [("IBAN", OTHER_IBAN)]
    own = snb.parse(line("CREDIT", "INCOMING_LOCAL", "Incoming Local transfer", f"CITY:Jeddah {OUR_IBAN} CHNL:SNB"))
    assert own["own_account"] and own["identifiers"] == []


def test_larger_local_debit_name_comes_from_otbank():
    s = snb.parse(line("DEBIT", "LOCAL_OTBANK", detail="OTBANK:SABBACME COMPANY LTD"))
    assert s["identifiers"] == [("NAME", "ACME COMPANY LTD")]


def test_amount_never_decides_the_format():
    for amount_note in ("19999", "20000", "20001"):
        s = snb.parse(line("CREDIT", "IPS_LOCAL", "Incoming IPS local transfer", f"SAUDI ARABIA ACME CO {amount_note}"))
        assert s["format"] == "IPS_LOCAL"


def test_tawal_and_bank_adjustments_are_flagged():
    assert snb.parse(line("CREDIT", "INCOMING_LOCAL", "Incoming Local transfer", "TELECOMMUNICATIONS TOWERS COMPANY"))["tawal"]
    assert snb.parse(line("CREDIT", "UNKNOWN_FORMAT", "Transfer Fees Reversal"))["adjustment"]
    assert snb.parse(line("CREDIT", "UNKNOWN_FORMAT", "VAT Rebate"))["adjustment"]


def test_sadad_biller_code_is_extracted_without_inferring_a_payee():
    parsed = snb.parse(line("DEBIT", "SADAD", "SADAD payment", "Biller Code: 101 Electricity"))
    assert parsed["biller_code"] == "101"
    assert parsed["identifiers"] == [] and not parsed["display_name"]


# ---- identify -----------------------------------------------------------------------------------------------
def registry(entries):
    return lambda kind, value: entries.get((kind, hint_key(kind, value)), [])


def test_identify_prefers_agreeing_strong_identifiers_and_reports_conflicts():
    reg = registry({("DEP_ID", "2323429131"): [("CP-A", "ACTIVE")], ("ACCOUNT", hint_key("ACCOUNT", OTHER_ACCOUNT)): [("CP-A", "ACTIVE")]})
    result = identify([("DEP_ID", "2323429131"), ("ACCOUNT", OTHER_ACCOUNT)], reg)
    assert (result["status"], result["counterparty"]) == ("IDENTIFIED", "CP-A")
    clash = registry({("DEP_ID", "2323429131"): [("CP-A", "ACTIVE")], ("ACCOUNT", hint_key("ACCOUNT", OTHER_ACCOUNT)): [("CP-B", "ACTIVE")]})
    assert identify([("DEP_ID", "2323429131"), ("ACCOUNT", OTHER_ACCOUNT)], clash)["status"] == "CONFLICT"


def test_identify_suggested_and_none():
    reg = registry({("NAME", "acme"): [("CP-A", "SUGGESTED")]})
    assert identify([("NAME", "ACME")], reg) == {"status": "SUGGESTED", "counterparty": "", "candidates": ["CP-A"], "via": ""}
    assert identify([("NAME", "other")], reg)["status"] == "NONE"
    assert identify([], reg)["status"] == "NONE"


def test_beneficiary_registry_resolves_enabled_customer_and_supplier_links():
    customer = seed.plan({"source_key": "BEN-C", "beneficiary_name": "Customer Name", "erp_record_id": "CUST-1"},
                         set(), {}, set(), customers={"CUST-1"})
    supplier = seed.plan({"source_key": "BEN-S", "beneficiary_name": "Supplier Name", "erp_party": "Supplier: Supplier Name"},
                         {"SUP-1"}, {"Supplier Name": "SUP-1"}, set())
    assert customer["customer"] == "CUST-1" and customer["supplier"] == ""
    assert supplier["supplier"] == "SUP-1" and supplier["customer"] == ""


def test_beneficiary_registry_resolves_customer_exact_name_and_ignores_untyped_id():
    linked = seed.plan({"source_key": "BEN-C", "beneficiary_name": "Acme", "erp_party": "Customer: Acme"},
                       set(), {}, set(), customers={"CUST-2"}, customer_names={"Acme": "CUST-2"})
    ignored = seed.plan({"source_key": "BEN-X", "beneficiary_name": "Acme", "erp_record_id": "OTHER-1"},
                        {"SUP-1"}, {}, set(), customers={"CUST-2"})
    assert linked["customer"] == "CUST-2"
    assert ignored["customer"] == "" and ignored["supplier"] == ""


# ---- classify -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("direction,family,signals,facts,intent,route,expected", [
    ("DEBIT", "BANK_FEE", {}, {}, "", "", C.BANK_CHARGE),
    ("DEBIT", "FEE_VAT", {}, {}, "", "", C.BANK_CHARGE),
    ("DEBIT", "INTERNAL_BEN_ID", {"own_account": True}, {}, "", "", C.OWN_TRANSFER),
    ("DEBIT", "IPS_LOCAL", {}, {"is_company": True}, "", "REVIEW", C.OWN_TRANSFER),
    ("DEBIT", "IPS_LOCAL", {}, {}, "", "JE_BANK_TRANSFER", C.OWN_TRANSFER),
    ("DEBIT", "IPS_LOCAL", {"tawal": True}, {}, "", "", C.SPECIALIST),
    ("DEBIT", "INTERNAL_BEN_ID", {}, {"custody_account": "132223"}, "XXPC", "JE_EMPLOYEE", C.PETTY_CASH),
    ("DEBIT", "INTERNAL_BEN_ID", {}, {}, "XXPC", "", C.PETTY_CASH),
    ("DEBIT", "INTERNAL_BEN_ID", {}, {"is_employee": True}, "XXSC", "JE_EMPLOYEE", C.UNKNOWN),
    ("DEBIT", "LOCAL_OTBANK", {}, {}, "XXMT", "PAY_SUPPLIER|MAINTENANCE|CONFIRMED", C.UNKNOWN),
    ("DEBIT", "INTERNAL_BEN_ID", {}, {"is_employee": True}, "", "", C.EMPLOYEE),
    ("DEBIT", "IPS_LOCAL", {}, {}, "", "JE_EMPLOYEE", C.EMPLOYEE),
    ("DEBIT", "IPS_LOCAL", {}, {}, "XXSL", "", C.EMPLOYEE),
    ("DEBIT", "SADAD", {}, {}, "", "", C.OTHER),
    ("DEBIT", "PAYROLL_FEE", {}, {}, "", "", C.OTHER),
    ("DEBIT", "IPS_LOCAL", {}, {"expense_account": "5130"}, "", "", C.EXPENSE_PAYMENT),
    ("DEBIT", "IPS_LOCAL", {}, {}, "", "JE_PERSON|PROJECT_OPERATING_COST|CONFIRMED|NO_PI", C.EXPENSE_PAYMENT),
    ("DEBIT", "IPS_LOCAL", {}, {}, "XXMR", "PAY_SUPPLIER|MATERIAL_SUPPLY|CONFIRMED", C.SUPPLIER_PAYMENT),
    ("DEBIT", "LOCAL_OTBANK", {}, {}, "", "", C.UNKNOWN),
    ("CREDIT", "IPS_LOCAL", {"format": "IPS_LOCAL"}, {}, "", "", C.CUSTOMER_RECEIPT),
    ("CREDIT", "INCOMING_LOCAL", {"format": "INTERNAL_SNB"}, {}, "", "", C.CUSTOMER_RECEIPT),
    ("CREDIT", "INCOMING_LOCAL", {"format": "LARGE_LOCAL", "own_account": True}, {}, "", "", C.OWN_TRANSFER),
    ("CREDIT", "INCOMING_LOCAL", {"format": "LARGE_LOCAL", "tawal": True}, {}, "", "", C.SPECIALIST),
    ("CREDIT", "UNKNOWN_FORMAT", {"adjustment": True}, {}, "", "", C.OTHER),
    ("CREDIT", "LG_OUTWARD", {}, {}, "", "", C.OTHER),
    ("CREDIT", "UNKNOWN_FORMAT", {}, {}, "", "", C.OTHER),
])
def test_classification_table(direction, family, signals, facts, intent, route, expected):
    assert C.classify(direction, family, signals, facts, intent, route) == expected


# ---- reconcile ----------------------------------------------------------------------------------------------
def doc(name, amount, day, **extra):
    base = {"doctype": "Journal Entry", "name": name, "date": day, "docstatus": 1, "amount": amount, "reference": "",
            "marker": "", "bank_account": "13121"}
    base.update(extra)
    return base


def movement(amount=-1000.0, day="2026-10-05", key="K1", reference="R1"):
    return {"key": key, "amount": amount, "date": day, "reference": reference, "bank_account": "13121"}


def test_marker_beats_everything():
    out = R.pick_document(movement(), [doc("JV-A", -1000, "2026-10-05"), doc("JV-B", -1000, "2026-10-05", marker="K1")])
    assert (out[0], out[1][0]["name"], out[2]) == ("LINK", "JV-B", "MARKER")


def test_unique_ledger_match_requires_review():
    out = R.pick_document(movement(), [doc("JV-A", -1000, "2026-10-07"), doc("JV-B", -999, "2026-10-05"), doc("JV-C", -1000, "2026-10-20")])
    assert (out[0], out[1][0]["name"], out[2]) == ("PICK", "JV-A", "LEDGER")


def test_wrong_direction_or_account_never_matches():
    assert R.pick_document(movement(), [doc("JV-A", 1000, "2026-10-05")])[0] == "NONE"
    assert R.pick_document(movement(), [doc("JV-A", -1000, "2026-10-05", bank_account="13123")])[0] == "NONE"


def test_several_candidates_need_a_person_unless_reference_or_day_is_unique():
    twins = [doc("JV-A", -1000, "2026-10-04"), doc("JV-B", -1000, "2026-10-06")]
    assert R.pick_document(movement(), twins)[0] == "PICK"
    assert R.pick_document(movement(), twins + [doc("JV-C", -1000, "2026-10-05")])[0] == "PICK"
    by_ref = [doc("JV-A", -1000, "2026-10-04", reference="R1"), doc("JV-B", -1000, "2026-10-06")]
    assert R.pick_document(movement(), by_ref)[0] == "PICK"


def test_claimed_rejected_and_cancelled_documents_are_skipped():
    docs = [doc("JV-A", -1000, "2026-10-05")]
    assert R.pick_document(movement(), docs, claimed={"JV-A"})[0] == "NONE"
    assert R.pick_document(movement(), docs, rejected={"JV-A"})[0] == "NONE"
    assert R.pick_document(movement(), [doc("JV-A", -1000, "2026-10-05", docstatus=2)])[0] == "NONE"


def test_am_hint_links_only_when_it_agrees_on_account_and_amount():
    hint = doc("JV-Z", -1000, "2026-11-30")
    assert R.pick_document(movement(), [], hint=hint)[2] == "AM_LINK"
    assert R.pick_document(movement(), [], hint=doc("JV-Z", -900, "2026-10-05"))[0] == "NONE"
    assert R.pick_document(movement(), [], hint=doc("JV-Z", -1000, "2026-10-05", bank_account="13123"))[0] == "NONE"
    assert R.pick_document(movement(), [], hint=doc("JV-Z", 1000, "2026-10-05"))[0] == "NONE"


# ---- documents ----------------------------------------------------------------------------------------------
def test_payment_entry_bodies_for_both_directions():
    pay = D.payment_entry(movement(), "Supplier", "Collective", "2261 - AP", "13121 - Bank", "Acme", "SUPPLIER_PAYMENT", holding=True, intended="Acme Co")
    assert (pay["payment_type"], pay["paid_from"], pay["paid_to"], pay["paid_amount"]) == ("Pay", "13121 - Bank", "2261 - AP", 1000.0)
    assert pay["custom_snb_idempotency_key"] == "K1" and pay["custom_linkage_agent"] == "Active" and "Acme Co" in pay["remarks"]
    receive = D.payment_entry(movement(2500.5, key="K2"), "Customer", "Unidentified Receipts", "1331 - AR", "13121 - Bank")
    assert (receive["payment_type"], receive["paid_from"], receive["paid_to"], receive["paid_amount"], receive["custom_linkage_agent"]) == ("Receive", "1331 - AR", "13121 - Bank", 2500.5, "Off")


def test_expense_journal_carries_its_fees_and_balances():
    fees = [{"amount": -1.0, "family": "BANK_FEE"}, {"amount": -0.15, "family": "FEE_VAT"}]
    je = D.expense_journal(movement(), "5130 - Subcontract", "13121 - Bank", fees, "538 - Charges", "", "Ejaz", "EXPENSE_PAYMENT")
    debit = round(sum(l["debit_in_account_currency"] for l in je["accounts"]), 2)
    credit = round(sum(l["credit_in_account_currency"] for l in je["accounts"]), 2)
    assert debit == credit == 1001.15
    assert len(je["accounts"]) == 6 and je["custom_pc_statement_key"] == "K1"
    vat = D.expense_journal(movement(), "5130", "13121", fees, "538", "521", "Ejaz", "EXPENSE_PAYMENT")
    assert [l["account"] for l in vat["accounts"] if l["debit_in_account_currency"]] == ["5130", "538", "521"]


def test_fee_journal_uses_its_own_marker():
    je = D.fee_journal(movement(), [{"amount": -1.15, "family": "BANK_FEE"}], "13121", "538", "")
    assert je["custom_pc_statement_key"] == "K1#FEE" and len(je["accounts"]) == 2


def test_incoming_local_bic_and_extn_produces_a_reviewable_payer_name():
    source = {"parser_family": "INCOMING_LOCAL", "direction": "CREDIT", "transaction_description": "Incoming Local transfer",
              "detail_description": "SA CHNL: KING FAHD DIST 7639 KING FAHAD RD SA6885476230061800108SAR SUPP 23659568000109 BNPASARI ENOVA FOR FACILITIES AND ENERG EXTN980263063RK6"}
    result = snb.parse(source)
    assert result["display_name"] == "ENOVA FOR FACILITIES AND ENERG"
    assert result["identifiers"] == [("NAME", "ENOVA FOR FACILITIES AND ENERG")]
    reg = registry({("NAME", "enova for facilities and energ"): [("CP-1", "ACTIVE")]})
    assert identify(result["identifiers"], reg)["status"] == "SUGGESTED"


def test_format_specific_names_take_priority_as_suggestions_without_changing_legacy_hints():
    reg = registry({("NAME", "acme"): [("LEGACY", "ACTIVE")],
                    ("NAME_IPS_LOCAL", "acme"): [("IPS", "ACTIVE")],
                    ("NAME_LARGE_LOCAL", "acme"): [("LARGE", "ACTIVE")]})
    ips = identify([("NAME", "ACME"), ("NAME_IPS_LOCAL", "ACME")], reg)
    large = identify([("NAME", "ACME"), ("NAME_LARGE_LOCAL", "ACME")], reg)
    assert ips["status"] == "SUGGESTED" and ips["candidates"] == ["IPS"]
    assert large["status"] == "SUGGESTED" and large["candidates"] == ["LARGE"]
    assert identify([("NAME", "ACME")], reg)["candidates"] == ["LEGACY"]


def test_petty_cash_body_records_reviewed_employee_and_statement_identity():
    movement = {"key": "BANK-KEY", "amount": -1000, "date": "2026-11-10", "reference": "REF-1"}
    body = D.petty_cash_journal(movement, "EMP-1", "1322 - Employee", "131 - Bank", [], "Fees", "VAT", "Employee")
    assert body["custom_pc_top_up"] == 1 and body["custom_pc_employee"] == "EMP-1"
    assert body["custom_pc_statement_key"] == "BANK-KEY" and body["custom_pc_funding_source"] == "Bank Statement"
    assert body["accounts"][0]["account"] == "1322 - Employee"
    assert body["accounts"][1]["account"] == "131 - Bank"
    with pytest.raises(ValueError):
        D.petty_cash_journal(movement, "", "1322 - Employee", "131 - Bank", [], "Fees", "VAT")


def test_own_transfer_journal_uses_one_debit_and_one_credit():
    movement = {"key": "KEY-OUT", "amount": -2500, "date": "2026-11-10", "reference": "REF"}
    body = D.own_transfer_journal(movement, "BANK-OUT", "BANK-IN")
    assert body["custom_pc_statement_key"] == "KEY-OUT"
    assert body["accounts"][0]["account"] == "BANK-IN" and body["accounts"][0]["debit_in_account_currency"] == 2500
    assert body["accounts"][1]["account"] == "BANK-OUT" and body["accounts"][1]["credit_in_account_currency"] == 2500
    with pytest.raises(ValueError):
        D.own_transfer_journal(movement, "BANK", "BANK")


def test_sadad_biller_is_read_from_the_real_statement_shape():
    parsed = snb.parse(line("DEBIT", "SADAD", "SADAD Payment", "165-2001003327019603 01400010326605 6950931237"))
    assert (parsed["biller_code"], parsed["bill_account"]) == ("165", "2001003327019603")
    assert parsed["identifiers"] == [("SADAD_CODE", "165-2001003327019603")] and not parsed["display_name"]


def test_draft_remarks_name_the_type_of_supply():
    mv = {"key": "K", "amount": -100, "date": dt.date(2026, 11, 3), "reference": "R", "supply": "Maintenance"}
    assert "Type of supply: Maintenance" in D.remarks(mv, "Payee", "SUPPLIER_PAYMENT")
    assert "Type of supply" not in D.remarks({**mv, "supply": ""}, "Payee", "SUPPLIER_PAYMENT")


def test_sadad_biller_names_come_from_the_public_list_and_unlisted_codes_stay_unnamed():
    from bank_router.sadad_billers import biller_name
    assert biller_name("050") == "Ministry of Labor" and biller_name("5") == "Mobily" and biller_name("020").endswith("Zakat and Tax")
    assert biller_name("090") == "" and biller_name("") == ""
    parsed = snb.parse(line("DEBIT", "SADAD", "SADAD Payment", "050-100000000000001 01400010326605 1234567890"))
    assert (parsed["biller_code"], parsed["biller_name"]) == ("050", "Ministry of Labor")
