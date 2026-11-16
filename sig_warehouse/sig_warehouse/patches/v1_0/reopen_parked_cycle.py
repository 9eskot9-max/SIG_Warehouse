"""Add guarded reopening after accepted new evidence; retain EV1 endpoint."""
import frappe

MARKER = "    # SIG_PARKED_REOPEN_V1\n"
ANCHOR = "    ev.insert(ignore_permissions=True)\n"
SAVE_ANCHOR = "    cycdoc.save(ignore_permissions=True)\n"
VISIT_ANCHOR = "                cycdoc.set('sessions_auto_closed', (cycdoc.get('sessions_auto_closed') or 0) + 1)\n"
VISIT_BLOCK = '''                # SIG_ESTIMATED_VISIT_CHECKPOINT_V1
                fv = cycdoc.get('first_visit_at')
                if not fv or v_start < str(fv)[:19]:
                    cycdoc.set('first_visit_at', v_start)
                lv = cycdoc.get('last_visit_at')
                if not lv or v_start > str(lv)[:19]:
                    cycdoc.set('last_visit_at', v_start)
'''
BLOCK = '''    # SIG_PARKED_REOPEN_V1
    reopen_now = False
    if cycdoc.get('terminal'):
        cycdoc.set('sig_lifecycle', 'Closed')
    elif cycdoc.get('sig_lifecycle') == 'Parked':
        reopen_now = event_code in ('TCN_GENERATED', 'FIELD_VISIT_COMPLETED')
        if not reopen_now and cycdoc.get('sig_parked_at'):
            parked_at = frappe.utils.get_datetime(cycdoc.get('sig_parked_at'))
            received_at = frappe.utils.get_datetime(frappe.utils.now())
            reopen_now = received_at > frappe.utils.add_to_date(parked_at, days=30, as_datetime=True)
        if reopen_now:
            cycdoc.set('sig_lifecycle', 'Open')
'''
AUDIT_BLOCK = '''    if reopen_now:
        frappe.get_doc({'doctype': 'Comment', 'comment_type': 'Info',
            'reference_doctype': 'SIG Site Cycle', 'reference_name': cyc,
            'content': 'Reopened automatically after ' + event_code}).insert(ignore_permissions=True)
'''


def rewrite(source):
    if '# SIG_ESTIMATED_VISIT_CHECKPOINT_V1' not in source:
        if source.count(VISIT_ANCHOR) != 1:
            raise ValueError("Estimated visit anchor is missing or ambiguous")
        source = source.replace(VISIT_ANCHOR, VISIT_ANCHOR + VISIT_BLOCK, 1)
    if source.count(MARKER) == 1:
        return source
    if MARKER in source or source.count(ANCHOR) != 1 or source.count(SAVE_ANCHOR) != 1:
        raise ValueError("Evidence writer anchor is missing or ambiguous")
    if not (source.index("dup_cycle =") < source.index(SAVE_ANCHOR)
            < source.index(ANCHOR) < source.index("    frappe.db.commit()", source.index(ANCHOR))):
        raise ValueError("Unexpected evidence writer ordering")
    source = source.replace(SAVE_ANCHOR, BLOCK + SAVE_ANCHOR, 1)
    return source.replace(ANCHOR, ANCHOR + AUDIT_BLOCK, 1)


def execute():
    name = "register_evidence_event"
    source = frappe.db.get_value("Server Script", name, "script") or ""
    updated = rewrite(source)
    if updated != source:
        frappe.db.set_value("Server Script", name, "script", updated)
