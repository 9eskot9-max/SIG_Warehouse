"""Shared petty-cash sender-to-review-group routing.

This module is the single routing source for task assignment now and the
future invoice-access policy. It does not grant access and exposes no API.
"""

import json
import re
from pathlib import Path

import frappe

from .pc_clearance_rules import compile_scopes


def load_matrix():
    # The existing approved file remains the source until the first publication.
    configured = None
    if frappe.db.exists("DocType", "SIG People Routing Setup"):
        configured = frappe.db.get_single_value("SIG People Routing Setup", "configuration_json")
    if configured:
        matrix = json.loads(configured)
    else:
        path = Path(__file__).with_name("pc_review_assignments.json")
        matrix = json.loads(path.read_text(encoding="utf-8-sig"))
    if matrix.get("phase") != "task_assignment_only":
        frappe.throw("PC review matrix is not marked for task assignment. [PC_MATRIX_PHASE_INVALID]")
    return matrix


def effective_scopes(matrix, employees):
    """Compile reviewer access from the exact same published matrix as task routing.

    Names remain in the current matrix contract, but every referenced identity must
    resolve uniquely to an active Employee ID before it can authorize a receipt.
    The returned scope is request-local; no second file or stale cache participates.
    """
    compiled = compile_scopes(matrix)
    by_name = {}
    active_ids = set()
    for employee in employees:
        if str(getattr(employee, "status", "Active")) != "Active":
            continue
        active_ids.add(str(employee.name))
        key = " ".join(str(getattr(employee, "employee_name", "") or "").casefold().split())
        if key:
            by_name.setdefault(key, []).append(str(employee.name))

    configured_ids = {str(row.get("employee") or "") for row in matrix.get("employees", [])}
    missing_targets = configured_ids - active_ids
    if missing_targets:
        raise ValueError("PC routing contains missing or inactive Employee IDs: " + ", ".join(sorted(missing_targets)))

    for row in matrix.get("employees", []):
        key = " ".join(str(row.get("employee_name") or "").casefold().split())
        hits = by_name.get(key, [])
        if len(hits) != 1 or hits[0] != str(row.get("employee") or ""):
            raise ValueError("PC routing identity no longer matches active Employee " + str(row.get("employee") or ""))

    for group, definition in matrix.get("review_groups", {}).items():
        for name in definition.get("reviewers", []):
            key = " ".join(str(name or "").casefold().split())
            hits = by_name.get(key, [])
            if len(hits) != 1:
                raise ValueError("Reviewer {!r} in group {!r} does not resolve to exactly one active Employee.".format(name, group))
            configured = [row for row in matrix.get("employees", [])
                          if " ".join(str(row.get("employee_name") or "").casefold().split()) == key]
            if len(configured) != 1 or str(configured[0].get("employee") or "") != hits[0]:
                raise ValueError("Reviewer {!r} in group {!r} has a stale Employee ID.".format(name, group))
    for employee_id, reviewers in compiled["employees"].items():
        if employee_id not in active_ids:
            raise ValueError("PC routing target is not active: " + employee_id)
        if any(reviewer not in active_ids for reviewer in reviewers):
            raise ValueError("PC routing reviewer is not active for " + employee_id)
    return compiled


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
        fields=["name", "employee_name", "cell_number", "user_id", "status"],
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
    extra = [g for g in assignment.get("additional_review_groups", [])
             if g in matrix["review_groups"] and g != group]
    return {"employee": employee.name, "employee_name": employee.employee_name,
            "user_id": employee.user_id, "group": group, "extra_groups": extra, "status": "resolved",
            "matrix_version": matrix.get("routing_version")}
