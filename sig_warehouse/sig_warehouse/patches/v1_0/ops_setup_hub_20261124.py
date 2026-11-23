"""Convert the published Excel Setup to the Operations Setup Hub shape and drop the unused Weekly Scope DocType.

The previous revision stays in revision history. Fails loudly (blocking the update) rather than
guessing a role for a person who was not in the old hard-coded roster. Running it twice is a no-op.
"""
import frappe


def execute():
    from sig_warehouse.sig_operations.excel_setup import _publish, _state
    from sig_warehouse.sig_operations.ops_setup_migration import WAREHOUSE_USERS, migrate

    if frappe.db.exists("DocType", "SIG Excel Setup"):
        doc, stored_now = _state(lock=True)
        raw = frappe.parse_json(doc.configuration_json or "{}")
        ids = {row.get("employee") for row in raw.get("ops_team_members", []) + raw.get("team_memberships", [])}
        names = {e.name: e.employee_name for e in frappe.get_all("Employee", filters={"name": ["in", sorted(i for i in ids if i)]},
                                                                  fields=["name", "employee_name"], limit_page_length=0)}
        warehouse = frappe.get_all("Employee", filters={"user_id": ["in", list(WAREHOUSE_USERS)], "status": "Active"},
                                   pluck="name", limit_page_length=0)
        migrated = migrate(raw, names, warehouse, str(frappe.utils.nowdate()))
        if migrated != stored_now:
            _publish(migrated, int(doc.revision or 0))
    if frappe.db.exists("DocType", "SIG PM Weekly Scope"):
        if not frappe.db.count("SIG PM Weekly Scope"):
            frappe.delete_doc("DocType", "SIG PM Weekly Scope", force=True, ignore_missing=True)
