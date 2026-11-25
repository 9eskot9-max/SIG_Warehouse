"""Keep each TCN's visit type (TCN-MDT column I, Remarks) on its own evidence event.

Until now planned_activity was only written to the Site Cycle, where the next TCN overwrote
it. SIG Field Visit also gains a PAT activity so a TCN-labelled acceptance visit can be
saved. No permissions change; old events are not backfilled (their type was never stored).
"""
import frappe

FIELD = {"dt": "SIG Evidence Event", "fieldname": "planned_activity", "label": "Planned Activity (TCN Remarks)",
         "fieldtype": "Data", "read_only": 1, "insert_after": "tcn_window_kind"}
MARKER = "# SIG_TCN_VISIT_TYPE_V1"
ANCHOR = "    ev.insert(ignore_permissions=True)"
INSERTION = '''    # SIG_TCN_VISIT_TYPE_V1
    if event_code == 'TCN_GENERATED':
        ev.set('planned_activity', str(frappe.form_dict.get('planned_activity') or '').strip().upper()[:40])
'''


def rewrite(source):
    if MARKER in source:
        return source
    if source.count(ANCHOR) != 1:
        raise ValueError("Evidence writer anchor is missing or ambiguous; review the live script before migration.")
    return source.replace(ANCHOR, INSERTION + ANCHOR, 1)


def add_option(options, value):
    items = (options or "").split("\n")
    return options if value in items else "\n".join(items + [value])


def execute():
    script = "register_evidence_event"
    if not frappe.db.exists("Server Script", script):
        frappe.throw("Cannot store the TCN visit type: register_evidence_event is missing.")
    original = frappe.db.get_value("Server Script", script, "script") or ""
    try:
        source = rewrite(original)
    except ValueError as error:
        frappe.throw(str(error))

    # Validate metadata before inserting the Custom Field, which can change the schema.
    row = frappe.db.get_value("DocField", {"parent": "SIG Field Visit", "fieldname": "activity_code"},
                              ["name", "fieldtype", "options"], as_dict=True)
    if not row or row.fieldtype != "Select":
        frappe.throw("SIG Field Visit.activity_code is not the expected Select; review before migration.")

    name = frappe.db.get_value("Custom Field", {"dt": FIELD["dt"], "fieldname": FIELD["fieldname"]}, "name")
    if name:
        if frappe.db.get_value("Custom Field", name, "fieldtype") != FIELD["fieldtype"]:
            frappe.throw("Unexpected existing field type for SIG Evidence Event.planned_activity")
    else:
        frappe.get_doc(dict(FIELD, doctype="Custom Field")).insert(ignore_permissions=True)

    # SIG Field Visit is a site-owned DocType (custom=1), so its DocField is the source to change.
    options = add_option(row.options, "PAT")
    if options != row.options:
        frappe.db.set_value("DocField", row.name, "options", options, update_modified=False)
    if source != original:
        frappe.db.set_value("Server Script", script, "script", source)
    for doctype in ("SIG Evidence Event", "SIG Field Visit"):
        frappe.clear_cache(doctype=doctype)
