from decimal import Decimal
from sig_warehouse.sig_accounting.bank_router.snb_financing import reconcile_facility, match_unique_transfer


def test_settlement_needs_principal_and_respects_booked_interest():
    assert reconcile_facility(facility='A', drawdown=1000, settlement=1050)['cost'] is None
    row = reconcile_facility(facility='A', drawdown=1000, settlement=1050, principal=1000, booked_cost=40)
    assert row['status'] == 'CLOSED' and row['remaining_cost'] == Decimal('10.00')
    assert reconcile_facility(facility='A', drawdown=1000, settlement=1050, principal=1000, booked_cost=60)['status'] == 'SETTLEMENT SEEN'


def test_transfer_requires_unique_reference_and_amount():
    debit = {'source_tail': '3605', 'destination_tail': '6605', 'reference': '123', 'amount': '100'}
    credit = {'account_tail': '6605', 'reference': '123', 'amount': '100'}
    assert match_unique_transfer(debit, [credit])['status'] == 'MATCHED'
    assert match_unique_transfer(debit, [credit, credit])['reason'] == 'TRANSFER_AMBIGUOUS'
    assert match_unique_transfer(debit, [])['reason'] == 'TRANSFER_MISSING'


def test_classification_keeps_receipts_and_financing_separate():
    from sig_warehouse.sig_accounting.bank_router.snb_financing import summarize_movements
    rows = [
        {'account_tail':'3605', 'reference':'1', 'date':'2026-11-05', 'direction':'CREDIT', 'amount':24133.63, 'description':'Telecommunication Towers Tawal'},
        {'account_tail':'3605', 'reference':'2', 'date':'2026-11-11', 'direction':'DEBIT', 'amount':1799396.53, 'description':'Financing Early Settlement'},
        {'account_tail':'3605', 'reference':'3', 'date':'2026-11-12', 'direction':'DEBIT', 'amount':1824054.15, 'description':'Outgoing transfer 01400010326605'},
    ]
    assert [r['classification'] for r in summarize_movements(rows)] == ['TAWAL_RECEIPT','SETTLEMENT_CANDIDATE','TRANSFER_TO_6605']


def test_settlement_and_reopening_signal():
    from sig_warehouse.sig_accounting.bank_router.snb_financing import financing_status
    settlement = {'account_tail':'3605', 'reference':'2', 'date':'2026-11-11', 'direction':'DEBIT', 'amount':1799396.53, 'description':'Financing Early Settlement'}
    incoming = {'account_tail':'3605', 'reference':'3', 'date':'2026-11-12', 'direction':'CREDIT', 'amount':1799637.75, 'description':'Incoming internal transfer'}
    assert financing_status([settlement])['status'] == 'CLOSURE_ONGOING'
    assert financing_status([incoming, settlement])['status'] == 'FUNDING_RECEIVED_REVIEW'

def test_financing_review_links_booked_costs_and_uses_both_transfer_legs():
    from sig_warehouse.sig_accounting.bank_router.snb_financing import allocation_review

    rows = [
        {'name': 'loan', 'account_tail': '3605', 'reference': 'key1', 'bank_reference': '123456',
         'date': '2026-08-24', 'direction': 'CREDIT', 'amount': 1199758.50, 'description': 'Loan disbursement'},
        {'name': 'transfer', 'account_tail': '3605', 'reference': 'key2', 'bank_reference': '654321',
         'date': '2026-08-25', 'direction': 'DEBIT', 'amount': 1199758.50, 'description': 'Outgoing internal transfer 01400010326605'},
    ]
    credits = [{'account_tail': '6605', 'reference': '654321', 'date': '2026-08-25', 'direction': 'CREDIT', 'amount': 1199758.50}]
    booked = [
        {'voucher_type': 'Journal Entry', 'voucher_no': 'ACC-JV-2026-01579', 'posting_date': '2026-08-24',
         'remarks': 'Bank ref 123456', 'account_number': number, 'debit': debit, 'credit': credit}
        for number, debit, credit in [('13124', 1199758.50, 0), ('221', 0, 1239842.96), ('5151', 39842.96, 0), ('538', 241.50, 0)]
    ]
    result = allocation_review(rows, credits, booked)
    assert result['status'] == 'OPEN'
    loan, transfer = result['movements']
    assert loan['posted_allocation']['interest'] == Decimal('39842.96')
    assert loan['posted_allocation']['fees'] == Decimal('241.50')
    assert transfer['transfer_status'] == 'MATCHED'
    assert [line['account'] for line in transfer['proposed_lines']] == ['13123', '13124']
    transfer_voucher = [
        {'voucher_type': 'Journal Entry', 'voucher_no': 'ACC-JV-2026-01578', 'posting_date': '2026-08-25',
         'remarks': '', 'account_number': number, 'debit': debit, 'credit': credit}
        for number, debit, credit in [('13124', 0, 1199758.50), ('13123', 1199758.50, 0)]
    ]
    booked_transfer = allocation_review(rows, credits, booked + transfer_voucher)['movements'][1]
    assert booked_transfer['allocation_status'] == 'VERIFY_ERP_CANDIDATE'
    assert 'proposed_lines' not in booked_transfer
