"""Offline business scenarios: these build in-memory proposals, never ERP entries."""
import pytest

from sig_warehouse.sig_accounting.bank_router.business_routes import resolve_route
from sig_warehouse.sig_accounting.bank_router.documents import (
    expense_journal, fee_journal, own_transfer_journal, payment_entry, petty_cash_journal,
)


@pytest.mark.parametrize("movement,party,expected", [
    ({"direction": "DEBIT"}, {"employee": "E1", "custody_account": "1322"}, ""),
    ({"direction": "DEBIT", "category": "XXPC"}, {"employee": "E1", "custody_account": "1322"}, "custody_topup"),
    ({"direction": "DEBIT", "category": "XXSL"}, {"employee": "E1"}, "employee_salary"),
    ({"direction": "DEBIT", "category": "XXHR"}, {"employee": "E1"}, "employee_advance"),
    ({"direction": "DEBIT", "category": "XXMR"}, {"supplier": "S1"}, "supplier"),
    ({"direction": "CREDIT"}, {"customer": "C1"}, "client_receipt"),
    ({"direction": "CREDIT"}, {}, "other_in"),
    ({"direction": "CREDIT", "is_tawal": True}, {}, "tawal"),
    ({"direction": "DEBIT", "is_sadad": True, "biller_account": "ELECTRICITY"}, {}, "bill"),
    ({"direction": "DEBIT", "paired_transfer": {"name": "other-leg"}}, {}, "own_transfer"),
])
def test_purpose_suggestions_need_the_right_evidence(movement, party, expected):
    result = resolve_route(movement, party)
    assert result["route"] == expected
    assert result["state"] in ("ASK", "CONFIRM", "SPECIALIST")


def test_untagged_employee_payment_does_not_inherit_topup_memory():
    memory = {"confirmed": True, "route": "custody_topup", "direction": "DEBIT", "purpose": "XXPC", "account": "1322"}
    result = resolve_route({"direction": "DEBIT"}, {"employee": "E1", "custody_account": "1322"}, [memory])
    assert result["state"] == "ASK" and result["route"] == ""


def test_obed_topup_proposal_carries_pc_flags_and_balances_fees():
    movement = {"date": "2026-11-10", "reference": "130480245", "amount": -150, "key": "SIM-OBED"}
    fees = [{"amount": -0.50, "family": "BANK_FEE"}, {"amount": -0.08, "family": "FEE_VAT"}]
    entry = petty_cash_journal(movement, "EMP-OBED", "132244", "BANK", fees, "FEES", "VAT", "Obed")
    assert entry["custom_pc_top_up"] == 1 and entry["custom_pc_employee"] == "EMP-OBED"
    assert entry["custom_pc_funding_source"] == "Bank Statement" and entry["custom_pc_bank_txn_id"] == "130480245"
    assert entry["accounts"][0]["account"] == "132244" and entry["accounts"][0]["debit_in_account_currency"] == 150
    assert sum(x["debit_in_account_currency"] for x in entry["accounts"]) == pytest.approx(150.58)
    assert sum(x["credit_in_account_currency"] for x in entry["accounts"]) == pytest.approx(150.58)


def test_payment_receipt_and_own_transfer_proposals_preserve_direction():
    out = {"date": "2026-11-10", "reference": "SIM-OUT", "amount": -1000, "key": "OUT"}
    incoming = {**out, "amount": 1000, "key": "IN"}
    supplier = payment_entry(out, "Supplier", "SUP-1", "PAYABLE", "BANK")
    customer = payment_entry(incoming, "Customer", "CUST-1", "RECEIVABLE", "BANK")
    assert (supplier["payment_type"], supplier["paid_from"], supplier["paid_to"]) == ("Pay", "BANK", "PAYABLE")
    assert (customer["payment_type"], customer["paid_from"], customer["paid_to"]) == ("Receive", "RECEIVABLE", "BANK")
    transfer = own_transfer_journal(out, "BANK-A", "BANK-B")
    assert (transfer["accounts"][0]["account"], transfer["accounts"][1]["account"]) == ("BANK-B", "BANK-A")
    assert expense_journal(out, "EXPENSE", "BANK", [], "FEES", "VAT")["accounts"][0]["account"] == "EXPENSE"
    assert fee_journal(out, [{"amount": -0.5, "family": "BANK_FEE"}], "BANK", "FEES", "VAT")["custom_pc_statement_key"] == "OUT#FEE"
