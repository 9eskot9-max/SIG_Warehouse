"""Restricted, revision-controlled employee operational and PC routing setup."""

import copy
import hashlib
import json
from pathlib import Path

import frappe
from frappe import _

from sig_warehouse.sig_warehouse.pc_review_routing import active_employees, effective_scopes, load_matrix

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


def scope_difference(before, after):
    """Compare receipt access by target Employee and reviewer Employee ID."""
    result = []
    for employee in sorted(set(before) | set(after)):
        old, new = set(before.get(employee, [])), set(after.get(employee, []))
        added, removed = sorted(new - old), sorted(old - new)
        if added or removed:
            result.append({"employee": employee, "added": added, "removed": removed})
    return result


@frappe.whitelist()
def preview_current_scope_change():
    """Review today's published matrix against the currently deployed static scope."""
    _require()
    matrix = load_matrix()
    try:
        compiled = effective_scopes(matrix, active_employees())
        baseline = json.loads(Path(__file__).parents[1].joinpath(
            "sig_warehouse", "pc_review_scopes.json").read_text(encoding="utf-8"))
        changes = scope_difference(baseline["employees"], compiled["employees"])
    except (KeyError, ValueError, OSError) as exc:
        frappe.throw(_("Cannot compare routing scopes: {0}").format(str(exc)))
    return {"revision": compiled.get("revision"), "changes": changes,
            "added": sum(len(row["added"]) for row in changes),
            "removed": sum(len(row["removed"]) for row in changes)}


def _prepare_proposal(rows, base_revision, reviewer_groups):
    rows, reviewer_groups = frappe.parse_json(rows), frappe.parse_json(reviewer_groups)
    doc = frappe.get_single(DOCTYPE)
    if int(doc.revision or 0) != int(base_revision):
        frappe.throw(_("Routing changed in another session. Reload and review it."))
    original = load_matrix()
    matrix = copy.deepcopy(original)
    if not isinstance(rows, list) or len(rows) > 10000 or not isinstance(reviewer_groups, dict):
        frappe.throw(_("Invalid routing proposal."))
    groups = set(matrix["review_groups"])
    if set(reviewer_groups) != groups:
        frappe.throw(_("Reviewer groups do not match the current setup."))
    existing = {r["employee"]: r for r in matrix["employees"]}
    if len(existing) != len(matrix["employees"]):
        frappe.throw(_("Duplicate employee in current routing."))
    people = {person.name: person for person in active_employees()}
    setup = json.loads(frappe.db.get_single_value("SIG Excel Setup", "configuration_json") or "{}")
    defaults = {r["family"]: r["review_group"] for r in setup.get("pc_family_defaults", []) if r.get("enabled")}
    families = {"capex": "Capex", "incident": "Incident", "colocation": "5G / Colocation"}
    proposed, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {"employee", "work_group", "pc_review_group", "additional_review_groups", "pc_mode"} or not {"employee", "work_group", "pc_review_group", "additional_review_groups"}.issubset(row):
            frappe.throw(_("Invalid routing row."))
        employee = str(row["employee"] or "").strip()
        additional = row["additional_review_groups"]
        mode = row.get("pc_mode", "override") or "override"
        if mode not in ("inherit", "override"):
            frappe.throw(_("Choose inherit or override for petty cash routing."))
        if mode == "inherit":
            family = families.get(row["work_group"])
            group = defaults.get(family)
            if not family or group not in groups:
                frappe.throw(_("A valid family default is required for {0}.").format(employee))
            row["pc_review_group"] = group
        if not employee or employee in seen or employee not in people:
            frappe.throw(_("Each routing row needs a distinct active Employee."))
        if row["work_group"] not in groups or row["pc_review_group"] not in groups or not isinstance(additional, list):
            frappe.throw(_("Choose valid routing groups."))
        if any(not isinstance(g, str) or g not in groups or g == row["pc_review_group"] for g in additional) or len(set(additional)) != len(additional):
            frappe.throw(_("Additional groups must be valid and distinct."))
        seen.add(employee)
        item = copy.deepcopy(existing.get(employee) or {"employee": employee, "employee_name": people[employee].employee_name, "basis": "People setup"})
        item.update(work_group=row["work_group"], pc_review_group=row["pc_review_group"], additional_review_groups=additional, pc_mode=mode)
        proposed.append(item)
    if not set(existing).issubset(seen):
        frappe.throw(_("All existing routing employees must be included."))
    for group, reviewers in reviewer_groups.items():
        if not isinstance(reviewers, list) or not reviewers or any(not isinstance(n, str) or not n.strip() for n in reviewers):
            frappe.throw(_("Every group needs valid reviewers."))
        normalized = [" ".join(n.casefold().split()) for n in reviewers]
        if len(set(normalized)) != len(normalized):
            frappe.throw(_("Duplicate reviewer in group {0}.").format(group))
        matrix["review_groups"][group]["reviewers"] = [n.strip() for n in reviewers]
    matrix["employees"] = proposed
    try:
        old = effective_scopes(original, list(people.values()))["employees"]
        new = effective_scopes(matrix, list(people.values()))["employees"]
    except (KeyError, ValueError) as exc:
        frappe.throw(_("Cannot validate routing proposal: {0}").format(str(exc)))
    changes = scope_difference(old, new)
    fingerprint = hashlib.sha256(json.dumps(matrix, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return matrix, {"revision": int(doc.revision or 0), "changes": changes, "hash": fingerprint,
                    "added": sum(len(r["added"]) for r in changes), "removed": sum(len(r["removed"]) for r in changes)}


@frappe.whitelist(methods=["POST"])
def preview_proposed_routing(rows, base_revision, reviewer_groups):
    _require()
    return _prepare_proposal(rows, base_revision, reviewer_groups)[1]


@frappe.whitelist(methods=["POST"])
def publish(rows, base_revision, reviewer_groups, preview_hash=None):
    """Publish only the exact validated proposal, retaining recoverable history."""
    _require()
    with frappe.cache().lock("sig_people_routing_publish", timeout=60):
        # Serialize against Excel Setup publication so inherited defaults cannot
        # change between the reviewed hash and this routing revision.
        frappe.db.sql("SELECT value FROM tabSingles WHERE doctype=%s AND field='revision' FOR UPDATE", ("SIG Excel Setup",))
        matrix, preview = _prepare_proposal(rows, base_revision, reviewer_groups)
        if not preview_hash or preview_hash != preview["hash"]:
            frappe.throw(_("Preview the current proposal before publishing; configuration may have changed."))
        doc = frappe.get_single(DOCTYPE)
        history = json.loads(doc.history_json or "[]")
        history.append({"revision": int(doc.revision or 0), "matrix": load_matrix(), "saved_by": frappe.session.user, "saved_at": str(frappe.utils.now_datetime())})
        doc.revision = int(doc.revision or 0) + 1
        matrix["routing_version"] = "people-setup-" + str(doc.revision)
        doc.configuration_json = json.dumps(matrix, ensure_ascii=False, sort_keys=True)
        doc.history_json = json.dumps(history, ensure_ascii=False, sort_keys=True)
        previous = frappe.flags.sig_people_routing_service
        frappe.flags.sig_people_routing_service = True
        try:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        finally:
            frappe.flags.sig_people_routing_service = previous
        return {"revision": doc.revision}


@frappe.whitelist()
def history():
    _require()
    doc = frappe.get_single(DOCTYPE)
    return [{"revision": item["revision"], "saved_by": item.get("saved_by"), "saved_at": item.get("saved_at")}
            for item in json.loads(doc.history_json or "[]")]


def _history_proposal(revision):
    doc = frappe.get_single(DOCTYPE)
    matches = [item for item in json.loads(doc.history_json or "[]") if int(item["revision"]) == int(revision)]
    if len(matches) != 1:
        frappe.throw(_("Routing revision was not found or is ambiguous."))
    matrix = matches[0]["matrix"]
    # Restore the recorded effective groups exactly; a later family-default
    # change must not silently rewrite the meaning of a historical revision.
    rows = [{"employee": r["employee"], "work_group": r["work_group"],
             "pc_review_group": r["pc_review_group"], "additional_review_groups": r.get("additional_review_groups", []),
             "pc_mode": "override"} for r in matrix["employees"]]
    groups = {key: value["reviewers"] for key, value in matrix["review_groups"].items()}
    return rows, groups


@frappe.whitelist(methods=["POST"])
def preview_restore(revision, base_revision):
    _require()
    rows, groups = _history_proposal(revision)
    return _prepare_proposal(rows, base_revision, groups)[1]


@frappe.whitelist(methods=["POST"])
def restore(revision, base_revision, preview_hash):
    _require()
    rows, groups = _history_proposal(revision)
    return publish(rows, base_revision, groups, preview_hash)
