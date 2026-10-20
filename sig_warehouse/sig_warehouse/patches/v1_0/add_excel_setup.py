"""Add only Excel Setup capabilities; never reset another permission matrix."""
import frappe

EDITOR = "SIG Excel Setup Editor"
PROFILES = ("SIG Admin", "SIG PM", "SIG Coordinator", "SIG Stock Ops", "SIG Ops Coordinator")


def execute():
    for role in (EDITOR, "SIG Excel Setup Reader"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": int(role == EDITOR)}).insert(ignore_permissions=True)
    # Append a single capability, preserving every pre-existing role row. Add
    # to both profile and linked users so a later profile save retains it.
    for name in PROFILES:
        if not frappe.db.exists("Role Profile", name):
            continue
        profile = frappe.get_doc("Role Profile", name)
        if EDITOR not in {r.role for r in profile.roles}:
            # RoleProfile.on_update queues update_all_users, replacing each
            # user's whole role set (Frappe v15 core/doctype/role_profile).
            # Insert only this declared child row; do not trigger that fanout.
            child = profile.append("roles", {"role": EDITOR})
            child.db_insert()
        for user in frappe.get_all("User", filters={"role_profile_name": name, "enabled": 1, "user_type": "System User"}, pluck="name"):
            if not frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": EDITOR}):
                frappe.get_doc({"doctype": "Has Role", "parent": user, "parenttype": "User",
                                "parentfield": "roles", "role": EDITOR}).insert(ignore_permissions=True)
            frappe.clear_cache(user=user)
    if not frappe.db.get_single_value("SIG Excel Setup", "revision"):
        frappe.db.set_single_value("SIG Excel Setup", "revision", 0)
    for name in ("SIG Excel Setup", "SIG Excel Setup Revision"):
        if frappe.db.exists("Custom DocPerm", {"parent": name}):
            frappe.throw("Unexpected Custom DocPerm for " + name + "; review the whole matrix before release")
    frappe.clear_cache()
