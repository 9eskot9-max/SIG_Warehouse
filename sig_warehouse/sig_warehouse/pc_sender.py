"""Resolve pending petty-cash sender phones against ERP Employee records."""

import json
import re

import frappe


REVIEW_ROLES = {
    "System Manager",
    "Accounts User",
    "Accounts Manager",
    "Operations User",
    "Operations Manager",
    "SIG PC Clearance",
}


def _phone_key(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("05"):
        digits = "966" + digits[1:]
    elif len(digits) == 9 and digits.startswith("5"):
        digits = "966" + digits
    return digits if 9 <= len(digits) <= 15 else ""


@frappe.whitelist()
def resolve_pc_employee_senders(phone_numbers=None):
    """Return unique Employee primary or linked Contact matches for supplied phones.

    Callers must supply phone numbers already present on pending SIG PC Transactions.
    This API does not expose the employee directory to petty-cash reviewers.
    """
    if not REVIEW_ROLES.intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw("You need an authorised petty-cash reviewer role. [FINANCE_REVIEWER_REQUIRED]")

    if isinstance(phone_numbers, str):
        try:
            phone_numbers = json.loads(phone_numbers)
        except (TypeError, ValueError):
            phone_numbers = []
    if not isinstance(phone_numbers, (list, tuple)):
        phone_numbers = []

    requested = {_phone_key(value) for value in phone_numbers}
    requested.discard("")
    if not requested:
        return {}
    if len(requested) > 1000:
        frappe.throw("Too many sender phones were requested. [PC_SENDER_LOOKUP_LIMIT]")

    # Resolve only numbers represented by pending receipts. This keeps the API
    # aligned with its caller and prevents arbitrary Employee/Contact phone lookup.
    pending = frappe.get_list(
        "SIG PC Transaction",
        filters={"closure_status": ["in", ["Draft", "Needs Review"]]},
        fields=["employee_name"],
        limit_page_length=0,
    )
    pending_phone_keys = {_phone_key(row.employee_name) for row in pending}
    requested.intersection_update(pending_phone_keys)
    if not requested:
        return {}

    matches = {}

    def add_match(employee, phone):
        key = _phone_key(phone)
        label = str(employee.employee_name or "").strip()
        if key in requested and not label.lower().startswith("whatsapp sender "):
            matches.setdefault(key, {})[employee.name] = employee

    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name", "cell_number"],
        limit_page_length=0,
    )
    for employee in employees:
        add_match(employee, employee.cell_number)

    # ERPNext stores additional employee contact numbers on Contact documents,
    # joined through Dynamic Link. Emergency Phone is deliberately excluded.
    employee_by_name = {employee.name: employee for employee in employees}
    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Employee",
            "link_name": ["in", list(employee_by_name)],
            "parenttype": "Contact",
        },
        fields=["parent", "link_name"],
        limit_page_length=0,
    )
    employee_names_by_contact = {}
    for link in links:
        if link.link_name in employee_by_name:
            employee_names_by_contact.setdefault(link.parent, set()).add(link.link_name)
    if employee_names_by_contact:
        contact_phones = frappe.get_all(
            "Contact Phone",
            filters={
                "parent": ["in", list(employee_names_by_contact)],
                "parenttype": "Contact",
                "parentfield": "phone_nos",
            },
            fields=["parent", "phone"],
            limit_page_length=0,
        )
        for phone in contact_phones:
            for employee_name in employee_names_by_contact.get(phone.parent, ()):
                add_match(employee_by_name[employee_name], phone.phone)

    result = {}
    for key in requested:
        hits = list(matches.get(key, {}).values())
        if len(hits) == 1:
            result[key] = {
                "employee": hits[0].name,
                "employee_name": hits[0].employee_name,
            }
        elif len(hits) > 1:
            result[key] = {"ambiguous": True}
    return result
