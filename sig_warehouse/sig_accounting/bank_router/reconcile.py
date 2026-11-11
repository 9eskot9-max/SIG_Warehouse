"""Stage 4: is there already an ERP document for this line? Pure: candidates come from the caller.

Never draft what already exists. Finance posts many bank lines by hand with no marker, so a ledger match
(same bank account, direction, amount, nearby date) is how those lines are found. A match found only on
amount and date may suggest a link; it never decides a party.
"""
import datetime as dt

WINDOW_DAYS = 5
TOLERANCE = 0.005


def _date(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _same_amount(a, b):
    return abs(abs(float(a)) - abs(float(b))) <= TOLERANCE


def payee_fit(movement, doc):
    """'ok' when the document's other side is this payee, 'other' when it is another payee, 'unknown' when it cannot be told.

    movement["payee"] = {"custody": ledger number, "supplier": Supplier id}; a Journal Entry carries "counter" (the numbers of
    its non-bank accounts) and a Payment Entry carries "party". Only like is compared with like.
    """
    payee = movement.get("payee") or {}
    custody, supplier = str(payee.get("custody") or ""), str(payee.get("supplier") or "")
    if custody and payee.get("verified_custody") and doc.get("counter") is not None and doc["doctype"] == "Journal Entry":
        if custody in doc["counter"]:
            return "ok"
        return "other" if any(str(account).startswith("1322") for account in doc["counter"]) else "unknown"
    if supplier and payee.get("verified_supplier") and doc.get("party") and doc["doctype"] == "Payment Entry":
        return "ok" if doc["party"] == supplier else "other"
    return "unknown"


def pick_document(movement, candidates, claimed=(), rejected=(), hint=None, window=WINDOW_DAYS):
    """Choose the document for one movement.

    movement: {key, amount (signed), date, reference, bank_account}.
    candidates: [{doctype, name, date, docstatus, amount (positive = money into the bank), reference, marker,
                  bank_account}] taken from the ledger around the movement's date.
    hint: Am's erp_doc candidate dict when it exists in ERP, else None.
    Returns (outcome, documents, method): outcome is LINK, PICK or NONE.
    """
    claimed, rejected = set(claimed), set(rejected)
    live = [c for c in candidates if c["docstatus"] != 2 and c["name"] not in rejected]
    for doc in live:
        if doc.get("marker") and doc["marker"] == movement["key"] and doc["name"] not in claimed and doc["bank_account"] == movement["bank_account"] and (doc["amount"] > 0) == (float(movement["amount"]) > 0) and _same_amount(doc["amount"], movement["amount"]):
            return "LINK", [doc], "MARKER"
    if hint and hint["docstatus"] != 2 and hint["name"] not in rejected and hint["name"] not in claimed and payee_fit(movement, hint) != "other" \
            and (hint["amount"] > 0) == (float(movement["amount"]) > 0) and _same_amount(hint["amount"], movement["amount"]) and hint.get("bank_account") == movement["bank_account"]:
        return "LINK", [hint], "AM_LINK"
    day = _date(movement["date"])
    near = [c for c in live
            if c["name"] not in claimed
            and c["bank_account"] == movement["bank_account"]
            and (c["amount"] > 0) == (float(movement["amount"]) > 0)
            and _same_amount(c["amount"], movement["amount"])
            and abs((_date(c["date"]) - day).days) <= window]
    # Another payee's document is never offered, however close its amount and date.
    near = [c for c in near if payee_fit(movement, c) != "other"]
    if not near:
        return "NONE", [], ""
    # One document on the very same day whose other side is this payee: it is this line's document.
    exact = [c for c in near if _date(c["date"]) == day and payee_fit(movement, c) == "ok"]
    if len(exact) == 1 and (movement.get("unique_statement_amount") or movement.get("unique_statement_payee")):
        return "LINK", exact, "LEDGER"
    return "PICK", near, "LEDGER"


def fee_total_match(main_candidate_lines, fee_total, bank_account):
    """True when the document that carries the main line also has a bank line equal to the summed fee lines."""
    return any(line["bank_account"] == bank_account and _same_amount(line["amount"], fee_total)
               for line in main_candidate_lines)
