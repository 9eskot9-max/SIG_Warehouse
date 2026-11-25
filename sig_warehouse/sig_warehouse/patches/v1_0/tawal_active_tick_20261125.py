"""Replace the TAWAL family default dates with one Active tick per family; keep old PMs unticked.

Reads the raw stored JSON because the current contract no longer knows the date columns.
Running it twice is a no-op.
"""
import frappe


def execute():
    from sig_warehouse.sig_operations.excel_setup import _publish, _state
    from sig_warehouse.sig_operations.ops_setup_migration import _norm, tawal_active_tick

    if not frappe.db.exists("DocType", "SIG Excel Setup"):
        return
    doc, datasets = _state(lock=True)
    raw = frappe.parse_json(doc.configuration_json or "{}").get("family_tawal_defaults", [])
    if not raw:
        return
    contacts = {_norm(c.full_name): c.name for c in
                frappe.get_all("SIG TAWAL Contact", fields=["name", "full_name"], limit_page_length=0)}
    datasets["family_tawal_defaults"] = tawal_active_tick(raw, contacts, str(frappe.utils.nowdate()))
    _publish(datasets, int(doc.revision or 0))
