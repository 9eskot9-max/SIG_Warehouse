"""Keep explicit closure historical when later evidence arrives for the same scope."""

import frappe


def rewrite(script):
    """Change only the verified cycle-selection block in register_evidence_event."""
    old = "    FIELD_DELIVERY = ('FIELD_VISIT_COMPLETED', 'TCN_GENERATED', 'MIR_CONFIRMED')\n\n"
    replacement = (
        "    # A new accepted work event after SITE_CLOSED starts a fresh cycle.\n"
        "    # Repeated EventIds are rejected before cycle selection.\n\n"
    )
    if script.count(old) != 1:
        raise ValueError("Evidence intake header changed; review the live Server Script before migrating.")
    script = script.replace(old, replacement, 1)

    old = "    cyc = None\n    resolution = ''\n    if wo:\n"
    replacement = "    cyc = None\n    resolution = ''\n    closed_exact_scope = False\n    if wo:\n"
    if script.count(old) != 1:
        raise ValueError("Evidence scope selection changed; review the live Server Script before migrating.")
    script = script.replace(old, replacement, 1)

    old = (
        "        rows = frappe.get_all('SIG Site Cycle', filters={'wo': wo, 'site_key': sk},\n"
        "                              fields=['name', 'terminal'], order_by='modified desc', limit_page_length=1)\n"
        "        if rows:\n"
        "            if (not rows[0].terminal) or (event_code not in FIELD_DELIVERY):\n"
        "                cyc = rows[0].name\n"
        "        if cyc is None:\n"
    )
    replacement = (
        "        rows = frappe.get_all('SIG Site Cycle', filters={'wo': wo, 'site_key': sk, 'terminal': 0},\n"
        "                              fields=['name'], order_by='modified desc', limit_page_length=1)\n"
        "        if rows:\n"
        "            cyc = rows[0].name\n"
        "        elif event_code == 'SITE_CLOSED':\n"
        "            prior = frappe.get_all('SIG Site Cycle', filters={'wo': wo, 'site_key': sk, 'terminal': 1},\n"
        "                                   fields=['name'], order_by='modified desc', limit_page_length=1)\n"
        "            if prior:\n"
        "                cyc = prior[0].name\n"
        "        else:\n"
        "            closed_exact_scope = bool(frappe.db.exists('SIG Site Cycle',\n"
        "                {'wo': wo, 'site_key': sk, 'terminal': 1}))\n"
        "        if cyc is None and not closed_exact_scope:\n"
    )
    if script.count(old) != 1:
        raise ValueError("Evidence WO selection changed; review the live Server Script before migrating.")
    script = script.replace(old, replacement, 1)

    old = (
        "            rows = frappe.get_all('SIG Site Cycle', filters={'po': po, 'site_key': sk},\n"
        "                                  fields=['name', 'terminal'], order_by='modified desc', limit_page_length=1)\n"
        "            if rows:\n"
        "                if (not rows[0].terminal) or (event_code not in FIELD_DELIVERY):\n"
        "                    cyc = rows[0].name\n"
        "        if cyc is None:\n"
    )
    replacement = (
        "            rows = frappe.get_all('SIG Site Cycle', filters={'po': po, 'site_key': sk, 'terminal': 0},\n"
        "                                  fields=['name'], order_by='modified desc', limit_page_length=1)\n"
        "            if rows:\n"
        "                cyc = rows[0].name\n"
        "            elif event_code == 'SITE_CLOSED':\n"
        "                prior = frappe.get_all('SIG Site Cycle', filters={'po': po, 'site_key': sk, 'terminal': 1},\n"
        "                                       fields=['name'], order_by='modified desc', limit_page_length=1)\n"
        "                if prior:\n"
        "                    cyc = prior[0].name\n"
        "            else:\n"
        "                closed_exact_scope = bool(frappe.db.exists('SIG Site Cycle',\n"
        "                    {'po': po, 'site_key': sk, 'terminal': 1}))\n"
        "        if cyc is None and not closed_exact_scope:\n"
    )
    if script.count(old) != 1:
        raise ValueError("Evidence PO selection changed; review the live Server Script before migrating.")
    return script.replace(old, replacement, 1)


def execute():
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Cannot update Operations evidence intake: register_evidence_event is missing.")
    script = frappe.db.get_value("Server Script", name, "script") or ""
    try:
        updated = rewrite(script)
    except ValueError as error:
        frappe.throw(str(error))
    frappe.db.set_value("Server Script", name, "script", updated)
