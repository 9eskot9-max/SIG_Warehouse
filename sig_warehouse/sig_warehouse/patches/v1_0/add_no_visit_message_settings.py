"""Settings for the daily no-visit WhatsApp message, on SIG Field Ops Settings. The message stays Off until switched on."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

FIELDS = [
    {"fieldname": "nv_section", "label": "No-visit message", "fieldtype": "Section Break", "collapsible": 1},
    {"fieldname": "nv_mode", "label": "No-visit message mode", "fieldtype": "Select", "options": "Off\nTest\nLive",
     "default": "Off", "description": "Off: nothing is sent. Test: every message goes to the Maytapi test number. Live: to each person."},
    {"fieldname": "nv_hour", "label": "Send after hour (Riyadh)", "fieldtype": "Int", "default": "19"},
    {"fieldname": "nv_lookback_days", "label": "Active in the last N days", "fieldtype": "Int", "default": "14",
     "description": "Only people with a field visit or session in this period are messaged."},
    {"fieldname": "nv_include", "label": "Also message (Employee IDs)", "fieldtype": "Small Text",
     "description": "Employees to include even without recent visits. Separate IDs with commas or new lines."},
    {"fieldname": "nv_exclude", "label": "Never message (Employee IDs)", "fieldtype": "Small Text"},
]


def execute():
    if not frappe.db.exists("DocType", "SIG Field Ops Settings"):
        return
    previous = "feed_alert_user" if frappe.db.exists("Custom Field", {"dt": "SIG Field Ops Settings", "fieldname": "feed_alert_user"}) else None
    for field in FIELDS:
        if not frappe.db.exists("Custom Field", {"dt": "SIG Field Ops Settings", "fieldname": field["fieldname"]}):
            create_custom_field("SIG Field Ops Settings", {**field, **({"insert_after": previous} if previous else {})})
        previous = field["fieldname"]
    frappe.clear_cache(doctype="SIG Field Ops Settings")
