"""Persist verified RV80-exported TCN windows on individual evidence events.

The existing server script remains the evidence owner. Only explicitly marked
new payloads are accepted; old raw TCN sheet values are never backfilled as
verified windows. This patch does not change DocType or Page permissions.
"""
import frappe

FIELDS = (
    {"dt": "SIG Evidence Event", "fieldname": "tcn_window_start", "label": "TCN Window Start",
     "fieldtype": "Datetime", "read_only": 1},
    {"dt": "SIG Evidence Event", "fieldname": "tcn_window_end", "label": "TCN Window End",
     "fieldtype": "Datetime", "read_only": 1},
    {"dt": "SIG Evidence Event", "fieldname": "tcn_window_kind", "label": "TCN Window Kind",
     "fieldtype": "Select", "options": "\nNormal\nCritical Project\nCritical Incident", "read_only": 1},
)

MARKER = "# SIG_EFFECTIVE_TCN_WINDOW_V1"
ANCHOR = "    ev.insert(ignore_permissions=True)"
INSERTION = '''    # SIG_EFFECTIVE_TCN_WINDOW_V1
    if event_code == 'TCN_GENERATED' and str(frappe.form_dict.get('tcn_window_source') or '') == 'rv80_export_v1':
        tcn_start = str(frappe.form_dict.get('tcn_window_start') or '').strip()
        tcn_end = str(frappe.form_dict.get('tcn_window_end') or '').strip()
        tcn_kind = str(frappe.form_dict.get('tcn_window_kind') or '').strip()
        if not tcn_start or not tcn_end or tcn_kind not in ('Normal', 'Critical Project', 'Critical Incident'):
            frappe.throw('Incomplete effective TCN window; evidence was not saved.')
        start_value = frappe.utils.get_datetime(tcn_start)
        end_value = frappe.utils.get_datetime(tcn_end)
        if end_value <= start_value:
            frappe.throw('Invalid effective TCN window; evidence was not saved.')
        ev.set('tcn_window_start', start_value)
        ev.set('tcn_window_end', end_value)
        ev.set('tcn_window_kind', tcn_kind)
'''


def rewrite(source):
    if MARKER in source:
        return source
    if source.count(ANCHOR) != 1:
        raise ValueError("Evidence writer anchor is missing or ambiguous; review the live script before migration.")
    return source.replace(ANCHOR, INSERTION + ANCHOR, 1)


def execute():
    for spec in FIELDS:
        name = frappe.db.get_value("Custom Field", {"dt": spec["dt"], "fieldname": spec["fieldname"]}, "name")
        if name:
            if frappe.db.get_value("Custom Field", name, "fieldtype") != spec["fieldtype"]:
                frappe.throw("Unexpected existing field type for %s.%s" % (spec["dt"], spec["fieldname"]))
        else:
            frappe.get_doc(dict(spec, doctype="Custom Field")).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="SIG Evidence Event")
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Cannot update TCN evidence: register_evidence_event is missing.")
    try:
        source = rewrite(frappe.db.get_value("Server Script", name, "script") or "")
    except ValueError as error:
        frappe.throw(str(error))
    frappe.db.set_value("Server Script", name, "script", source)
