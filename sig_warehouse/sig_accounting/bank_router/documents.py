"""Stage 5: ERP document bodies for a movement. Pure builders: callers resolve accounts and parties first.

Nothing here submits anything. Every body carries the statement-key marker so a rerun finds its own document.
"""
import datetime as dt

COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"
COST_CENTER = "Main - SIG"
MODE_OF_PAYMENT = "Wire Transfer"
FEE_MARKER_SUFFIX = "#FEE"


def posting_date(movement):
    value = movement["date"]
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


def remarks(movement, label, kind, holding=False, intended=""):
    lines = ["[SNB auto-draft: do not submit until cleared]", f"Counterparty: {label or '(not identified)'}",
             f"Kind: {kind}", f"Bank ref: {movement.get('reference') or ''} | {posting_date(movement)} | {abs(float(movement['amount'])):.2f} SAR"]
    if movement.get("supply"):
        lines.append(f"Type of supply: {movement['supply']}")
    if holding:
        lines.append(f"Holding party (intended: {intended or 'unknown'}): confirm the real party in the Bank Router")
    return "\n".join(lines)


def payment_entry(movement, party_type, party, party_account, bank_account, label="", kind="", holding=False,
                  intended="", references=None):
    """Pay (money out, Supplier) or Receive (money in, Customer) Payment Entry body."""
    amount = round(abs(float(movement["amount"])), 2)
    receive = float(movement["amount"]) > 0
    body = {
        "doctype": "Payment Entry", "payment_type": "Receive" if receive else "Pay", "company": COMPANY,
        "party_type": party_type, "party": party, "posting_date": posting_date(movement),
        "paid_from": party_account if receive else bank_account, "paid_to": bank_account if receive else party_account,
        "paid_amount": amount, "received_amount": amount, "source_exchange_rate": 1, "target_exchange_rate": 1,
        "mode_of_payment": MODE_OF_PAYMENT, "reference_no": str(movement.get("reference") or movement["key"])[:140],
        "reference_date": posting_date(movement), "custom_remarks": 1,
        "remarks": remarks(movement, label, kind, holding, intended),
        "custom_snb_idempotency_key": movement["key"],
        "custom_linkage_agent": "Active" if holding else "Off",
    }
    if references:
        body["references"] = references
    return body


def fee_lines(fees, bank_account, fee_account, vat_account):
    """One debit line per fee row and one bank credit line per fee row, so each ties to a statement amount."""
    lines = []
    for fee in fees:
        amount = round(abs(float(fee["amount"])), 2)
        expense = vat_account if fee.get("family") == "FEE_VAT" and vat_account else fee_account
        lines.append({"account": expense, "debit_in_account_currency": amount, "credit_in_account_currency": 0, "cost_center": COST_CENTER})
        lines.append({"account": bank_account, "debit_in_account_currency": 0, "credit_in_account_currency": amount, "cost_center": COST_CENTER})
    return lines


def expense_journal(movement, expense_account, bank_account, fees, fee_account, vat_account, label="", kind=""):
    """Non-employee person or expense payment: debit the category account, credit bank, fee lines in the same JE."""
    amount = round(abs(float(movement["amount"])), 2)
    lines = [
        {"account": expense_account, "debit_in_account_currency": amount, "credit_in_account_currency": 0, "cost_center": COST_CENTER},
        {"account": bank_account, "debit_in_account_currency": 0, "credit_in_account_currency": amount, "cost_center": COST_CENTER},
    ] + fee_lines(fees, bank_account, fee_account, vat_account)
    return {
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": COMPANY, "posting_date": posting_date(movement),
        "custom_pc_statement_key": movement["key"], "user_remark": f"[SNB auto-draft] ref {movement.get('reference') or ''} | {label} | {kind}",
        "remark": remarks(movement, label, kind), "accounts": lines,
    }


def fee_journal(movement, fees, bank_account, fee_account, vat_account):
    """Separate fee and VAT journal for a main line settled by a Payment Entry."""
    return {
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": COMPANY, "posting_date": posting_date(movement),
        "custom_pc_statement_key": movement["key"] + FEE_MARKER_SUFFIX,
        "user_remark": f"[SNB auto-draft] bank charges for ref {movement.get('reference') or ''}",
        "accounts": fee_lines(fees, bank_account, fee_account, vat_account),
    }


def petty_cash_journal(movement, employee, custody_account, bank_account, fees, fee_account, vat_account, label=""):
    """A reviewer-confirmed Employee custody top-up, subject to ERP funding validation."""
    if not employee or not custody_account or custody_account == bank_account:
        raise ValueError("A confirmed employee and distinct custody account are required.")
    body = expense_journal(movement, custody_account, bank_account, fees, fee_account, vat_account, label, "PETTY_CASH")
    body.update(custom_pc_top_up=1, custom_pc_transfer_category="XXPC", custom_pc_employee=employee,
                custom_pc_funding_date=posting_date(movement), custom_pc_funding_source="Bank Statement",
                custom_pc_bank_txn_id=str(movement.get("reference") or "")[:140])
    return body


def own_transfer_journal(movement, from_account, to_account):
    """One journal for both sides of a reviewed transfer between company banks."""
    if not from_account or not to_account or from_account == to_account:
        raise ValueError("Two distinct company bank accounts are required.")
    return expense_journal(movement, to_account, from_account, [], "", "", "Company bank transfer", "OWN_TRANSFER")
