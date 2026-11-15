"""Accounting rules for receipt clearance. No posting, account lookup or permissions."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re
from datetime import date


CATEGORY_ACCOUNTS = {
    "Fuel/Disel": "51315", "Hotel Rent": "5148", "Food expenses": "5150",
    "Equipment Rental": "5123", "Car Maintanence": "51312",
    "Construction/Operational Material": "5121", "Vehicle OIL change": "51312",
    "Vehicle Other Misc.": "5126", "Drinking water": "5150", "Medical expenses": "518",
    "Phone bill": "517", "Trailer Rent": "51313", "Dyna Rent": "51313",
    "Work Labor": "5124", "Car Spare Parts": "51312", "Others": "5126",
    "Air-Ticket": "5147", "Bus Ticket": "5147", "Fax": "5126", "Iqama fees": "5145",
    "Office rental": "5411", "Stationaries": "523", "Taxi": "5131", "Train ticket": "5147",
    "VISA fees": "5145", "Xerox Copy": "523", "Fork Lift Rent": "5123",
    "Pickup Rent": "51311", "Office - Housekeeping": "543", "Warehouse misc.": "5149",
}


def money(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Enter a positive receipt amount with at most two decimal places.")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("999999999.99"):
            raise ValueError("Receipt amount is outside the supported range.")
        rounded = amount.quantize(Decimal("0.01"))
        if amount != rounded:
            raise ValueError("Receipt amount must have at most two decimal places.")
        return rounded
    except InvalidOperation as exc:
        raise ValueError("Enter a valid receipt amount.") from exc


def request_digest(user, receipt, modified, values):
    encoded = json.dumps([user, receipt, modified, values], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_key(source_id):
    if not str(source_id or "").strip():
        raise ValueError("The receipt has no stable source ID.")
    return hashlib.sha256(str(source_id).strip().encode("utf-8")).hexdigest()


def legacy_cycle_period(remark):
    """The existing hub stores ISO cycle bounds in its SIG-PC idempotency key."""
    key = str(remark or "").partition("| ")[2]
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", key)
    if not key.startswith("SIG-PC-") or len(dates) != 2:
        raise ValueError("Legacy clearance cycle dates need Finance reconciliation.")
    start, end = (date.fromisoformat(value) for value in dates)
    if start > end:
        raise ValueError("Legacy clearance cycle dates are reversed.")
    return start.isoformat(), end.isoformat()


def inclusive_vat(amount):
    return (money(amount) * Decimal('15') / Decimal('115')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def journal_lines(amount, expense_account, custody_account, cost_center,
                  vat_account=None, vat_amount=0):
    """Split evidenced recoverable VAT from the gross receipt amount."""
    total = money(amount)
    if not expense_account or not custody_account or expense_account == custody_account:
        raise ValueError("Expense and employee custody accounts must be configured separately.")
    if not cost_center:
        raise ValueError("A company cost center is required for the expense line.")
    tax = money(vat_amount) if vat_amount else Decimal("0.00")
    if tax and (not vat_account or tax >= total or vat_account in (expense_account, custody_account)):
        raise ValueError("A valid input VAT account and an amount below the receipt total are required.")
    lines = [{"account": expense_account, "debit_in_account_currency": float(total - tax),
         "credit_in_account_currency": 0, "cost_center": cost_center},
    ]
    if tax:
        lines.append({"account": vat_account, "debit_in_account_currency": float(tax),
                      "credit_in_account_currency": 0, "cost_center": cost_center})
    lines.append({"account": custody_account, "debit_in_account_currency": 0,
                  "credit_in_account_currency": float(total)})
    return lines


def compile_scopes(matrix):
    """Compile the approved roster into stable, independent reviewer Employee IDs."""
    by_name, employees = {}, {}
    for row in matrix["employees"]:
        employee = row["employee"]
        name = " ".join(row["employee_name"].casefold().split())
        if employee in employees or name in by_name:
            raise ValueError("Duplicate Employee identity in PC assignment source.")
        employees[employee] = row
        by_name[name] = employee
    profiles = {}
    for employee, row in employees.items():
        groups = [row["pc_review_group"], *row.get("additional_review_groups", [])]
        reviewers = [name for group in groups for name in matrix["review_groups"][group]["reviewers"]]
        ids = {by_name[" ".join(name.casefold().split())] for name in reviewers}
        ids.discard(employee)
        if not ids:
            raise ValueError("No independent reviewer for " + employee)
        profiles[employee] = sorted(ids)
    return {"revision": matrix["routing_version"], "employees": profiles}
