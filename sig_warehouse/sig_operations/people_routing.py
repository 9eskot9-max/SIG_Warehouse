"""Restricted, revision-controlled employee operational and PC routing setup."""

import copy
import json

import frappe
from frappe import _

from sig_warehouse.sig_warehouse.pc_clearance_rules import compile_scopes
from sig_warehouse.sig_warehouse.pc_review_routing import load_matrix

DOCTYPE = "SIG People Routing Setup"


def _require():
    if frappe.session.user == "Guest" or "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only System Manager can manage employee routing."), frappe.PermissionError)


@frappe.whitelist()
def get_state():
    _require()
    doc = frappe.get_single(DOCTYPE)
    matrix = load_matrix()
    return {"revision": int(doc.revision or 0), "matrix": matrix}


@frappe.whitelist(methods=["POST"])
def publish(rows, base_revision, reviewer_groups):
    """Update employee group membership and reviewer lists as one revision."""
    _require()
    rows = frappe.parse_json(rows)
    reviewer_groups = frappe.parse_json(reviewer_groups)
    if not isinstance(rows, list) or len(rows) > 10000:
        frappe.throw(_("Invalid employee routing rows."))
    # A distributed lock serializes the first publication as well as later ones.
    with frappe.cache().lock("sig_people_routing_publish", timeout=60):
        doc = frappe.get_single(DOCTYPE)
        if int(doc.revision or 0) != int(base_revision):
            frappe.throw(_("Routing changed in another session. Reload and review it."))
        matrix = copy.deepcopy(load_matrix())
        current = {row["employee"]: row for row in matrix["employees"]}
        original = set(current)
        if len(current) != len(matrix["employees"]):
            frappe.throw(_("Duplicate employee in current routing source."))
        groups = set(matrix["review_groups"])
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"employee", "work_group", "pc_review_group", "additional_review_groups"}:
                frappe.throw(_("Invalid routing row."))
            employee = str(row["employee"] or "").strip()
            if not employee or employee in seen:
                frappe.throw(_("Employee is missing or duplicated."))
            if employee not in current:
                person = frappe.get_doc("Employee", employee)
                person.check_permission("read")
                if person.status != "Active":
                    frappe.throw(_("A new routing row requires an active Employee."))
                current[employee] = {"employee": employee, "employee_name": person.employee_name,
                                     "department": person.department or "", "basis": "People setup"}
                matrix["employees"].append(current[employee])
            seen.add(employee)
            work_group = str(row["work_group"] or "").strip()
            pc_group = str(row["pc_review_group"] or "").strip()
            additional = row["additional_review_groups"]
            if work_group not in groups or pc_group not in groups or not isinstance(additional, list):
                frappe.throw(_("Choose valid groups."))
            if len(set(additional)) != len(additional) or any(group not in groups or group == pc_group for group in additional):
                frappe.throw(_("Additional review groups must be valid, distinct and different from the main group."))
            current[employee].update(work_group=work_group, pc_review_group=pc_group, additional_review_groups=additional)
        if not original.issubset(seen):
            frappe.throw(_("All current employee rows must be included. Reload and retry."))
        if not isinstance(reviewer_groups, dict) or set(reviewer_groups) != groups:
            frappe.throw(_("Reviewer groups do not match the current setup."))
        employee_names = {" ".join(str(row["employee_name"]).casefold().split()) for row in current.values()}
        for group, reviewers in reviewer_groups.items():
            if not isinstance(reviewers, list) or not reviewers or any(not isinstance(name, str) or not name.strip() for name in reviewers):
                frappe.throw(_("Every group needs at least one valid reviewer."))
            normalized = [" ".join(name.casefold().split()) for name in reviewers]
            if len(set(normalized)) != len(normalized) or any(name not in employee_names for name in normalized):
                frappe.throw(_("Reviewers must be distinct employees in the routing list."))
            matrix["review_groups"][group]["reviewers"] = [name.strip() for name in reviewers]
        matrix["routing_version"] = "people-setup-" + str(int(doc.revision or 0) + 1)
        try:
            compile_scopes(matrix)
        except (KeyError, ValueError) as exc:
            frappe.throw(_("Routing is invalid: {0}").format(str(exc)))
        doc.revision = int(doc.revision or 0) + 1
        doc.configuration_json = json.dumps(matrix, ensure_ascii=False, sort_keys=True)
        previous = frappe.flags.sig_people_routing_service
        frappe.flags.sig_people_routing_service = True
        try:
            doc.save(ignore_permissions=True)
            # Keep the lock until the new revision is visible to another request.
            frappe.db.commit()
        finally:
            frappe.flags.sig_people_routing_service = previous
        return {"revision": doc.revision}
