"""Add lifecycle metadata without changing existing cycle status or access."""
import frappe

FIELDS = (
    {"fieldname": "sig_lifecycle", "label": "Lifecycle", "fieldtype": "Select",
     "options": "\nOpen\nParked\nClosed", "read_only": 1},
    {"fieldname": "sig_parked_at", "label": "Parked At", "fieldtype": "Datetime", "read_only": 1},
    {"fieldname": "sig_parked_by", "label": "Parked By", "fieldtype": "Link", "options": "User", "read_only": 1},
    {"fieldname": "sig_park_reason", "label": "Parking Reason", "fieldtype": "Small Text", "read_only": 1},
    {"fieldname": "sig_close_outcome", "label": "Closure Outcome", "fieldtype": "Select",
     "options": "\nCompleted\nCancelled\nInvalid", "read_only": 1},
)


EVENT_FIELDS = (
    FIELDS[-1],
    {"fieldname": "sig_close_reason", "label": "Closure Reason", "fieldtype": "Small Text", "read_only": 1},
)


def execute():
    missing = []
    for doctype, fields in (("SIG Site Cycle", FIELDS), ("SIG Evidence Event", EVENT_FIELDS)):
        for spec in fields:
            filters = {"dt": doctype, "fieldname": spec["fieldname"]}
            name = frappe.db.get_value("Custom Field", filters, "name")
            if not name:
                missing.append(dict(spec, doctype="Custom Field", dt=doctype))
                continue
            existing = frappe.get_doc("Custom Field", name)
            for key in ("fieldtype", "options", "read_only", "permlevel"):
                if str(existing.get(key) or "") != str(spec.get(key) or ""):
                    frappe.throw("Cycle lifecycle field conflict: " + doctype + "." + spec["fieldname"])
    for spec in missing:
        frappe.get_doc(spec).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.clear_cache(doctype="SIG Evidence Event")
