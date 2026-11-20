"""Read-only statement to ledger reconciliation in the Bank Router."""
import json
import re

import frappe
from frappe import _
from frappe.utils import add_days

from sig_warehouse.sig_accounting.bank_router.documents import COMPANY
from sig_warehouse.sig_accounting.bank_router.snb_financing import allocation_review, classify_movement, money, settlement_cost

ACCOUNT_NUMBERS = ('221', '5151', '538', '13124', '13123')


def _require_read(doctype):
    if frappe.session.user == 'Guest' or not frappe.has_permission(doctype, 'read'):
        frappe.throw(_('Read access to {0} is required.').format(doctype), frappe.PermissionError)


def _movement(doc):
    source = json.loads(doc.source_json or '{}')
    description = ' '.join(str(source.get(k) or '') for k in (
        'transaction_description', 'detail_description', 'extra_description', 'description_extra', 'remarks'))
    tawal = re.search(r'\b(?:CRF\s*:|Ref\s*-)\s*(\d{10,12})(?!\d)', description, re.I)
    return {
        'name': doc.name, 'account_tail': doc.source_account_tail,
        'reference': doc.source_key, 'date': str(doc.event_date),
        'direction': doc.direction, 'amount': abs(money(doc.amount)),
        'description': description, 'bank_reference': str(source.get('reference') or ''),
        'tawal_reference': tawal.group(1) if tawal else '',
        'linked_voucher': (doc.erp_doctype, doc.erp_document) if doc.erp_document else None,
    }


@frappe.whitelist(methods=['GET'])
def review():
    for dt in ('SNB Movement Review', 'GL Entry', 'Account'):
        _require_read(dt)
    accounts = frappe.get_list('Account', filters={
        'account_number': ['in', ACCOUNT_NUMBERS], 'company': COMPANY, 'is_group': 0,
    }, fields=['name', 'account_number'], limit_page_length=0)
    by_name = {a.name: a.account_number for a in accounts}
    if len(by_name) != len(ACCOUNT_NUMBERS) or set(by_name.values()) != set(ACCOUNT_NUMBERS):
        frappe.throw(_('The five SNB financing accounts must be uniquely visible to review allocations.'))
    fields = ['name', 'source_key', 'source_account_tail', 'event_date', 'direction', 'amount', 'source_json', 'erp_doctype', 'erp_document']
    moves = [_movement(m) for m in frappe.get_list(
        'SNB Movement Review', filters={'source_account_tail': '3605', 'source_key': ['like', 'SNB-%']},
        fields=fields, order_by='event_date asc, name asc', limit_page_length=0,
    )]
    ledger_fields = ['account', 'posting_date', 'debit', 'credit', 'voucher_type', 'voucher_no', 'remarks']
    gl_filters = {'company': COMPANY, 'is_cancelled': 0}
    loan = next(k for k, v in by_name.items() if v == '221')
    loan_rows = frappe.get_list('GL Entry', filters={**gl_filters, 'account': loan},
                                fields=['debit', 'credit', 'posting_date'], order_by='posting_date asc', limit_page_length=0)
    rows, credits = [], []
    if moves:
        days = ['between', [add_days(moves[0]['date'], -3), add_days(moves[-1]['date'], 3)]]
        credits = [_movement(m) for m in frappe.get_list('SNB Movement Review', filters={
            'source_account_tail': '6605', 'direction': 'CREDIT', 'event_date': days, 'source_key': ['like', 'SNB-%'],
        }, fields=fields, limit_page_length=0)]
        for credit in credits:
            credit['reference'] = credit['bank_reference']
        rows = [dict(r, account_number=by_name[r.account]) for r in frappe.get_list('GL Entry', filters={
            **gl_filters, 'account': ['in', list(by_name)], 'posting_date': days,
        }, fields=ledger_fields, limit_page_length=0)]
    result = allocation_review(moves, credits, rows)
    result['loan_credit_balance'] = sum((money(r.credit) - money(r.debit) for r in loan_rows), money(0)) if loan_rows else None
    result['loan_first_posting'] = str(loan_rows[0].posting_date) if loan_rows else None
    result['loan_last_posting'] = str(loan_rows[-1].posting_date) if loan_rows else None
    result['last_staged_movement'] = moves[-1]['date'] if moves else None
    result['coverage_warning'] = _('Latest staged movement shows the last transaction received by ERP. Verify statement coverage and the bank loan balance before closing a period.')
    return result


@frappe.whitelist(methods=['GET'])
def preview_cost(movement, bank_evidence, principal, already_booked, extra_fees=0, refund=0):
    """Scenario from a visible settlement and Finance-confirmed figures."""
    _require_read('SNB Movement Review')
    _require_read('GL Entry')
    evidence = str(bank_evidence or '').strip()
    if not evidence or len(evidence) > 140 or principal in ('', None) or already_booked in ('', None):
        frappe.throw(_('Provide the bank evidence reference, principal and already booked costs.'))
    doc = frappe.get_doc('SNB Movement Review', movement)
    doc.check_permission('read')
    row = _movement(doc)
    if not row['reference'].startswith('SNB-') or classify_movement(row) != 'SETTLEMENT_CANDIDATE':
        frappe.throw(_('The selected movement must be an SNB financing settlement.'))
    try:
        preview = settlement_cost(row['amount'], principal, already_booked, extra_fees, refund)
    except ValueError as error:
        frappe.throw(_(str(error)))
    return {**preview, 'statement_reference': row['bank_reference'], 'evidence': evidence}
