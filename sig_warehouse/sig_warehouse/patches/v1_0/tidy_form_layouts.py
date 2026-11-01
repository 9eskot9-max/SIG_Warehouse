"""v16: tidy the layout of the customised forms (see layout_spec.py). Idempotent; a missing field is skipped."""
import frappe

from sig_warehouse.sig_warehouse.layout_spec import CF, PS


def execute():
    for dt, fieldname, props in CF:
        name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname})
        if not name:
            print(f"layout: skip {dt}.{fieldname} (not found)")
            continue
        doc = frappe.get_doc("Custom Field", name)
        changed = False
        for key, value in props.items():
            if doc.get(key) != value:
                doc.set(key, value)
                changed = True
        if changed:
            doc.flags.ignore_permissions = True
            doc.save()
    for dt, fieldname, prop, value, ptype in PS:
        if frappe.db.exists("DocType", dt):
            frappe.make_property_setter({"doctype": dt, "doctype_or_field": "DocField", "fieldname": fieldname,
                                         "property": prop, "value": value, "property_type": ptype})
    frappe.clear_cache()
