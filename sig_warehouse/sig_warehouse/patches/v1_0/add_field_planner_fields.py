"""Add the fields the weekly field planner reads.

SIG Site gets coordinates as `site_latitude`/`site_longitude` (one-way copy of SitesDB, which stays the master;
the names avoid the orphan `latitude`/`longitude` columns left in tabSIG Site by the 2026-09 import,
whose old values cannot be converted to Float) and SIG Site Cycle gets
a PM hold/visited mark. No permission, role or Page setting changes.
"""
import frappe

FIELDS = [
    {"dt": "SIG Site", "fieldname": "geo_section", "label": "Location", "fieldtype": "Section Break",
     "insert_after": "default_warehouse", "collapsible": 1},
    {"dt": "SIG Site", "fieldname": "site_latitude", "label": "Latitude", "fieldtype": "Float", "precision": "6",
     "read_only": 1, "in_list_view": 1, "insert_after": "geo_section",
     "description": "Copied from SitesDB by the planner geo import. Edit SitesDB, not this field."},
    {"dt": "SIG Site", "fieldname": "site_longitude", "label": "Longitude", "fieldtype": "Float", "precision": "6",
     "read_only": 1, "in_list_view": 1, "insert_after": "site_latitude"},
    {"dt": "SIG Site", "fieldname": "geo_source", "label": "Location Source", "fieldtype": "Data", "read_only": 1,
     "in_standard_filter": 1, "insert_after": "site_longitude"},
    {"dt": "SIG Site Cycle", "fieldname": "plan_hold", "label": "Planner Mark", "fieldtype": "Select",
     "options": "\nHold\nVisited\nMust", "insert_after": "delay_note",
     "description": "Hold keeps the cycle out of the weekly field plan; Visited records a visit that was not reported; Must puts the cycle first in the weekly plan."},
    {"dt": "SIG Site Cycle", "fieldname": "plan_hold_note", "label": "Planner Mark Note", "fieldtype": "Data",
     "insert_after": "plan_hold"},
]


def execute():
    for spec in FIELDS:
        existing = frappe.db.get_value("Custom Field", {"dt": spec["dt"], "fieldname": spec["fieldname"]}, "name")
        if existing:
            field = frappe.get_doc("Custom Field", existing)
            if field.fieldtype != spec["fieldtype"]:
                frappe.throw("%s.%s exists as %s; review it before migration." % (spec["dt"], spec["fieldname"], field.fieldtype))
            continue
        frappe.get_doc(dict(spec, doctype="Custom Field")).insert(ignore_permissions=True)
    for doctype in {spec["dt"] for spec in FIELDS}:
        frappe.clear_cache(doctype=doctype)
