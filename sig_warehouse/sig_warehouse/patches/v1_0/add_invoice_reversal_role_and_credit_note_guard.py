"""Durable baseline for the 2026-10-07 invoice-reversal control.

Until further notice only Baligh, Mohammed and Administrator may cancel Sales Invoices or
create/submit credit notes (Sales Invoice with is_return = 1). This patch makes that baseline
repeatable on any site that already carries the finance permission set; it is idempotent and was
applied live through the API first (record: ERPNext/backups/2026-10-07_invoice_reversal_restriction).

It converges the site to:
  * Role "SIG Invoice Reversal";
  * Sales Invoice Custom DocPerm row for that role: read + cancel only (every other ptype 0);
  * "cancel" removed from the Accounts Manager level-0 Sales Invoice row;
  * the role added to the ERP Admin Role Profile, plus a "Finance User + Invoice Reversal" profile
    assigned to Baligh (only while he is still on plain "Finance User");
  * Server Script "SIG Credit Note Restriction" (Sales Invoice, Before Validate).

Safety: in Frappe v15 any Custom DocPerm row replaces the standard list, so permission rows are only
touched when the site already has custom Sales Invoice rows - on a bare site this patch skips them
instead of creating a sparse set that would hide every other role.
"""
import frappe

ROLE = "SIG Invoice Reversal"
DOCTYPE = "Sales Invoice"
ADMIN_PROFILE = "ERP Admin"
BASE_FINANCE_PROFILE = "Finance User"
FINANCE_PROFILE = "Finance User + Invoice Reversal"
PROFILE_ASSIGNMENTS = {"baligh.hamdi@sigtele.com": FINANCE_PROFILE}
SCRIPT_NAME = "SIG Credit Note Restriction"

PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend",
          "report", "export", "import", "print", "email", "share", "select", "if_owner")
REVERSAL_ROW = {p: 0 for p in PTYPES}
REVERSAL_ROW.update(read=1, cancel=1)

SCRIPT_BODY = """# Server Script mirror: "SIG Credit Note Restriction"
# DocType Event | Sales Invoice | Before Validate | live from 2026-10-07
# Credit notes (is_return = 1) may be created or submitted only by Administrator or holders of
# the "SIG Invoice Reversal" role (Baligh, Mohammed, ERP Admin profile). Already-submitted
# returns are skipped so post-submit ZATCA / QR / payment-state updates are never blocked.
# Sandbox rules: no import, no frappe.db.sql, no backslash escapes.
if doc.is_return:
    stored = None
    if doc.name:
        stored = frappe.db.get_value("Sales Invoice", doc.name, "docstatus")
    if stored is None or stored == 0:
        user = frappe.session.user
        if user != "Administrator":
            allowed = frappe.db.exists("Has Role", {"parenttype": "User", "parent": user, "role": "SIG Invoice Reversal"})
            if not allowed:
                frappe.throw("Credit notes can be created or submitted only by authorised finance users (SIG Invoice Reversal). Please ask Baligh or Mohammed.")
"""


def execute():
    _ensure_role()
    _ensure_permission_rows()
    _ensure_role_profiles()
    _ensure_server_script()


def _ensure_role():
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(
            ignore_permissions=True
        )


def _ensure_permission_rows():
    if not frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE}):
        frappe.logger().warning("invoice reversal: no custom Sales Invoice permissions; rows skipped")
        return

    row = frappe.db.get_value(
        "Custom DocPerm", {"parent": DOCTYPE, "role": ROLE, "permlevel": 0}, "name"
    )
    if row:
        frappe.db.set_value("Custom DocPerm", row, REVERSAL_ROW, update_modified=False)
    else:
        frappe.get_doc(
            dict(doctype="Custom DocPerm", parent=DOCTYPE, role=ROLE, permlevel=0, **REVERSAL_ROW)
        ).insert(ignore_permissions=True)

    manager = frappe.db.get_value(
        "Custom DocPerm", {"parent": DOCTYPE, "role": "Accounts Manager", "permlevel": 0}, "name"
    )
    if manager:
        frappe.db.set_value("Custom DocPerm", manager, "cancel", 0, update_modified=False)
    frappe.clear_cache(doctype=DOCTYPE)


def _role_names(profile_doc):
    return [r.role for r in profile_doc.roles]


def _ensure_role_profiles():
    # Roles reach people only through Role Profiles; saving a profile re-derives its users' roles,
    # so profiles that already match are left untouched.
    if frappe.db.exists("Role Profile", ADMIN_PROFILE):
        admin = frappe.get_doc("Role Profile", ADMIN_PROFILE)
        if ROLE not in _role_names(admin):
            admin.append("roles", {"role": ROLE})
            admin.save(ignore_permissions=True)

    if not frappe.db.exists("Role Profile", FINANCE_PROFILE) and frappe.db.exists(
        "Role Profile", BASE_FINANCE_PROFILE
    ):
        roles = _role_names(frappe.get_doc("Role Profile", BASE_FINANCE_PROFILE)) + [ROLE]
        frappe.get_doc(
            {
                "doctype": "Role Profile",
                "role_profile": FINANCE_PROFILE,
                "roles": [{"role": r} for r in roles],
            }
        ).insert(ignore_permissions=True)

    if not frappe.db.exists("Role Profile", FINANCE_PROFILE):
        return
    for user, profile in PROFILE_ASSIGNMENTS.items():
        current = frappe.db.get_value("User", user, "role_profile_name")
        if current == BASE_FINANCE_PROFILE:
            doc = frappe.get_doc("User", user)
            doc.role_profile_name = profile
            doc.save(ignore_permissions=True)


def _ensure_server_script():
    if frappe.db.exists("Server Script", SCRIPT_NAME):
        if frappe.db.get_value("Server Script", SCRIPT_NAME, "script") != SCRIPT_BODY:
            frappe.db.set_value("Server Script", SCRIPT_NAME, "script", SCRIPT_BODY)
        return
    frappe.get_doc(
        {
            "doctype": "Server Script",
            "name": SCRIPT_NAME,
            "script_type": "DocType Event",
            "reference_doctype": DOCTYPE,
            "doctype_event": "Before Validate",
            "disabled": 0,
            "script": SCRIPT_BODY,
        }
    ).insert(ignore_permissions=True)
