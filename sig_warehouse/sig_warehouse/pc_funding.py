"""Finance designation and employee-cycle projection for petty-cash funding."""

from datetime import date, timedelta
from hashlib import sha256

import frappe
from frappe.utils import cint


FINANCE_ROLES = {"System Manager", "Accounts User", "Accounts Manager"}
REVIEW_ROLES = FINANCE_ROLES | {"Operations User", "Operations Manager", "SIG PC Clearance"}
FUNDING_FIELDS = (
    "custom_pc_top_up", "custom_pc_transfer_category", "custom_pc_employee",
    "custom_pc_funding_date", "custom_pc_funding_source", "custom_pc_bank_txn_id",
    "custom_pc_bank_journal_number", "custom_pc_statement_key", "custom_pc_funding_source_key",
)


def _require_finance():
    roles = set(frappe.get_roles())
    if not roles.intersection(FINANCE_ROLES):
        frappe.throw("Only Finance can designate a Journal Entry as petty-cash funding.",
                     frappe.PermissionError)


def _active_employee(name, company):
    if not name:
        frappe.throw("Select the Employee funded by this Journal Entry.")
    row = frappe.db.get_value("Employee", name, ["status", "company", "custom_custody_account"], as_dict=True)
    if not row or row.status != "Active" or row.company != company or not row.custom_custody_account:
        frappe.throw("Select an active Employee in the same Company with a configured custody account.")
    currency = frappe.db.get_value("Company", company, "default_currency")
    account = frappe.db.get_value("Account", row.custom_custody_account,
                                 ["company", "disabled", "is_group", "root_type", "account_currency"], as_dict=True)
    if (currency != "SAR" or not account or account.company != company or account.disabled
            or account.is_group or account.root_type != "Asset" or account.account_currency != currency):
        frappe.throw("The Employee custody account must be an active SAR asset account in the Journal Entry Company.")
    parent = frappe.db.get_value("Account", row.custom_custody_account, "parent_account")
    seen = set()
    while parent and parent not in seen:
        seen.add(parent)
        number, parent = frappe.db.get_value("Account", parent, ["account_number", "parent_account"])
        if str(number) == "1322":
            return row.custom_custody_account
    frappe.throw("The Employee custody account must be under the approved 1322 ledger.")


def _fields_changed(doc, fields):
    before = doc.get_doc_before_save()
    if before is None:
        # Frappe fills Link fields from the current user's User Permissions on
        # insert. A reviewer's own Employee default is not a funding designation.
        before = frappe.new_doc(doc.doctype, as_dict=True)
    def value(record, field):
        raw = record.get(field)
        return cint(raw) if field == "custom_pc_top_up" else str(raw or "")
    return any(value(doc, field) != value(before, field) for field in fields)


def validate_journal_entry(doc, method=None):
    """Validate the manual top-up checkbox without changing accounting lines."""
    if _fields_changed(doc, FUNDING_FIELDS):
        _require_finance()
    if not cint(doc.get("custom_pc_top_up")):
        return
    _require_finance()
    if doc.docstatus == 2:
        frappe.throw("A cancelled Journal Entry cannot start a petty-cash cycle.")
    if not doc.get("custom_pc_funding_date"):
        frappe.throw("Funding Date is required for a petty-cash top-up.")
    source = doc.get("custom_pc_funding_source")
    if source not in ("Bank Statement", "Manual Finance"):
        frappe.throw("Choose Bank Statement or Manual Finance as the funding source.")
    if source == "Bank Statement":
        if not (doc.get("custom_pc_bank_txn_id") or doc.get("custom_pc_bank_journal_number")
                or doc.get("custom_pc_statement_key")):
            frappe.throw("A bank transaction ID, bank journal number or statement key is required for statement-backed funding.")

    custody = _active_employee(doc.get("custom_pc_employee"), doc.company)
    custody_lines = [row for row in doc.get("accounts", []) if row.account == custody]
    principal = sum(float(row.debit or 0) for row in custody_lines)
    custody_credit = sum(float(row.credit or 0) for row in custody_lines)
    bank_accounts = set(frappe.get_all("Account", filters={"company": doc.company,
                                 "account_type": "Bank", "disabled": 0, "is_group": 0},
                                 pluck="name", limit_page_length=0))
    bank_lines = [row for row in doc.get("accounts", []) if row.account in bank_accounts]
    bank_debit = sum(float(row.debit or 0) for row in bank_lines)
    bank_credit = sum(float(row.credit or 0) for row in bank_lines)
    if principal <= 0 or custody_credit > 0.005 or bank_debit > 0.005 or bank_credit + 0.005 < principal:
        frappe.throw("The Journal Entry must debit the Employee custody account and credit the company bank for at least the principal amount.")

    key = ("STATEMENT:" + str(doc.get("custom_pc_statement_key")).strip()
           if doc.get("custom_pc_statement_key") else
           "SNB:" + str(doc.get("custom_pc_bank_txn_id")).strip()
           if doc.get("custom_pc_bank_txn_id") else
           "BANK-JE:" + str(doc.get("custom_pc_bank_journal_number")).strip()
           if doc.get("custom_pc_bank_journal_number") else
           str(doc.get("custom_pc_funding_source_key") or "MANUAL:" + str(doc.name or frappe.generate_hash(length=16))))
    existing = frappe.db.get_value("Journal Entry", {
        "custom_pc_funding_source_key": key,
        "name": ["!=", doc.name or ""],
        "docstatus": ["<", 2],
    }, "name")
    if existing:
        frappe.throw("This funding source is already assigned to Journal Entry " + existing + ".")
    doc.custom_pc_funding_source_key = key


def prevent_funding_edits_after_submit(doc, method=None):
    before = doc.get_doc_before_save()
    if before and any(doc.get(field) != before.get(field) for field in FUNDING_FIELDS):
        frappe.throw("Petty-cash funding details on a submitted Journal Entry are locked. Use the Finance correction process.")


def _context():
    from sig_warehouse.sig_warehouse.pc_journal import _context as pc_context

    context = pc_context()
    if not context["roles"].intersection(REVIEW_ROLES):
        frappe.throw("You need an authorised petty-cash reviewer role.", frappe.PermissionError)
    return context


def _employee_for_report(employee_name, context):
    employee = next((e for e in context["employees"] if e.name == employee_name and e.status == "Active"), None)
    if not employee:
        frappe.throw("The selected Employee is not available.", frappe.PermissionError)
    if not context["roles"].intersection(FINANCE_ROLES):
        from sig_warehouse.sig_warehouse.pc_journal import _in_scope

        if not _in_scope(employee, context):
            frappe.throw("You are not assigned to this Employee's petty-cash records.", frappe.PermissionError)
    return employee


def _cycles(employee, context):
    employee = _employee_for_report(employee.name if hasattr(employee, "name") else employee, context)
    custody = employee.custom_custody_account
    journals = frappe.get_all(
        "Journal Entry",
        filters={"custom_pc_top_up": 1, "custom_pc_employee": employee.name,
                 "company": employee.company, "docstatus": ["<", 2]},
        fields=["name", "docstatus", "posting_date", "custom_pc_funding_date",
                "custom_pc_funding_source", "custom_pc_funding_source_key",
                "custom_pc_bank_txn_id", "custom_pc_bank_journal_number"],
        order_by="custom_pc_funding_date asc, name asc", limit_page_length=0,
    )
    principals = {}
    if journals:
        journal_names = [row.name for row in journals]
        placeholders = ",".join(["%s"] * len(journal_names))
        totals = frappe.db.sql(f"""select parent, sum(debit) as principal
            from `tabJournal Entry Account`
            where parent in ({placeholders}) and account=%s
            group by parent""", tuple(journal_names + [custody]),
            as_dict=True)
        principals = {row.parent: round(float(row.principal or 0), 2) for row in totals}
    result = []
    for row in journals:
        if row.custom_pc_funding_source == "Manual Finance" and row.docstatus != 1:
            continue
        principal = principals.get(row.name, 0)
        if principal <= 0:
            continue
        result.append({
            # The stable internal source key stays server-side. Return only a
            # deterministic opaque handle to the reviewer page.
            "cycle_key": sha256(str(row.custom_pc_funding_source_key or row.name).encode("utf-8")).hexdigest(),
            "funding_date": str(row.custom_pc_funding_date)[:10],
            "principal": principal,
            "journal_status": {0: "Pending Finance", 1: "Posted", 2: "Cancelled"}.get(row.docstatus, "Unknown"),
        })
    for idx, item in enumerate(result):
        next_distinct = next((other for other in result[idx + 1:]
                              if other["funding_date"] > item["funding_date"]), None)
        same_day_group = [other for other in result if other["funding_date"] == item["funding_date"]]
        last_on_day = item is same_day_group[-1]
        item["end_date"] = (
            str(date.fromisoformat(item["funding_date"]) - timedelta(days=1))
            if len(same_day_group) > 1 and not last_on_day else
            str(date.fromisoformat(next_distinct["funding_date"]) - timedelta(days=1))
            if next_distinct else None
        )
        item["open"] = next_distinct is None and last_on_day
        item["same_day_ambiguous"] = len(same_day_group) > 1
    return result


@frappe.whitelist(methods=["POST"])
def get_funding_cycles(employee):
    context = _context()
    resolved = _employee_for_report(employee, context)
    return _cycles(resolved, context)


def cycle_membership(row, cycles):
    tx_date = str(row.get("transaction_date") or "")[:10]
    if sum(1 for cycle in cycles if cycle["funding_date"] == tx_date) > 1:
        return {"cycle_key": None, "cycle_label": "Awaiting cycle allocation",
                "cycle_allocation_status": "Awaiting allocation"}
    matching = [cycle for cycle in cycles
                if cycle["funding_date"] <= tx_date and (not cycle["end_date"] or tx_date <= cycle["end_date"])]
    if not cycles or tx_date < cycles[0]["funding_date"]:
        return {"cycle_key": None, "cycle_label": "Before first recorded funding" if cycles else "No recorded funding",
                "cycle_allocation_status": "Before first funding" if cycles else "Funding not recorded"}
    if len(matching) != 1 or (matching and matching[0]["same_day_ambiguous"]):
        return {"cycle_key": None, "cycle_label": "Awaiting cycle allocation",
                "cycle_allocation_status": "Awaiting allocation"}
    cycle = matching[0]
    return {"cycle_key": cycle["cycle_key"],
            "cycle_label": "Cycle from " + cycle["funding_date"],
            "cycle_allocation_status": "Assigned"}
