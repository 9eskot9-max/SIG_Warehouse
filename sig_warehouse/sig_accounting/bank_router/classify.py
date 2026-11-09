"""Stage 3: what kind of money movement is this? Pure. First match wins."""

BANK_CHARGE = "BANK_CHARGE"
OWN_TRANSFER = "OWN_TRANSFER"
SPECIALIST = "SPECIALIST"
PETTY_CASH = "PETTY_CASH"
EMPLOYEE = "EMPLOYEE"
OTHER = "OTHER"
EXPENSE_PAYMENT = "EXPENSE_PAYMENT"
SUPPLIER_PAYMENT = "SUPPLIER_PAYMENT"
CUSTOMER_RECEIPT = "CUSTOMER_RECEIPT"

FEE_FAMILIES = {"BANK_FEE", "FEE_VAT"}
OTHER_DEBIT_FAMILIES = {"SADAD", "PAYROLL_FEE", "PAYROLL_BULK_FEE", "LG_OUTWARD", "SWIFT", "CHEQUE_OR_MANUAL", "UNKNOWN_FORMAT"}
TRANSFER_FORMATS = {"IPS_LOCAL", "INTERNAL_SNB", "LARGE_LOCAL"}
# Intents TX Manager records at initiation. XXPC is petty-cash funding.
EMPLOYEE_INTENTS = {"XXSL", "XXHR"}


def classify(direction, parser_family, signals, facts, intent="", mined_route=""):
    """Return the movement kind.

    facts: Counterparty facts {is_company, handler, is_employee, custody_account, expense_account}; {} when unknown.
    intent: the matched TX Manager category (XXPC...), or ''.
    mined_route: Am's proposed_route, used only as evidence for persons and employees.
    """
    facts = facts or {}
    family = str(parser_family or "").upper()
    own = signals.get("own_account") or facts.get("is_company")
    if family in FEE_FAMILIES:
        return BANK_CHARGE
    if direction == "CREDIT":
        if signals.get("adjustment") or family == "LG_OUTWARD":
            return OTHER
        if own:
            return OWN_TRANSFER
        if signals.get("tawal") or facts.get("handler"):
            return SPECIALIST
        if facts.get("is_employee"):
            return EMPLOYEE
        if signals.get("format") in TRANSFER_FORMATS:
            return CUSTOMER_RECEIPT
        return OTHER
    # DEBIT
    if own or mined_route == "JE_BANK_TRANSFER":
        return OWN_TRANSFER
    if signals.get("tawal") or facts.get("handler"):
        return SPECIALIST
    if intent == "XXPC":
        return PETTY_CASH
    if facts.get("is_employee") or str(mined_route).startswith("JE_EMPLOYEE") or intent in EMPLOYEE_INTENTS:
        return EMPLOYEE
    if family in OTHER_DEBIT_FAMILIES:
        return OTHER
    if facts.get("expense_account") or str(mined_route).startswith("JE_PERSON"):
        return EXPENSE_PAYMENT
    return SUPPLIER_PAYMENT


DRAFTABLE = {SUPPLIER_PAYMENT, CUSTOMER_RECEIPT, EXPENSE_PAYMENT}
IMPORTER_OWNED = {PETTY_CASH, EMPLOYEE}
DEFERRED_KINDS = {SPECIALIST, OTHER, OWN_TRANSFER}
