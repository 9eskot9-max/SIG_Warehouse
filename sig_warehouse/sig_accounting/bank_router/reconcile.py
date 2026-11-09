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
        if doc.get("marker") and doc["marker"] == movement["key"]:
            return "LINK", [doc], "MARKER"
    if hint and hint["docstatus"] != 2 and hint["name"] not in rejected and hint["name"] not in claimed \
            and _same_amount(hint["amount"], movement["amount"]) and hint.get("bank_account") == movement["bank_account"]:
        return "LINK", [hint], "AM_LINK"
    day = _date(movement["date"])
    near = [c for c in live
            if c["name"] not in claimed
            and c["bank_account"] == movement["bank_account"]
            and (c["amount"] > 0) == (float(movement["amount"]) > 0)
            and _same_amount(c["amount"], movement["amount"])
            and abs((_date(c["date"]) - day).days) <= window]
    if not near:
        return "NONE", [], ""
    if len(near) == 1:
        return "LINK", near, "LEDGER"
    by_reference = [c for c in near if movement.get("reference") and str(c.get("reference") or "").strip() == movement["reference"]]
    if len(by_reference) == 1:
        return "LINK", by_reference, "LEDGER"
    same_day = [c for c in near if _date(c["date"]) == day]
    if len(same_day) == 1:
        return "LINK", same_day, "LEDGER"
    return "PICK", near, "LEDGER"


def fee_total_match(main_candidate_lines, fee_total, bank_account):
    """True when the document that carries the main line also has a bank line equal to the summed fee lines."""
    return any(line["bank_account"] == bank_account and _same_amount(line["amount"], fee_total)
               for line in main_candidate_lines)
