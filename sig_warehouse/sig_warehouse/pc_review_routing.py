"""Shared petty-cash sender-to-review-group routing.

This module is the single routing source for task assignment now and the
future invoice-access policy. It does not grant access and exposes no API.
"""

import json
import re
from pathlib import Path

import frappe


def load_matrix():
    path = Path(__file__).with_name("pc_review_assignments.json")
    matrix = json.loads(path.read_text(encoding="utf-8-sig"))
    if matrix.get("phase") != "task_assignment_only":
        frappe.throw("PC review matrix is not marked for task assignment. [PC_MATRIX_PHASE_INVALID]")
    return matrix


def phone_key(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("05"):
        digits = "966" + digits[1:]
    elif len(digits) == 9 and digits.startswith("5"):
        digits = "966" + digits
    return digits if 9 <= len(digits) <= 15 else ""


def active_employees():
    return frappe.get_all(
        "Employee", filters={"status": "Active"},
        fields=["name", "employee_name", "cell_number", "user_id"],
        limit_page_length=0,
    )


def phone_index(employees):
    """Index unique real Employees by primary and Employee-linked Contact phones."""
    real = {
        employee.name: employee for employee in employees
        if not str(employee.employee_name or "").casefold().startswith("whatsapp sender ")
    }
    matches = {}

    def add(employee, phone):
        key = phone_key(phone)
        if key:
            matches.setdefault(key, {})[employee.name] = employee

    for employee in real.values():
        add(employee, employee.cell_number)
    if not real:
        return matches

    links = frappe.get_all(
        "Dynamic Link", filters={"link_doctype": "Employee",
                                 "link_name": ["in", list(real)],
                                 "parenttype": "Contact"},
        fields=["parent", "link_name"], limit_page_length=0,
    )
    by_contact = {}
    for link in links:
        by_contact.setdefault(link.parent, set()).add(link.link_name)
    if by_contact:
        phones = frappe.get_all(
            "Contact Phone", filters={"parent": ["in", list(by_contact)],
                                      "parenttype": "Contact", "parentfield": "phone_nos"},
            fields=["parent", "phone"], limit_page_length=0,
        )
        for phone in phones:
            for employee_id in by_contact.get(phone.parent, ()):
                add(real[employee_id], phone.phone)
    return matches


def resolve_sender(sender, matrix, employees, indexed_phones=None):
    """Resolve a receipt sender to its Employee ID and review-group key.

    Unknown, ambiguous, inactive, synthetic, and not-yet-configured senders
    fall back to the Finance-owned ``unassigned`` group. Employee IDs in the
    matrix take precedence over legacy Source Manager values.
    """
    indexed_phones = indexed_phones if indexed_phones is not None else phone_index(employees)
    hits = list(indexed_phones.get(phone_key(sender), {}).values())
    default_group = matrix["default_review_group"]
    if len(hits) != 1:
        status = "ambiguous" if len(hits) > 1 else "unmatched"
        return {"employee": None, "employee_name": None, "user_id": None,
                "group": default_group, "status": status,
                "matrix_version": matrix.get("routing_version")}

    employee = hits[0]
    assignments = {row["employee"]: row for row in matrix["employees"]}
    assignment = assignments.get(employee.name)
    group = assignment.get("pc_review_group") if assignment else None
    if group not in matrix["review_groups"]:
        return {"employee": employee.name, "employee_name": employee.employee_name,
                "user_id": employee.user_id, "group": default_group,
                "status": "employee_not_configured",
                "matrix_version": matrix.get("routing_version")}
    return {"employee": employee.name, "employee_name": employee.employee_name,
            "user_id": employee.user_id, "group": group, "status": "resolved",
            "matrix_version": matrix.get("routing_version")}
