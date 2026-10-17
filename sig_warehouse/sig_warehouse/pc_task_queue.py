"""Task assignment only. This module grants no invoice access or confirmation API.

Employee IDs in pc_review_assignments.json own routing. Legacy Source Manager
does not override owner-approved Capex, Incident, Colocation or Warehouse scope.
Finance receives General and every unresolved/unassigned receipt. Visibility
and confirmation authorization are a separate, deferred release.
"""

from html import escape

import frappe
from .pc_review_routing import active_employees, load_matrix, phone_index, resolve_sender


def _routed_pending(matrix, employees):
    phones = phone_index(employees)
    routed = []
    pending = frappe.get_all(
        "SIG PC Transaction",
        filters={"closure_status": ["in", ["Draft", "Needs Review"]]},
        fields=["name", "employee_name"], limit_page_length=0,
    )
    for row in pending:
        route = resolve_sender(row.employee_name, matrix, employees, phones)
        routed.append({"transaction": row.name, "group": route["group"],
                       "employee": route["employee"],
                       "sender_user": route["user_id"],
                       "route_status": route["status"],
                       "matrix_version": route["matrix_version"]})
    return routed


def _reviewer_accounts(matrix, employees):
    by_name = {}
    for employee in employees:
        key = " ".join(str(employee.employee_name or "").casefold().split())
        by_name.setdefault(key, []).append(employee)
    accounts, missing = {}, []
    for group, definition in matrix["review_groups"].items():
        accounts[group] = set()
        for name in definition["reviewers"]:
            hits = by_name.get(" ".join(name.casefold().split()), [])
            user = hits[0].user_id if len(hits) == 1 else None
            if user and frappe.db.get_value("User", user, "enabled"):
                accounts[group].add(user)
            else:
                missing.append({"group": group, "employee_name": name})
    return accounts, missing


def _marker(group, user):
    return "<!--SIGPC_TASK_GROUP:{}:{}-->".format(group, user)


def _close(task_name):
    task = frappe.get_doc("ToDo", task_name)
    if task.status not in ("Closed", "Cancelled"):
        task.status = "Closed"
        task.save(ignore_permissions=True)


def _upsert(user, group, label, count):
    marker = _marker(group, user)
    existing = frappe.get_all(
        "ToDo", filters={"allocated_to": user, "description": ["like", "%" + marker + "%"]},
        fields=["name", "description", "status"], order_by="creation asc", limit_page_length=0,
    )
    if not count:
        for task in existing:
            _close(task.name)
        return
    description = (
        '<p>Review {} pending petty-cash receipt(s): {}.</p>'
        '<p><a href="/app/pc-invoice-review">Open petty-cash review</a>. '
        'The count follows pending receipts; checking off this ToDo does not confirm them.</p>{}'
    ).format(count, escape(label), marker)
    if existing:
        task = frappe.get_doc("ToDo", existing[0].name)
        if task.description != description or task.status in ("Closed", "Cancelled"):
            task.description = description
            task.status = "Open"
            task.save(ignore_permissions=True)
        for duplicate in existing[1:]:
            _close(duplicate.name)
    else:
        frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": description,
                        "status": "Open", "priority": "Medium"}).insert(ignore_permissions=True)


def sync_pc_review_todos():
    """Maintain shared group-count tasks under existing access; not whitelisted."""
    matrix = load_matrix()
    employees = active_employees()
    rows = _routed_pending(matrix, employees)
    accounts, missing = _reviewer_accounts(matrix, employees)
    active_markers, counts = set(), {}
    route_exceptions = {}
    for group, definition in matrix["review_groups"].items():
        group_rows = [r for r in rows if r["group"] == group]
        counts[group] = len(group_rows)
        for user in accounts[group]:
            # A person's own receipts are never included in their assigned task.
            count = sum(1 for row in group_rows if row["sender_user"] != user)
            active_markers.add(_marker(group, user))
            _upsert(user, group, definition["label"], count)
    for row in rows:
        if row["route_status"] != "resolved":
            route_exceptions[row["route_status"]] = route_exceptions.get(row["route_status"], 0) + 1
    for task in frappe.get_all(
        "ToDo", filters={"description": ["like", "%<!--SIGPC_TASK_GROUP:%"],
                          "status": ["not in", ["Closed", "Cancelled"]]},
        fields=["name", "description"], limit_page_length=0,
    ):
        if not any(marker in task.description for marker in active_markers):
            _close(task.name)
    return {"routing_version": matrix.get("routing_version"),
            "pending_by_group": counts, "route_exceptions": route_exceptions,
            "missing_reviewer_accounts": missing,
            "access_changes": False}
