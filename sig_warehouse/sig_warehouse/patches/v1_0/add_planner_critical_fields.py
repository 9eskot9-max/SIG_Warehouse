"""Add read-only source fields used by the reviewed RV80 critical-site sync."""
import frappe


FIELDS = [
    {
        "dt": "SIG Site",
        "fieldname": "planner_critical_status",
        "label": "Planner Critical Status",
        "fieldtype": "Select",
        "options": "\nCritical\nUnknown",
        "read_only": 1,
        "insert_after": "geo_source",
    },
    {
        "dt": "SIG Site",
        "fieldname": "planner_critical_source",
        "label": "Planner Critical Source",
        "fieldtype": "Data",
        "read_only": 1,
        "insert_after": "planner_critical_status",
    },
]


def execute():
    for spec in FIELDS:
        existing = frappe.db.get_value(
            "Custom Field", {"dt": spec["dt"], "fieldname": spec["fieldname"]}, "name"
        )
        if existing:
            field = frappe.get_doc("Custom Field", existing)
            if field.fieldtype != spec["fieldtype"]:
                frappe.throw(
                    "{0}.{1} exists as {2}; review it before migration.".format(
                        spec["dt"], spec["fieldname"], field.fieldtype
                    )
                )
            continue
        frappe.get_doc(dict(spec, doctype="Custom Field")).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="SIG Site")
