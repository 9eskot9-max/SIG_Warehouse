"""Settings for the weekly PM check, on SIG Field Ops Settings. Off until someone switches it on."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

FIELDS = [
    {"fieldname": "pm_weekly_section", "label": "Weekly PM check", "fieldtype": "Section Break", "collapsible": 1},
    {"fieldname": "pm_weekly_mode", "label": "Weekly PM check mode", "fieldtype": "Select", "options": "Off\nTest\nLive",
     "default": "Off", "description": "Off: nothing is sent. Test: messages go to the Maytapi test number. Live: to each PM. Sent once a week, on Sunday."},
    {"fieldname": "pm_weekly_hour", "label": "Send from hour (Riyadh, Sunday)", "fieldtype": "Int", "default": "8"},
]


def execute():
    if not frappe.db.exists("DocType", "SIG Field Ops Settings"):
        return
    previous = "nv_exclude" if frappe.db.exists("Custom Field", {"dt": "SIG Field Ops Settings", "fieldname": "nv_exclude"}) else None
    for field in FIELDS:
        if not frappe.db.exists("Custom Field", {"dt": "SIG Field Ops Settings", "fieldname": field["fieldname"]}):
            create_custom_field("SIG Field Ops Settings", {**field, **({"insert_after": previous} if previous else {})})
        previous = field["fieldname"]
    frappe.clear_cache(doctype="SIG Field Ops Settings")
