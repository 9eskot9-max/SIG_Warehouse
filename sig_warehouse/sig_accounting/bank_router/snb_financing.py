"""Read-only financing reconciliation; ambiguous evidence always stays in review."""
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from .text import normalize_text


def money(value):
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal('0.01'))
        if not amount.is_finite():
            raise ValueError('Invalid amount')
        return amount
    except InvalidOperation as exc:
        raise ValueError('Invalid amount') from exc


def reconcile_facility(*, facility, drawdown, settlement=None, principal=None, booked_cost=0, extra_fees=0, refund=0):
    """Calculate cost only against confirmed settled principal, accounting for booked expense."""
    if not str(facility or '').strip():
        raise ValueError('Facility reference is required')
    opening = money(drawdown)
    if opening <= 0:
        raise ValueError('Drawdown must be positive')
    result = {'facility': facility, 'drawdown': opening, 'status': 'OPEN', 'cost': None,
              'already_booked': money(booked_cost), 'remaining_cost': None, 'issues': []}
    if settlement is None:
        return result
    paid = money(settlement)
    if paid <= 0:
        raise ValueError('Settlement must be positive')
    result['settlement'] = paid
    result['status'] = 'SETTLEMENT SEEN'
    if principal is None:
        result['issues'].append('PRINCIPAL_REQUIRED')
        return result
    result.update(settlement_cost(paid, principal, booked_cost, extra_fees, refund))
    if result['issues']:
        return result
    result['status'] = 'CLOSED'
    return result


def settlement_cost(settlement, principal, booked_cost, extra_fees=0, refund=0):
    paid, principal, booked, fees, refunded = map(money, (settlement, principal, booked_cost, extra_fees, refund))
    if paid <= 0 or min(principal, fees, refunded, booked) < 0:
        raise ValueError('Settlement must be positive and supporting amounts must not be negative')
    cost = paid - principal + fees - refunded
    remaining = cost - booked
    return {'settlement': paid, 'principal': principal, 'cost': cost, 'remaining_cost': remaining,
            'already_booked': booked, 'extra_fees': fees, 'refund': refunded,
            'issues': ['COST_DISCREPANCY_REVIEW'] if min(cost, remaining) < 0 else []}


def match_unique_transfer(debit, credits):
    """Pair only explicit 3605-to-6605 transfers with unique reference evidence."""
    if debit.get('source_tail') != '3605' or debit.get('destination_tail') != '6605':
        return {'status': 'NOT_TRANSFER'}
    reference = str(debit.get('reference') or '').strip()
    if not reference:
        return {'status': 'REVIEW', 'reason': 'REFERENCE_REQUIRED'}
    matches = [c for c in credits if c.get('account_tail') == '6605'
               and c.get('direction', 'CREDIT') == 'CREDIT'
               and str(c.get('reference') or '').strip() == reference
               and (not debit.get('date') or abs((date.fromisoformat(c['date']) - date.fromisoformat(debit['date'])).days) <= 2)
               and money(c.get('amount')) == money(debit.get('amount'))]
    if len(matches) != 1:
        return {'status': 'REVIEW', 'reason': 'TRANSFER_MISSING' if not matches else 'TRANSFER_AMBIGUOUS'}
    return {'status': 'MATCHED', 'credit': matches[0]}


def classify_movement(row):
    """Classify source evidence without turning transfers into income."""
    text = ' '.join(str(row.get(k) or '') for k in ('description', 'details', 'extra', 'remarks')).lower()
    direction = str(row.get('direction') or '').upper()
    if row.get('account_tail') != '3605':
        return 'OUTSIDE_3605'
    digits = set(re.findall(r'(?<!\d)\d{10,24}(?!\d)', text))
    names = normalize_text(text)
    if direction == 'CREDIT' and re.search(r'\btawal\b|telecommunications? towers|ابراج ا\s*لاتصالات', names):
        return 'TAWAL_RECEIPT'
    if direction == 'DEBIT' and '01400010326605' in digits:
        return 'TRANSFER_TO_6605'
    if '23659568000109' in digits or '01400010326605' in digits:
        return 'OWN_ACCOUNT_TRANSFER'
    if direction == 'DEBIT' and re.search(r'financing (?:early )?settlement|سداد القرض', names):
        return 'SETTLEMENT_CANDIDATE'
    if direction == 'DEBIT' and 'internal transfer' in names and digits - {'81300000023605'}:
        return 'SETTLEMENT_OR_TRANSFER_REVIEW'
    if direction == 'CREDIT' and re.search(r'financing (?:drawdown|disbursement)|loan disbursement', names):
        return 'FUNDING_CANDIDATE'
    if direction == 'CREDIT' and 'internal transfer' in names:
        return 'DRAWDOWN_OR_TRANSFER_REVIEW'
    return 'OTHER_REVIEW'


def summarize_movements(rows):
    """Deterministic inbox for complete statement rows; preserves source identity."""
    out = []
    seen = set()
    for row in rows:
        identity = (str(row.get('account_tail') or ''), str(row.get('reference') or ''),
                    str(row.get('date') or ''), str(row.get('direction') or ''), str(money(row.get('amount'))))
        if not identity[1] or not identity[2]:
            raise ValueError('Bank reference and date are required')
        if identity in seen:
            raise ValueError('Duplicate bank movement in statement')
        seen.add(identity)
        out.append({**row, 'classification': classify_movement(row)})
    return out


def financing_status(rows):
    """Report latest observable financing signal without inventing facility matches."""
    ordered = sorted(summarize_movements(rows), key=lambda r: (str(r['date']), str(r['reference'])))
    state, evidence = _latest_status(ordered)
    return {'status': state, 'evidence': evidence, 'movements': ordered}


def _latest_status(ordered):
    state, evidence = 'UNKNOWN', None
    for row in ordered:
        kind = row['classification']
        if kind == 'SETTLEMENT_CANDIDATE':
            posting = row.get('posted_allocation') or {}
            state = 'SETTLEMENT_RECORDED' if posting.get('liability', 0) < 0 else 'CLOSURE_ONGOING'
            evidence = row
        elif kind == 'SETTLEMENT_OR_TRANSFER_REVIEW':
            state, evidence = 'POSSIBLE_CLOSURE', row
        elif kind == 'LOAN_FUNDING_POSTED':
            state, evidence = 'OPEN', row
        elif kind == 'FUNDING_CANDIDATE':
            state, evidence = 'FUNDING_RECEIVED_REVIEW', row
        elif kind == 'DRAWDOWN_OR_TRANSFER_REVIEW' and state in ('CLOSURE_ONGOING', 'POSSIBLE_CLOSURE', 'SETTLEMENT_RECORDED'):
            state, evidence = 'FUNDING_RECEIVED_REVIEW', row
    return state, evidence


def posted_allocations(rows):
    """Group visible GL lines by voucher, retaining separate liability and cost components."""
    vouchers = {}
    for row in rows:
        key = (row['voucher_type'], row['voucher_no'])
        voucher = vouchers.setdefault(key, {'doctype': key[0], 'name': key[1], 'date': str(row['posting_date']),
                                            'nets': defaultdict(lambda: money(0)), 'remarks': []})
        voucher['nets'][row['account_number']] += money(row['debit']) - money(row['credit'])
        if row.get('remarks'):
            voucher['remarks'].append(row['remarks'])
    return list(vouchers.values())


def _has_reference(text, reference):
    return bool(re.fullmatch(r'\d{5,}', reference)
                and re.search(rf'(?<!\d){re.escape(reference)}(?!\d)', text))


def allocation_review(movements, transfer_credits, ledger_rows):
    """Produce review actions with bank and ledger evidence. Never construct a live voucher."""
    result = financing_status(movements)
    vouchers = posted_allocations(ledger_rows)
    candidates = {}
    claims = defaultdict(set)
    for row in result['movements']:
        amount = money(row['amount']) * (1 if row['direction'] == 'CREDIT' else -1)
        eligible = []
        for voucher in vouchers:
            nets = voucher['nets']
            if abs((date.fromisoformat(voucher['date']) - date.fromisoformat(row['date'])).days) > 3:
                continue
            referenced = any(_has_reference(text, ref) for text in voucher['remarks']
                             for ref in (row.get('bank_reference', ''), row.get('tawal_reference', '')))
            if nets.get('13124') != amount and not referenced:
                continue
            eligible.append({
                'name': voucher['name'], 'doctype': voucher['doctype'], 'date': voucher['date'],
                'bank': nets.get('13124', money(0)), 'other_bank': nets.get('13123', money(0)),
                'liability': -nets.get('221', money(0)), 'interest': nets.get('5151', money(0)),
                'fees': nets.get('538', money(0)), 'referenced': referenced,
            })
            if referenced or row.get('linked_voucher') == (voucher['doctype'], voucher['name']):
                claims[(voucher['doctype'], voucher['name'])].add(row['name'])
        candidates[row['name']] = eligible

    outgoing = Counter((r.get('bank_reference'), money(r['amount'])) for r in result['movements']
                       if r['classification'] == 'TRANSFER_TO_6605')
    for row in result['movements']:
        kind = row['classification']
        amount = money(row['amount']) * (1 if row['direction'] == 'CREDIT' else -1)
        eligible = candidates[row['name']]
        verified = [v for v in eligible if v['bank'] == amount and (
            v['referenced'] or row.get('linked_voucher') == (v['doctype'], v['name']))
            and len(claims[(v['doctype'], v['name'])]) == 1]
        row['vouchers'] = eligible
        row['allocation_status'] = 'VERIFY_ERP_CANDIDATE' if eligible else 'NEEDS_REVIEW'
        if row.get('linked_voucher') and not verified:
            row['allocation_status'] = 'VERIFY_LINKED_VOUCHER'
        if len(verified) == 1:
            row['posted_allocation'] = verified[0]
            row['allocation_status'] = 'POSTED'
        if kind == 'TRANSFER_TO_6605':
            match = match_unique_transfer({
                'source_tail': '3605', 'destination_tail': '6605', 'reference': row.get('bank_reference'),
                'date': row['date'], 'amount': abs(amount),
            }, transfer_credits)
            if outgoing[(row.get('bank_reference'), abs(amount))] > 1:
                match = {'status': 'REVIEW', 'reason': 'MULTIPLE_DEBITS_CLAIM_TRANSFER'}
            row['transfer_status'] = match['status']
            row['transfer_reason'] = match.get('reason')
            row['transfer_reference'] = (match.get('credit') or {}).get('reference')
            row['allocation_action'] = 'Reconcile one transfer from 13124 to 13123'
            if match['status'] == 'MATCHED' and not eligible and not row.get('linked_voucher') and not match['credit'].get('linked_voucher'):
                row['proposed_lines'] = [
                    {'account': '13123', 'debit': abs(amount), 'credit': money(0)},
                    {'account': '13124', 'debit': money(0), 'credit': abs(amount)},
                ]
            if match['status'] != 'MATCHED' or (verified and verified[0]['other_bank'] != -amount):
                row['allocation_status'] = 'VERIFY_TRANSFER_PAIR'
        elif kind == 'TAWAL_RECEIPT':
            row['allocation_action'] = 'Match the TAWAL payment and allocate invoices in the TAWAL tab using 13124'
        elif kind in ('SETTLEMENT_CANDIDATE', 'SETTLEMENT_OR_TRANSFER_REVIEW'):
            row['allocation_action'] = 'Match the facility and reconcile the debit to loan liability 221 and supported costs'
            if verified and verified[0]['liability'] >= 0:
                row['allocation_status'] = 'VERIFY_SETTLEMENT_ACCOUNTS'
        elif kind in ('FUNDING_CANDIDATE', 'DRAWDOWN_OR_TRANSFER_REVIEW'):
            row['allocation_action'] = 'Verify the financing source and reconcile liability 221 and any booked interest and commissions'
            if verified and verified[0]['liability'] > 0:
                row['classification'] = 'LOAN_FUNDING_POSTED'
        else:
            row['allocation_action'] = 'Identify the counter-account from the bank evidence'
    status, evidence = _latest_status(result['movements'])
    result.update(status=status, evidence=evidence)
    return result
