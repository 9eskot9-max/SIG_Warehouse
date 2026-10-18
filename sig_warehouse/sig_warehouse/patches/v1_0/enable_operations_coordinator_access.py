"""Grant the existing Coordinator profile to the two owner-confirmed Ops coordinators.

The profile is reused so this release does not create a parallel role set. It
matches the current Coordinator audience, including cycle operations, stock view
and PC review. ZATCA navigation remains limited to finance and system administration.
"""

import frappe


COORDINATOR_PROFILE = "SIG Coordinator"
COORDINATOR_ROLES = {
    "Employee",
    "Employee Self Service",
    "Projects User",
    "SIG Field Ops",
    "SIG PC Clearance",
    "SIG Stock Viewer",
}
TARGETS = {
    "m.waled@sigtele.com": {
        "employee_name": "Mohamed Walid Khalil Nmer Rahma",
        "current_profile": "SIG Employee + PC Reviewer",
        "current_roles": {"Employee", "Employee Self Service", "SIG PC Clearance"},
        "module_profile": "",
    },
    "sultan.muhammed@sigtele.local": {
        "employee_name": "Sultan Afsar Ashraf Muhammed",
        "current_profile": "SIG Employee",
        "current_roles": {"Employee", "Employee Self Service"},
        "module_profile": "SIG Employee",
    },
}
ZATCA_WORKSPACE = "ZATCA Integrations"
ZATCA_ROLES = {"System Manager", "Finance Manager", "Accounts Manager", "Accounts User"}
PAGE_AUDIENCE_ROLES = {"Projects User", "SIG Field Ops"}


def execute():
    _verify_coordinator_profile()
    _verify_operations_entry_points()
    users = _validate_target_users()
    workspace = _validate_zatca_workspace()
    _assign_coordinator_profiles(users)
    _restrict_zatca_workspace(workspace)
    frappe.clear_cache()


def _profile_roles(profile_name):
    profile = frappe.get_doc("Role Profile", profile_name)
    return {row.role for row in profile.roles}


def _verify_coordinator_profile():
    if not frappe.db.exists("Role Profile", COORDINATOR_PROFILE):
        frappe.throw("SIG Coordinator Role Profile is missing; refusing to grant Operations access.")
    if _profile_roles(COORDINATOR_PROFILE) != COORDINATOR_ROLES:
        frappe.throw("SIG Coordinator role set changed; review the full profile before assigning it.")


def _verify_operations_entry_points():
    for page_name in ("operations-workbench", "site-cycles"):
        if not frappe.db.exists("Page", page_name):
            frappe.throw("Required Operations Page is missing: " + page_name)
        page = frappe.get_doc("Page", page_name)
        if not PAGE_AUDIENCE_ROLES.issubset({row.role for row in page.roles}):
            frappe.throw(page_name + " no longer grants the existing Coordinator role audience.")

    for workspace_name in ("SIG Projects", "SIG Operations"):
        if not frappe.db.exists("Workspace", workspace_name):
            frappe.throw("Required Operations workspace is missing: " + workspace_name)
        workspace = frappe.get_doc("Workspace", workspace_name)
        if not PAGE_AUDIENCE_ROLES.intersection({row.role for row in workspace.roles}):
            frappe.throw(workspace_name + " no longer includes the Coordinator workspace audience.")


def _validate_target_users():
    validated = {}
    for user_name, expected in TARGETS.items():
        if not frappe.db.exists("User", user_name):
            frappe.throw("Operations Coordinator ERP User is missing: " + user_name)
        user = frappe.get_doc("User", user_name)
        if not user.enabled or user.user_type != "System User":
            frappe.throw("Operations Coordinator is not an enabled System User: " + user_name)
        if (user.module_profile or "") != expected["module_profile"]:
            frappe.throw("Module Profile changed for " + user_name + "; review before assigning Operations access.")

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user_name, "status": "Active"},
            ["name", "employee_name"],
            as_dict=True,
        )
        if not employee or employee.employee_name != expected["employee_name"]:
            frappe.throw("Active Employee link changed for " + user_name + "; refusing the profile assignment.")

        current_profile = user.role_profile_name or ""
        current_roles = {row.role for row in user.roles}
        if current_profile == COORDINATOR_PROFILE:
            if current_roles != COORDINATOR_ROLES:
                frappe.throw("Coordinator user role rows differ from the approved profile: " + user_name)
        else:
            if current_profile != expected["current_profile"]:
                frappe.throw("Role Profile changed for " + user_name + "; review before assigning Operations access.")
            if current_roles != expected["current_roles"]:
                frappe.throw("Existing role rows changed for " + user_name + "; refusing to replace them.")
            if _profile_roles(current_profile) != expected["current_roles"]:
                frappe.throw("Existing Role Profile changed for " + user_name + "; review before reassignment.")
        validated[user_name] = user
    return validated


def _assign_coordinator_profiles(users):
    for user_name, user in users.items():
        if user.role_profile_name == COORDINATOR_PROFILE:
            continue
        user.role_profile_name = COORDINATOR_PROFILE
        user.save(ignore_permissions=True)
        if user.role_profile_name != COORDINATOR_PROFILE or {row.role for row in user.roles} != COORDINATOR_ROLES:
            frappe.throw("SIG Coordinator profile did not persist as expected for " + user_name)


def _validate_zatca_workspace():
    if not frappe.db.exists("Workspace", ZATCA_WORKSPACE):
        frappe.throw("ZATCA Integrations workspace is missing; refusing a silent partial release.")
    workspace = frappe.get_doc("Workspace", ZATCA_WORKSPACE)
    if not workspace.public:
        frappe.throw("ZATCA Integrations is no longer a public workspace; review its visibility before changing roles.")
    current_roles = {row.role for row in workspace.roles}
    if current_roles not in (set(), ZATCA_ROLES):
        frappe.throw("ZATCA Integrations already has a different role list; review it before replacement.")
    return workspace


def _restrict_zatca_workspace(workspace):
    if {row.role for row in workspace.roles} == ZATCA_ROLES:
        return
    workspace.set("roles", [{"role": role} for role in sorted(ZATCA_ROLES)])
    workspace.save(ignore_permissions=True)
    if {row.role for row in workspace.roles} != ZATCA_ROLES:
        frappe.throw("ZATCA Integrations audience restrictions did not persist.")
