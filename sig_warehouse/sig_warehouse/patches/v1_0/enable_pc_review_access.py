"""Enable the approved petty-cash reviewer audience on the canonical Desk Page.

This deliberately grants read-only transaction access to SIG PC Clearance. Review
actions remain explicitly role-checked in the two API Server Scripts. The assigned
queue is still global; project/group scoping is a later, separate release.
"""

import frappe


ROLE = "SIG PC Clearance"
DOCTYPE = "SIG PC Transaction"
PAGE = "pc-invoice-review"
WORKSPACE = "SIG Petty Cash"
SHORTCUT_LABEL = "Invoice Review Board"
BASE_PAGE_ROLES = {
    "System Manager",
    "Accounts User",
    "Accounts Manager",
    "Operations User",
    "Operations Manager",
}

PTYPES = (
    "read",
    "write",
    "create",
    "submit",
    "cancel",
    "delete",
    "amend",
    "report",
    "export",
    "import",
    "print",
    "email",
    "share",
    "select",
    "if_owner",
)

BASE_MATRIX = {
    role: {
        permission: int(
            permission
            in {"read", "write", "create", "delete", "report", "export", "print", "email", "share"}
        )
        for permission in PTYPES
    }
    for role in (
        "Accounts User",
        "Accounts Manager",
        "Operations User",
        "Operations Manager",
        "System Manager",
    )
}

REVIEWER_ROLE_PROFILES = {
    "mohammad.ansary@sigtele.com": ("SIG Employee", "SIG Employee + PC Reviewer"),
    "m.waled@sigtele.com": ("SIG Employee", "SIG Employee + PC Reviewer"),
    "tahir.shahzad@sigtele.com": ("Warehouse Manager", "Warehouse Manager + PC Reviewer"),
}

REQUIRED_REVIEWERS = (
    "mohammad.ansary@sigtele.com",
    "gulzaar.ahmed@sigtele.com",
    "abdul.raheem@sigtele.com",
    "s.ilyas@sigtele.com",
    "arshad.ahmed@sigtele.com",
    "imran.ansary@sigtele.com",
    "m.waled@sigtele.com",
    "obed.sharrif@sigtele.com",
    "tahir.shahzad@sigtele.com",
    "hamid.j@sigtele.com",
    "baligh.hamdi@sigtele.com",
    "mahmoud.muhammad@sigtele.com",
    "humaira.gilani@sigtele.com",
)
REVIEW_ROLES = {
    "System Manager",
    "Accounts User",
    "Accounts Manager",
    "Operations User",
    "Operations Manager",
    ROLE,
}

SERVER_SCRIPTS = (
    "sig_pc_close_transaction",
    "sig_pc_reject_transaction",
)
OLD_ALLOWLIST = 'ROLES = ["Accounts User", "Accounts Manager", "Operations User", "Operations Manager", "System Manager"]'
NEW_ALLOWLIST = 'ROLES = ["Accounts User", "Accounts Manager", "Operations User", "Operations Manager", "System Manager", "SIG PC Clearance"]'


def execute():
    _sync_page_roles()
    _ensure_read_permission()
    _assign_missing_reviewer_roles()
    _enable_review_actions()
    _remove_duplicate_workspace_shortcut()
    _verify_approved_reviewers()
    frappe.clear_cache(doctype=DOCTYPE)
    frappe.clear_cache(doctype="Page")


def _sync_page_roles():
    if not frappe.db.exists("Role", ROLE):
        frappe.throw("SIG PC Clearance role is missing; refusing the petty-cash access patch.")
    page = frappe.get_doc("Page", PAGE)
    page_roles = {row.role for row in page.roles}
    if page.module != "SIG Accounting":
        frappe.throw("pc-invoice-review is no longer owned by SIG Accounting; refusing the access patch.")
    if not BASE_PAGE_ROLES.issubset(page_roles) or page_roles - (BASE_PAGE_ROLES | {ROLE}):
        frappe.throw("pc-invoice-review Page role list changed; review the full audience before updating it.")
    if ROLE not in page_roles:
        page.append("roles", {"role": ROLE})
        page.save(ignore_permissions=True)
    if ROLE not in {row.role for row in page.roles}:
        frappe.throw("SIG PC Clearance did not persist on pc-invoice-review.")


def _row_values(row):
    return {permission: int(getattr(row, permission, 0) or 0) for permission in PTYPES}


def _ensure_read_permission():
    if frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE}):
        frappe.throw(
            "SIG PC Transaction has Custom DocPerm rows; review the full matrix before adding reviewer access."
        )

    doc = frappe.get_doc("DocType", DOCTYPE)
    if not doc.custom:
        frappe.throw("SIG PC Transaction is no longer a custom DocType; permission source ownership changed.")

    rows = {row.role: row for row in doc.permissions if int(row.permlevel or 0) == 0}
    expected_base_roles = set(BASE_MATRIX)
    allowed_roles = expected_base_roles | {ROLE}
    if set(rows) - allowed_roles or not expected_base_roles.issubset(rows):
        frappe.throw("SIG PC Transaction base permission roles changed; refusing to replace or broaden its matrix.")

    for role, expected in BASE_MATRIX.items():
        if _row_values(rows[role]) != expected:
            frappe.throw("SIG PC Transaction permission matrix changed for " + role + "; review it before release.")

    clearance = {permission: int(permission == "read") for permission in PTYPES}
    if ROLE in rows:
        if _row_values(rows[ROLE]) != clearance:
            frappe.throw("Existing SIG PC Clearance transaction permissions differ from the approved read-only row.")
        return

    doc.append("permissions", {"role": ROLE, "permlevel": 0, **clearance})
    doc.save(ignore_permissions=True)


def _role_names(profile):
    return {row.role for row in profile.roles}


def _assign_missing_reviewer_roles():
    for user_name, (base_profile_name, reviewer_profile_name) in REVIEWER_ROLE_PROFILES.items():
        if not frappe.db.exists("User", user_name):
            frappe.throw("Approved petty-cash reviewer ERP User is missing: " + user_name)

        user = frappe.get_doc("User", user_name)
        if not user.enabled or user.user_type != "System User":
            frappe.throw("Approved petty-cash reviewer is not an enabled System User: " + user_name)

        current_profile = user.role_profile_name or ""
        user_roles = {row.role for row in user.roles}
        if current_profile == reviewer_profile_name:
            profile = frappe.get_doc("Role Profile", reviewer_profile_name)
            if ROLE not in _role_names(profile) or ROLE not in user_roles:
                frappe.throw("Existing reviewer Role Profile is inconsistent for " + user_name)
            continue

        if current_profile != base_profile_name:
            if ROLE in user_roles:
                continue
            frappe.throw("Reviewer profile changed for " + user_name + "; expected " + base_profile_name + ".")

        base = frappe.get_doc("Role Profile", base_profile_name)
        expected_roles = _role_names(base) | {ROLE}
        if ROLE in _role_names(base):
            frappe.throw("Base Role Profile unexpectedly includes SIG PC Clearance: " + base_profile_name)

        if frappe.db.exists("Role Profile", reviewer_profile_name):
            reviewer_profile = frappe.get_doc("Role Profile", reviewer_profile_name)
            if _role_names(reviewer_profile) != expected_roles:
                frappe.throw("Reviewer Role Profile has unexpected permissions: " + reviewer_profile_name)
        else:
            frappe.get_doc(
                {
                    "doctype": "Role Profile",
                    "role_profile": reviewer_profile_name,
                    "roles": [{"role": role} for role in sorted(expected_roles)],
                }
            ).insert(ignore_permissions=True)

        user.role_profile_name = reviewer_profile_name
        user.save(ignore_permissions=True)
        if ROLE not in {row.role for row in user.roles}:
            frappe.throw("SIG PC Clearance did not persist on reviewer account: " + user_name)


def _enable_review_actions():
    for script_name in SERVER_SCRIPTS:
        script = frappe.get_doc("Server Script", script_name)
        if script.disabled:
            frappe.throw("Petty-cash review action is disabled: " + script_name)

        source = script.script or ""
        if NEW_ALLOWLIST in source:
            continue
        if source.count(OLD_ALLOWLIST) != 1:
            frappe.throw("Unexpected role guard in Server Script " + script_name + "; refusing a broad rewrite.")

        script.script = source.replace(OLD_ALLOWLIST, NEW_ALLOWLIST, 1)
        script.save(ignore_permissions=True)


def _remove_duplicate_workspace_shortcut():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    workspace = frappe.get_doc("Workspace", WORKSPACE)
    matches = [row for row in workspace.shortcuts if row.label == SHORTCUT_LABEL]
    if not matches:
        return
    if len(matches) != 1 or matches[0].type != "Page" or matches[0].link_to != PAGE:
        frappe.throw("SIG Petty Cash Invoice Review Board shortcut changed; refusing to remove an unexpected link.")

    workspace.set("shortcuts", [row for row in workspace.shortcuts if row.name != matches[0].name])
    workspace.save(ignore_permissions=True)


def _verify_approved_reviewers():
    for user_name in REQUIRED_REVIEWERS:
        if not frappe.db.exists("User", user_name):
            frappe.throw("Approved petty-cash reviewer ERP User is missing: " + user_name)
        user = frappe.get_doc("User", user_name)
        if not user.enabled or user.user_type != "System User":
            frappe.throw("Approved petty-cash reviewer is not an enabled System User: " + user_name)
        if not REVIEW_ROLES.intersection({row.role for row in user.roles}):
            frappe.throw("Approved petty-cash reviewer has no route role after the access patch: " + user_name)
