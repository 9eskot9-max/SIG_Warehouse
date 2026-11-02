"""v16: tidy the layout of the customised forms (see layout_spec.py).

Idempotent and failure-tolerant: a missing field or a refused change is logged and skipped so it can
never stop a migrate.
"""
import frappe

from sig_warehouse.sig_warehouse.layout_spec import CF, PS

SE_TAB = "custom_sig_overview_tab"
SE_SECTION = "custom_sig_return_section"


def _safe(label, fn):
    frappe.db.savepoint("layout_item")
    try:
        fn()
    except Exception as exc:
        frappe.db.rollback(save_point="layout_item")
        print(f"layout: skipped {label}: {exc!r}"[:300])


def _apply_cf(dt, fieldname, props):
    name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname})
    if not name:
        print(f"layout: skip {dt}.{fieldname} (not found)")
        return
    doc = frappe.get_doc("Custom Field", name)
    changed = False
    for key, value in props.items():
        if doc.get(key) != value:
            doc.set(key, value)
            changed = True
    if changed:
        doc.flags.ignore_permissions = True
        doc.save()


def _stock_entry():
    """Replace the near-empty first tab with a collapsed section further down (a field type cannot be edited)."""
    tab = frappe.db.get_value("Custom Field", {"dt": "Stock Entry", "fieldname": SE_TAB})
    if not tab or frappe.db.get_value("Custom Field", {"dt": "Stock Entry", "fieldname": SE_SECTION}):
        return
    frappe.get_doc({
        "doctype": "Custom Field", "dt": "Stock Entry", "fieldname": SE_SECTION, "fieldtype": "Section Break",
        "label": "Return / source information", "insert_after": "remarks", "collapsible": 1,
        "collapsible_depends_on": "eval:doc.custom_return_state || doc.custom_source_id",
    }).insert(ignore_permissions=True)
    _apply_cf("Stock Entry", "custom_return_state", {"insert_after": SE_SECTION})
    frappe.delete_doc("Custom Field", tab, ignore_permissions=True)


def _property_setter(dt, fieldname, prop, value, ptype):
    if frappe.db.exists("Property Setter", {"doc_type": dt, "field_name": fieldname, "property": prop}):
        return
    frappe.get_doc({"doctype": "Property Setter", "doctype_or_field": "DocField", "doc_type": dt,
                    "field_name": fieldname, "property": prop, "property_type": ptype, "value": value}
                   ).insert(ignore_permissions=True)


def execute():
    for dt, fieldname, props in CF:
        _safe(f"{dt}.{fieldname}", lambda: _apply_cf(dt, fieldname, props))
    _safe("Stock Entry tab", _stock_entry)
    for dt, fieldname, prop, value, ptype in PS:
        if frappe.db.exists("DocType", dt):
            _safe(f"{dt}.{fieldname}", lambda: _property_setter(dt, fieldname, prop, value, ptype))
    frappe.clear_cache()
