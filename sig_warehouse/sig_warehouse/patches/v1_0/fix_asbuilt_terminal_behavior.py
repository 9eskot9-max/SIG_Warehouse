import frappe


def execute():
    """Keep As-Built BOQ as a milestone; only explicit SITE_CLOSED is terminal."""
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Cannot update Operations evidence intake: register_evidence_event is missing.")

    script = frappe.db.get_value("Server Script", name, "script") or ""
    old_close = """if event_code == 'ASBUILT_BOQ_GENERATED' or event_code == 'SITE_CLOSED':
        if not cycdoc.get('terminal'):
            cycdoc.set('terminal', 1)
            cycdoc.set('closed_on', occurred_date)
        if event_code == 'SITE_CLOSED':
            if operator:
                cycdoc.set('closed_by', operator)"""
    new_close = """if event_code == 'SITE_CLOSED':
        if not cycdoc.get('terminal'):
            cycdoc.set('terminal', 1)
            cycdoc.set('closed_on', occurred_date)
        if operator:
            cycdoc.set('closed_by', operator)"""
    old_stage = "if cycdoc.get('terminal') or cycdoc.get('asbuilt_at'):"
    new_stage = "if cycdoc.get('terminal'):"

    if old_close in script:
        script = script.replace(old_close, new_close, 1)
    elif new_close not in script:
        frappe.throw("Evidence closeout logic changed; refusing an unreviewed Server Script rewrite.")

    if old_stage in script:
        script = script.replace(old_stage, new_stage, 1)
    elif new_stage not in script:
        frappe.throw("Evidence stage logic changed; refusing an unreviewed Server Script rewrite.")

    frappe.db.set_value("Server Script", name, "script", script)

