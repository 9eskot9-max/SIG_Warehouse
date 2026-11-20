"""Pure Tawal payment planning for the bank router (no Frappe import; fully unit-testable).

Server-side port of ERPNext/scripts/tawal/tawal_erpnext_payload.mjs, restructured for the router:
one portal payment becomes one row with a state, any bank credit and existing Payment Entry,
and, when supported, a draft Payment Entry. Cleared portal payments can be reviewed without a
bank feed; a person must supply the receiving account and date for that draft.
"""
import re
from datetime import date

COMPANY = "Salah Ibrahim Algain Contracting Company Ltd"
TAWAL_CUSTOMER = "Telecommunications Towers Company / Tawal"
COST_CENTER = "Main - SIG"
MODE_OF_PAYMENT = "Wire Transfer"

# Bank GL by the tail of the SNB account the credit actually landed in (never by the Tawal remit-to fallback).
BANK_GL_BY_TAIL = {"0109": "13121", "6605": "13123", "3605": "13124"}
# Tawal remit-to account -> SNB account tail, used only for matching unreferenced credits.
TAIL_BY_REMIT = {"23659568000109": "0109", "01400010326605": "6605", "81300000023605": "3605"}

CLEARED = {"CLEARED", "PAID", "COMPLETED"}
VOIDED = {"VOIDED", "VOID", "STOP INITIATED", "CANCELLED", "CANCELED"}
MULTI_RE = re.compile(r"^(multiple|none|various)$", re.I)
EXACT_WINDOW_DAYS = 10
REFERENCED_WINDOW_DAYS = 45  # a credit that names the payment number may land after a slow clearance
POSSIBLE_RECEIPT_DAYS = 7
AMOUNT_DATE_DAYS = 10  # same amount this close to the portal date = that payment's receipt (old entries carry the bank reference)

# Row states
READY, UNLINKED_READY, BANK_RECEIVED = "READY", "UNLINKED_READY", "BANK_RECEIVED"
WAITING_BANK, HOLD_REVIEW, POSSIBLE_EXISTING = "WAITING_BANK", "HOLD_REVIEW", "POSSIBLE_EXISTING"
DRAFT, POSTED, LEGACY, VOID = "DRAFT", "POSTED", "LEGACY", "VOID"
UNALLOCATED = "UNALLOCATED"  # receipt exists and is posted, but its money is not allocated to invoices
ACTION_STATES = {READY, UNLINKED_READY, BANK_RECEIVED, HOLD_REVIEW, POSSIBLE_EXISTING, UNALLOCATED}


def canonical_invoice(value):
    """Portal invoice label -> ERP Sales Invoice name. Handles R re-issues, -1/-F ERP copies and PAC/FAC/Retention tails."""
    s = str(value or "").strip()
    m = re.search(r"\bSIG-SINV-\d{2}-\d+(?=R?\b)", s, re.I)
    if m:
        return m.group(0).upper()
    m = re.match(r"^INV_SIG__\d+", s, re.I)
    if m:
        return m.group(0).upper()
    return re.sub(r"\s*/\s*(?:revised\s+)?(?:pac|fac|retention).*$", "", s, flags=re.I).strip()


def classify_child(label, kind=""):
    text = f"{label or ''} {kind or ''}".lower()
    if re.search(r"\bretention\b", text):
        return "RETENTION"
    if re.search(r"credit\s*memo", text):
        return "CREDIT_MEMO"
    if re.search(r"\b(?:revised\s+)?pac\b", text):
        return "PAC"
    if re.search(r"\b(?:revised\s+)?fac\b", text):
        return "FAC"
    return "MAIN"


def references_payment(text, payment_number):
    """The bank prints the portal payment number ("CRF:202601001526"); that is exact proof, unlike amount+date."""
    num = str(payment_number or "").strip()
    if len(num) < 8:
        return False
    return re.search(rf"(?<!\d){re.escape(num)}(?!\d)", str(text or "")) is not None


def _days(a, b):
    try:
        return abs((date.fromisoformat(str(a)[:10]) - date.fromisoformat(str(b)[:10])).days)
    except ValueError:
        return 10**6


def match_credit(payment, credits, used=frozenset()):
    """credits: dicts with name, event_date, amount, tail, text, erp_document. Returns (credit|None, by_reference, issue)."""
    amount = float(payment["amount"])
    tail = TAIL_BY_REMIT.get(re.sub(r"\D", "", str(payment.get("remit_account") or "")))
    pool = []
    for c in credits:
        if c["name"] in used or c.get("erp_document"):
            continue
        if abs(abs(float(c["amount"])) - amount) > 0.01:
            continue
        referenced = references_payment(c.get("text"), payment["payment_number"])
        if not referenced and (c.get("tail") == "3605" or (tail and c.get("tail") != tail)):
            continue
        window = REFERENCED_WINDOW_DAYS if referenced else EXACT_WINDOW_DAYS
        if _days(c["event_date"], payment["payment_date"]) <= window:
            pool.append((c, referenced))
    if not pool:
        return None, False, "NO_BANK_CREDIT"
    refd = [c for c, r in pool if r]
    if len(refd) == 1:
        return refd[0], True, ""
    if len(refd) > 1:
        return None, False, "BANK_CREDIT_AMBIGUOUS"
    if len(pool) == 1:
        return pool[0][0], pool[0][1], ""
    exact = [c for c, _ in pool if _days(c["event_date"], payment["payment_date"]) == 0]
    if len(exact) == 1:
        return exact[0], False, ""
    return None, False, "BANK_CREDIT_AMBIGUOUS"


def claim_entries(payments, entries):
    """{payment_number: (entry, how)}: by reference_no first, then by amount + date when the pairing is unique both ways."""
    claimed, used = {}, set()
    ordered = sorted(payments, key=lambda p: (str(p["payment_date"]), p["payment_number"]))
    by_ref = {}
    for e in entries:
        if e.get("reference_no"):
            by_ref.setdefault(str(e["reference_no"]).strip(), e)
    for p in ordered:
        e = by_ref.get(p["payment_number"])
        if e and e["name"] not in used:
            claimed[p["payment_number"]] = (e, "reference")
            used.add(e["name"])
    cands = {}
    for p in ordered:
        if p["payment_number"] not in claimed:
            cands[p["payment_number"]] = [e for e in entries if e["name"] not in used and abs(float(e.get("paid_amount") or 0) - float(p["amount"])) <= 0.005
                                          and _days(e["posting_date"], p["payment_date"]) <= AMOUNT_DATE_DAYS]
    wanted = {}
    for lst in cands.values():
        for e in lst:
            wanted[e["name"]] = wanted.get(e["name"], 0) + 1
    for num, lst in cands.items():
        if len(lst) == 1 and wanted[lst[0]["name"]] == 1:
            claimed[num] = (lst[0], "amount_date")
    return claimed


def _child(label, amount, kind, erp_doc, source):
    amount = float(amount or 0)
    line = classify_child(label, kind)
    return {"invoice_raw": str(label or "").strip(), "canonical": canonical_invoice(label), "erp_doc": erp_doc or "",
            "line_kind": line, "amount": amount, "source": source,
            "is_credit": amount < 0 or line in ("RETENTION", "CREDIT_MEMO")}


def resolve_children(payment, invoices, erp_index):
    """Every invoice variant this parent pays: portal detail rows if drilled, else the invoice export joined on payment number."""
    num = payment["payment_number"]
    detail = (payment.get("reconcile") or {}).get("allocation_rows") or []
    if detail:
        kids = [_child(d.get("invoice_number") or d.get("invoice"), d.get("paid_amount", d.get("amount")), d.get("type"),
                       (erp_index.get(canonical_invoice(d.get("invoice_number") or d.get("invoice"))) or {}).get("name"), "PORTAL_DETAIL")
                for d in detail]
    elif MULTI_RE.match(str(payment.get("invoice_raw") or "")):
        kids = [_child(i["invoice_number"], i["amount"], i.get("type"), (erp_index.get(i["canonical"]) or {}).get("name"), "INVOICE_EXPORT")
                for i in invoices if str(i.get("payment_number") or "") == num]
    else:
        canon = canonical_invoice(payment.get("invoice_raw"))
        rows = [i for i in invoices if i["canonical"] == canon]
        exact = [i for i in rows if str(i.get("payment_number") or "") == num]
        chosen = exact or rows
        kids = [_child(i["invoice_number"], i["amount"], i.get("type"), (erp_index.get(i["canonical"]) or {}).get("name"), "INVOICE_EXPORT")
                for i in chosen] or ([_child(payment.get("invoice_raw"), payment["amount"], "", (erp_index.get(canon) or {}).get("name"), "NAME_ONLY")] if canon else [])
    seen, out = set(), []
    for k in kids:
        key = (k["invoice_raw"], k["amount"])
        if key not in seen:
            seen.add(key)
            out.append(k)
    return out


def build_allocations(children):
    """Signed portal children -> positive ERP references. A labelled negative Retention nets into its own invoice;
    any other credit is a penalty and goes to review. Returns (issue, references, missing_invoices)."""
    if any(c["is_credit"] and c["line_kind"] != "RETENTION" for c in children):
        return "PENALTY_CREDIT_NOTE_REVIEW", [], []
    if any(c["line_kind"] == "RETENTION" and not c["amount"] < 0 for c in children):
        return "RETENTION_OFFSET_INVALID", [], []
    std, ret = {}, {}
    for c in children:
        if not c["canonical"]:
            return "INVOICE_NUMBER_MISSING", [], []
        if c["line_kind"] == "RETENTION":
            ret[c["canonical"]] = ret.get(c["canonical"], 0) + c["amount"]
        elif not c["is_credit"]:
            cur = std.setdefault(c["canonical"], {"amount": 0.0, "erp": set(), "raw": c["invoice_raw"]})
            cur["amount"] += c["amount"]
            if c["erp_doc"]:
                cur["erp"].add(c["erp_doc"])
    if any(k not in std for k in ret):
        return "RETENTION_ASSOCIATION_REVIEW", [], []
    refs, missing = [], []
    for canon, cur in std.items():
        allocated = cur["amount"] + ret.get(canon, 0)
        if not allocated > 0:
            return "RETENTION_NET_INVALID", [], []
        if len(cur["erp"]) > 1:
            return "INVOICE_AMBIGUOUS", [], []
        if not cur["erp"]:
            missing.append(canon)
            continue
        refs.append({"reference_doctype": "Sales Invoice", "reference_name": next(iter(cur["erp"])), "allocated_amount": round(allocated, 2),
                     "retention_offset": round(ret.get(canon, 0), 2)})
    return "", refs, missing


def _body(payment, credit, refs, missing, paid_from, tail, kind_note):
    gl = BANK_GL_BY_TAIL.get(tail or "")
    names = [r["reference_name"] for r in refs]
    offsets = [f"{r['reference_name']}: offset {r['retention_offset']:.2f}" for r in refs if r["retention_offset"]]
    remarks = f"Tawal payment {payment['payment_number']}; "
    remarks += f"invoices {', '.join(names)}; " if names else ""
    if missing:
        remarks += f"invoice(s) not present in ERP: {', '.join(missing)}; "
    remarks += (f"SNB {credit['name']}" if credit.get('name') else "TAWAL cleared; bank receipt requires reconciliation") + (f"; retention {' | '.join(offsets)}" if offsets else "") + (f"; {kind_note}" if kind_note else "")
    return {"doctype": "Payment Entry", "payment_type": "Receive", "company": COMPANY, "posting_date": str(credit["event_date"])[:10],
            "mode_of_payment": MODE_OF_PAYMENT, "party_type": "Customer", "party": TAWAL_CUSTOMER, "paid_from": paid_from, "paid_to_gl": gl,
            "paid_amount": float(payment["amount"]), "received_amount": float(payment["amount"]), "reference_no": payment["payment_number"],
            "reference_date": str(payment["payment_date"])[:10], "cost_center": COST_CENTER, "custom_remarks": 1, "remarks": remarks,
            "references": [{k: v for k, v in r.items() if k != "retention_offset"} for r in refs]}


def plan_payment(payment, invoices, erp_index, credits, entries, *, settings, default_receivable, used_credits=frozenset(), claimed=None, manual_receipt=None):
    """One row for one portal payment. See module docstring; never writes anything."""
    num = payment["payment_number"]
    base = {"payment_number": num, "payment_date": str(payment["payment_date"])[:10], "amount": float(payment["amount"]),
            "portal_status": payment.get("portal_status") or "", "invoice_raw": payment.get("invoice_raw") or "",
            "state": HOLD_REVIEW, "reason": "", "credit": None, "by_reference": False, "entry": None, "body": None, "can_draft": False,
            "mode": "", "missing_invoices": [], "possible_entries": [], "entry_match": ""}
    if claimed is None:
        claimed = claim_entries([payment], entries).get(num)
    if claimed:
        entry, how = claimed
        posted = int(entry.get("docstatus") or 0) == 1
        unallocated = float(entry.get("unallocated_amount") or 0) > 0.5
        base.update(state=DRAFT if not posted else UNALLOCATED if unallocated else POSTED, entry=entry["name"], entry_match=how,
                    reason="UNALLOCATED" if unallocated else "")
        return base
    status = str(payment.get("portal_status") or "").upper()
    if status in VOIDED:
        return {**base, "state": VOID, "reason": "PAYMENT_VOIDED"}
    if str(payment["payment_date"])[:10] < settings["legacy_before"]:
        return {**base, "state": LEGACY, "reason": "BEFORE_FORWARD_DATE"}
    credit, by_ref, issue = match_credit(payment, credits, used_credits)
    if not credit:
        occupied = [c for c in credits if (c["name"] in used_credits or c.get("erp_document"))
                    and abs(abs(float(c["amount"])) - base["amount"]) <= 0.01
                    and _days(c["event_date"], payment["payment_date"]) <= REFERENCED_WINDOW_DAYS
                    and (references_payment(c.get("text"), num) or _days(c["event_date"], payment["payment_date"]) <= EXACT_WINDOW_DAYS)]
        if occupied:
            return {**base, "state": HOLD_REVIEW, "reason": "BANK_CREDIT_ALREADY_LINKED"}
        if status not in CLEARED or issue != "NO_BANK_CREDIT":
            return {**base, "state": WAITING_BANK, "reason": issue}
        if not manual_receipt:
            return {**base, "state": HOLD_REVIEW, "reason": "CLEARED_BANK_DETAILS_REQUIRED"}
        if manual_receipt.get("tail") not in BANK_GL_BY_TAIL or not manual_receipt.get("date"):
            return {**base, "state": HOLD_REVIEW, "reason": "BANK_GL_UNMAPPED"}
        credit = {"name": None, "event_date": manual_receipt["date"], "tail": manual_receipt["tail"]}
    base.update(credit=credit["name"], by_reference=by_ref)
    amount = base["amount"]
    possible = [e["name"] for e in entries if abs(float(e.get("paid_amount") or 0) - amount) <= 0.005 and _days(e["posting_date"], credit["event_date"]) <= POSSIBLE_RECEIPT_DAYS]
    if possible:
        return {**base, "state": POSSIBLE_EXISTING, "reason": "POSSIBLE_EXISTING_RECEIPT", "possible_entries": possible}
    tail = credit.get("tail")
    if tail not in BANK_GL_BY_TAIL:
        return {**base, "state": HOLD_REVIEW, "reason": "BANK_GL_UNMAPPED"}
    cleared = status in CLEARED
    # A referenced bank credit remains useful when the portal status has not yet changed.
    if not cleared and not (by_ref and settings["allow_bank_reference"]):
        return {**base, "state": BANK_RECEIVED, "reason": "PORTAL_NOT_RECONCILED" if cleared else "PORTAL_NOT_CLEARED"}
    children = resolve_children(payment, invoices, erp_index)
    if not children:
        return {**base, "state": HOLD_REVIEW, "reason": "INVOICE_DETAILS_REQUIRED"}
    issue, refs, missing = build_allocations(children)
    if issue:
        return {**base, "state": HOLD_REVIEW, "reason": issue}
    if abs(sum(c["amount"] for c in children) - amount) > 0.02:
        return {**base, "state": HOLD_REVIEW, "reason": "ALLOCATION_TOTAL_MISMATCH"}
    receivable = default_receivable
    alloc_total = sum(r["allocated_amount"] for r in refs)
    if refs:
        invs = [erp_index[canonical_invoice(r["reference_name"])] if canonical_invoice(r["reference_name"]) in erp_index else None for r in refs]
        if any(i is None for i in invs):
            return {**base, "state": HOLD_REVIEW, "reason": "ERP_INDEX_INCONSISTENT"}
        if any(i["docstatus"] != 1 or i["customer"] != TAWAL_CUSTOMER for i in invs):
            return {**base, "state": HOLD_REVIEW, "reason": "INVOICE_NOT_SUBMITTED_TAWAL"}
        if len({i["debit_to"] for i in invs}) > 1:
            return {**base, "state": HOLD_REVIEW, "reason": "MIXED_RECEIVABLE_ACCOUNTS"}
        if any(r["allocated_amount"] > i["outstanding_amount"] + 0.01 for r, i in zip(refs, invs)):
            return {**base, "state": HOLD_REVIEW, "reason": "INVOICE_ALREADY_SETTLED"}
        receivable = invs[0]["debit_to"]
        for r, i in zip(refs, invs):
            r.update(total_amount=i["grand_total"], outstanding_amount=i["outstanding_amount"])
    if not missing and refs and abs(alloc_total - amount) <= 0.02:
        body = _body(payment, credit, refs, [], receivable, tail, "")
        return {**base, "state": READY, "mode": "allocated", "can_draft": True, "body": body, "paid_from": receivable}
    # Invoices are not (all) in ERP (legacy / pre-ERP): the money is real, so draft the receipt unlinked, naming the invoices.
    legacy_names = sorted({c["canonical"] for c in children if not c["is_credit"] and c["canonical"] and c["canonical"] not in {r["reference_name"] for r in refs}}) or missing
    if refs and abs(alloc_total - amount) > 0.02 and not missing:
        return {**base, "state": HOLD_REVIEW, "reason": "ALLOCATION_TOTAL_MISMATCH"}
    body = _body(payment, credit, [], legacy_names, receivable, tail, "UNLINKED: allocate in Payment Reconciliation")
    return {**base, "state": UNLINKED_READY, "mode": "unlinked", "can_draft": True, "body": body, "paid_from": receivable,
            "missing_invoices": legacy_names}


def plan_all(payments, invoices, erp_index, credits, entries, *, settings, default_receivable, manual_receipts=None):
    """Plan every payment oldest-first so one credit is never offered to two payments."""
    claims = claim_entries(payments, entries)
    taken = {e["name"] for e, _how in claims.values()}
    free = [e for e in entries if e["name"] not in taken]  # only unclaimed entries can be a "similar receipt"
    used, rows = set(), []
    for p in sorted(payments, key=lambda p: (str(p["payment_date"]), p["payment_number"])):
        row = plan_payment(p, invoices, erp_index, credits, free, settings=settings, default_receivable=default_receivable,
                           used_credits=frozenset(used), claimed=claims.get(p["payment_number"]) or False,
                           manual_receipt=(manual_receipts or {}).get(p["payment_number"]))
        if row["credit"]:
            used.add(row["credit"])
        rows.append(row)
    return rows
