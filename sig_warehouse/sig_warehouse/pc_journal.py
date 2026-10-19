"""One reviewer confirmation produces one native, unsubmitted clearance journal.

Account identities come from ERP configuration. No Supplier, PI or Payment Entry
is constructed. Frappe's normal Journal Entry create/validation path is retained.
"""

from pathlib import Path
import json

import frappe
from frappe.utils import get_datetime, now_datetime

from .pc_clearance_rules import CATEGORY_ACCOUNTS, journal_lines, legacy_cycle_period, money, request_digest, source_key
from .pc_review_routing import phone_index, phone_key


TRANSACTION = "SIG PC Transaction"
FINANCE = {"System Manager", "Accounts User", "Accounts Manager"}
REVIEWERS = FINANCE | {"Operations User", "Operations Manager", "SIG PC Clearance"}
EDIT_FIELDS = ("amount", "has_vat", "merchant", "supplier_vat_number", "invoice_number", "details")
FIELDS = ["name", "modified", "employee_name", "transaction_date", "amount", "purpose",
          "transaction_category", "has_vat", "vat_amount", "supplier_vat_number", "merchant",
          "invoice_number", "details", "source_id", "source_media_url"]


def _deny(message):
    frappe.throw(message, frappe.PermissionError)


def _context(user=None):
    user = user or frappe.session.user
    if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        _deny("Sign in with an enabled ERP reviewer account.")
    roles = set(frappe.get_roles(user))
    employees = frappe.get_all(
        "Employee", fields=["name", "employee_name", "status", "cell_number", "user_id",
                            "company", "custom_custody_account"], limit_page_length=0,
    )
    employees = [e for e in employees if not str(e.employee_name or "").casefold().startswith("whatsapp sender ")]
    actor = [e for e in employees if e.user_id == user and e.status == "Active"]
    scopes = json.loads(Path(__file__).with_name("pc_review_scopes.json").read_text(encoding="utf-8"))
    return {"user": user, "roles": roles, "employees": employees,
            "phones": phone_index(employees), "actor": actor[0] if len(actor) == 1 else None,
            "scopes": scopes}


def _resolve(sender, context):
    key = phone_key(sender)
    if key:
        hits = list(context["phones"].get(key, {}).values())
    else:
        label = " ".join(str(sender or "").casefold().split())
        hits = [e for e in context["employees"]
                if " ".join(str(e.employee_name or "").casefold().split()) == label]
    return hits[0] if len(hits) == 1 and hits[0].status == "Active" else None


def _in_scope(employee, context):
    actor = context["actor"]
    return bool(employee and actor and actor.name != employee.name
                and actor.name in context["scopes"]["employees"].get(employee.name, []))


def _authorize(doc, context):
    if not context["roles"].intersection(REVIEWERS):
        _deny("You need an authorised petty-cash reviewer role.")
    employee = _resolve(doc.employee_name, context)
    if not employee:
        frappe.throw("Sender must match exactly one active ERP Employee before confirmation.")
    if context["actor"] and context["actor"].name == employee.name:
        _deny("Your own receipts require an independent reviewer.")
    if not context["roles"].intersection(FINANCE) and not _in_scope(employee, context):
        _deny("You are not assigned to review this Employee's petty cash.")
    doc.check_permission("read")
    return employee


def transaction_query_conditions(user=None):
    """Scope native lists/counts/searches before pagination, using actual sender values."""
    context = _context(user)
    if context["roles"].intersection(FINANCE):
        return ""
    if not context["roles"].intersection(REVIEWERS):
        return "1=0"
    senders = frappe.get_all(TRANSACTION, fields=["employee_name"],
                             group_by="employee_name", limit_page_length=0)
    allowed = [row.employee_name for row in senders if _in_scope(_resolve(row.employee_name, context), context)]
    if not allowed:
        return "1=0"
    return "`tabSIG PC Transaction`.`employee_name` in ({})".format(
        ",".join(frappe.db.escape(value) for value in allowed)
    )


def transaction_permission(doc, user=None, permission_type=None):
    context = _context(user)
    if context["roles"].intersection(FINANCE):
        return None  # retain the full existing native permission matrix
    if not context["roles"].intersection(REVIEWERS):
        return False
    if not doc:
        return None
    if not _in_scope(_resolve(doc.employee_name, context), context):
        return False
    return None  # scope restricts; it never supplies a missing native ptype


@frappe.whitelist(methods=["POST"])
def pending_receipts():
    context = _context()
    if not context["roles"].intersection(REVIEWERS):
        _deny("You need an authorised petty-cash reviewer role.")
    return frappe.get_list(TRANSACTION, fields=FIELDS,
                           filters={"closure_status": ["in", ["Draft", "Needs Review"]]},
                           order_by="employee_name asc, transaction_date asc", limit_page_length=0)


def _locked_receipt(transaction_id):
    if not isinstance(transaction_id, str) or not transaction_id:
        frappe.throw("A receipt ID is required.")
    names = frappe.db.sql("select name from `tabSIG PC Transaction` where name=%s for update",
                          (transaction_id,))
    if not names:
        frappe.throw("Petty cash receipt was not found.")
    return frappe.get_doc(TRANSACTION, transaction_id)


def _values(doc, category, provided):
    values = {field: provided[field] if provided[field] is not None else doc.get(field)
              for field in EDIT_FIELDS}
    values["transaction_category"] = str(category or doc.transaction_category or "").strip()
    if values["transaction_category"] not in CATEGORY_ACCOUNTS:
        frappe.throw("Choose a valid petty-cash category.")
    try:
        values["amount"] = str(money(values["amount"]))
    except ValueError as exc:
        frappe.throw(str(exc))
    if str(values["has_vat"] or 0).lower() not in ("0", "1", "true", "false"):
        frappe.throw("VAT evidence flag must be yes or no.")
    values["has_vat"] = int(str(values["has_vat"] or 0).lower() in ("1", "true"))
    for field in EDIT_FIELDS[2:]:
        value = values[field] or ""
        if not isinstance(value, str) or len(value) > (2000 if field == "details" else 140):
            frappe.throw("Receipt text is invalid or too long: " + field)
        values[field] = value.strip()
    return values


def _accounts(employee, category):
    company = employee.company
    if not company or not employee.custom_custody_account:
        frappe.throw("Set Company and Custody Account on the ERP Employee before confirmation.")
    frappe.has_permission("Company", ptype="select", doc=company, throw=True)
    currency, cost_center = frappe.db.get_value("Company", company, ["default_currency", "cost_center"])
    if currency != "SAR":
        frappe.throw("This petty-cash clearance supports SAR accounts only.")
    expenses = frappe.get_all("Account", filters={"company": company, "is_group": 0,
                              "disabled": 0, "account_number": CATEGORY_ACCOUNTS[category]},
                              pluck="name", limit_page_length=2)
    if len(expenses) != 1:
        frappe.throw("The category must resolve to exactly one active expense account in the Company.")
    expense = frappe.get_doc("Account", expenses[0])
    custody = frappe.get_doc("Account", employee.custom_custody_account)
    if (custody.company != company or custody.disabled or custody.is_group
            or custody.account_type in ("Receivable", "Payable") or custody.root_type != "Asset"):
        frappe.throw("The Employee custody account must be an active asset leaf in the same Company.")
    parent = custody.parent_account
    seen = set()
    while parent and parent not in seen:
        seen.add(parent)
        number, parent = frappe.db.get_value("Account", parent, ["account_number", "parent_account"])
        if str(number) == "1322":
            break
    else:
        frappe.throw("The Employee custody account must be under the approved 1322 ledger.")
    if expense.root_type != "Expense" or expense.account_currency != currency or custody.account_currency != currency:
        frappe.throw("Expense and custody accounts must use the Company's SAR currency and correct classification.")
    if not cost_center or frappe.db.get_value("Cost Center", cost_center, "company") != company:
        frappe.throw("Set a valid Company cost center before confirmation.")
    return company, expense.name, custody.name, cost_center


@frappe.whitelist(methods=["POST"])
def confirm_receipt(transaction_id, expected_modified=None, transaction_category=None,
                    amount=None, has_vat=None, merchant=None, supplier_vat_number=None,
                    invoice_number=None, details=None):
    if not expected_modified:
        frappe.throw("Refresh the petty-cash review page before confirming this receipt.")
    context = _context()
    doc = _locked_receipt(transaction_id)
    employee = _authorize(doc, context)
    values = _values(doc, transaction_category, {
        "amount": amount, "has_vat": has_vat, "merchant": merchant,
        "supplier_vat_number": supplier_vat_number, "invoice_number": invoice_number, "details": details,
    })
    digest = request_digest(context["user"], doc.name, str(expected_modified), values)
    try:
        key = source_key(doc.source_id)
    except ValueError as exc:
        frappe.throw(str(exc))
    # Existing PI/PE clearances are a separate, explicitly reviewed conversion.
    if doc.purchase_invoice or doc.payment_entry:
        frappe.throw("This receipt already has invoice/payment documents. Finance must reconcile them before conversion.")
    if doc.journal_entry:
        journal = frappe.get_doc("Journal Entry", doc.journal_entry)
        if (journal.docstatus != 2 and journal.get("custom_pc_receipt") == doc.name
                and journal.get("custom_pc_request_digest") == digest):
            journal.check_permission("read")
            return {"ok": True, "existing": True, "journal_entry": journal.name,
                    "closure_status": doc.closure_status}
        frappe.throw("This receipt already has a journal. Reload its existing clearance; no new draft was created.")
    if doc.closure_status not in ("Draft", "Needs Review"):
        frappe.throw("Only pending receipts can be confirmed.")
    if get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw("This receipt changed after you opened it. Reload and review the latest version.")
    if not doc.source_media_url and not doc.sync_archive_locator:
        frappe.throw("The original receipt evidence must be linked before confirmation.")
    if frappe.db.exists("Journal Entry", {"custom_pc_source_key": key}):
        frappe.throw("A journal already owns this receipt source. Finance must resolve the duplicate.")
    company, expense, custody, cost_center = _accounts(employee, values["transaction_category"])
    frappe.db.sql("select name from `tabAccount` where name=%s for update", (custody,))
    # A legacy cycle export has no receipt IDs. Hold for reconciliation rather than guess overlap.
    legacy = frappe.db.sql("""select distinct je.name, je.user_remark from `tabJournal Entry` je
        inner join `tabJournal Entry Account` line on line.parent=je.name
        where line.account=%s and je.docstatus<2 and je.user_remark like %s""",
        (custody, "[SIGPC clearance]%"))
    for legacy_name, remark in legacy:
        try:
            start, end = legacy_cycle_period(remark)
        except ValueError as exc:
            frappe.throw(str(exc))
        if start <= str(doc.transaction_date)[:10] <= end:
            frappe.throw("An older cycle journal covers this receipt date. Finance must check overlap first: " + legacy_name)
    journal = frappe.get_doc({
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": company,
        "posting_date": doc.transaction_date, "custom_pc_receipt": doc.name,
        "custom_pc_source_key": key, "custom_pc_request_digest": digest,
        "user_remark": ("[SIGPC receipt clearance] " + str(doc.source_id) + "\nEmployee: "
                        + employee.name + " / " + employee.employee_name + "\nCategory: "
                        + values["transaction_category"] + "\nMerchant: " + values["merchant"]
                        + "\nInvoice: " + values["invoice_number"] + "\nVAT evidence: "
                        + ("Yes" if values["has_vat"] else "No") + " / " + values["supplier_vat_number"]
                        + "\nGross expense; Finance assesses VAT before submission.\n" + values["details"]),
        "accounts": journal_lines(values["amount"], expense, custody, cost_center),
    })
    journal.insert()  # native create, User Permissions, links and validation; never submit
    for field, value in values.items():
        doc.set(field, float(value) if field == "amount" else value)
    doc.vat_amount = round(float(values["amount"]) * 15 / 115, 2) if values["has_vat"] else 0
    doc.journal_entry, doc.journal_status = journal.name, "Draft"
    doc.closure_status, doc.reviewed_by, doc.reviewed_at = "Closed", context["user"], now_datetime()
    # This read-only review record is written only after the scope/version checks;
    # native accounting permission checks above are never bypassed.
    doc.save(ignore_permissions=True)
    return {"ok": True, "journal_entry": journal.name, "journal_status": "Draft", "closure_status": "Closed"}


@frappe.whitelist(methods=["POST"])
def reject_receipt(transaction_id, expected_modified=None, notes=None):
    context = _context()
    doc = _locked_receipt(transaction_id)
    _authorize(doc, context)
    if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw("Reload the receipt before rejecting it.")
    if doc.closure_status not in ("Draft", "Needs Review") or doc.journal_entry or doc.purchase_invoice or doc.payment_entry:
        frappe.throw("Only pending receipts without accounting documents can be rejected.")
    if not isinstance(notes, str) or not notes.strip() or len(notes) > 2000:
        frappe.throw("Enter a rejection reason of at most 2000 characters.")
    doc.closure_status, doc.closure_notes = "Rejected", notes.strip()
    doc.reviewed_by, doc.reviewed_at = context["user"], now_datetime()
    doc.save(ignore_permissions=True)
    return {"ok": True, "closure_status": "Rejected"}


def guard_legacy_cycle(doc, method=None):
    """Serialise the two known writers; never book both routes for one custodian."""
    if not str(doc.user_remark or "").startswith("[SIGPC clearance]"):
        return
    try:
        start, end = legacy_cycle_period(doc.user_remark)
    except ValueError as exc:
        frappe.throw(str(exc))
    for account in sorted({line.account for line in doc.accounts
                           if float(line.credit_in_account_currency or 0) > 0}):
        frappe.db.sql("select name from `tabAccount` where name=%s for update", (account,))
        overlap = frappe.db.sql("""select je.name from `tabJournal Entry` je
            inner join `tabJournal Entry Account` line on line.parent=je.name
            inner join `tabSIG PC Transaction` receipt on receipt.name=je.custom_pc_receipt
            where line.account=%s and je.docstatus<2
              and receipt.transaction_date between %s and %s limit 1""", (account, start, end))
        if overlap:
            frappe.throw("This custodian already uses ERP receipt clearance. Finance must reconcile the old cycle export before importing it.")
