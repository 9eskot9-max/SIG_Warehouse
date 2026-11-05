"""Read-only comparison before activating the shared Operations/team model."""
import frappe

from sig_warehouse.sig_operations.excel_setup import _state
from sig_warehouse.sig_warehouse.operations_workbench import OPS_ROSTER, _normalize_person
from sig_warehouse.sig_warehouse.project_family import normalize_family


@frappe.whitelist()
def preview():
    if frappe.session.user == "Guest" or "System Manager" not in frappe.get_roles():
        frappe.throw("Only System Manager can review the People model cutover.", frappe.PermissionError)
    if not frappe.has_permission("Employee", "read"):
        frappe.throw("Employee read access is required.", frappe.PermissionError)
    doc, data = _state()
    today = str(frappe.utils.nowdate())[:10]
    employees = frappe.get_all("Employee", filters={"status": "Active"},
                               fields=["name", "employee_name", "user_id"], limit_page_length=0)
    identities = {}
    for employee in employees:
        if employee.get("user_id"):
            identities.setdefault(_normalize_person(employee.get("employee_name")), []).append(str(employee.name))
    existing, unresolved = {}, []
    for family, groups in OPS_ROSTER.items():
        for names in groups.values():
            for name in names:
                matches = identities.get(_normalize_person(name), [])
                if len(matches) != 1:
                    unresolved.append({"family": family, "name": name, "matches": len(matches)})
                else:
                    existing.setdefault(family, set()).add(matches[0])
    configured, exceptions = {}, {}
    for row in data.get("ops_team_members", []):
        start, end = str(row.get("effective_from") or "")[:10], str(row.get("effective_to") or "")[:10]
        if not (row.get("enabled") and start and start <= today and (not end or today <= end)):
            continue
        family = normalize_family(row.get("family"))
        if row.get("project"):
            exceptions.setdefault(str(row["project"]), set()).add(str(row.get("employee") or ""))
        else:
            configured.setdefault(family, set()).add(str(row.get("employee") or ""))
    comparisons = []
    for family in sorted(set(existing) | set(configured)):
        old, new = existing.get(family, set()), configured.get(family, set())
        comparisons.append({"family": family, "current": sorted(old), "configured": sorted(new),
                            "added": sorted(new - old), "removed": sorted(old - new)})
    active_leaders = {}
    for row in data.get("team_memberships", []):
        start, end = str(row.get("effective_from") or "")[:10], str(row.get("effective_to") or "")[:10]
        if row.get("enabled") and row.get("role") == "leader" and start and start <= today and (not end or today <= end):
            active_leaders.setdefault(str(row.get("team")), set()).add(str(row.get("employee") or ""))
    bad_teams = [{"team": row.get("id"), "active_leaders": len(active_leaders.get(str(row.get("id")), set()))}
                 for row in data.get("operational_teams", []) if row.get("enabled")
                 and len(active_leaders.get(str(row.get("id")), set())) != 1]
    return {"revision": int(doc.revision or 0), "as_of": today, "families": comparisons,
            "unresolved_identities": unresolved, "project_exceptions": len(exceptions), "teams_needing_leader": bad_teams,
            "notice": "Membership comparison only. Shared task roles, Project exceptions, permissions, cycle links and Planner behavior need separate review."}
