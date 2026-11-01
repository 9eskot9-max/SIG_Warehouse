"""Release submitted unsent MIRs even when the warehouse rollup is partial.

The endpoint's existing unsent, source ID and docstatus gates remain intact.
Refuse unknown source instead of replacing the server script wholesale.
"""

OLD_RV80 = "is_rv80 = source_id.startswith('SIG-MIR-') and mr.docstatus == 1 and state in ('DRAFT_CREATED', 'REVIEW_REQUIRED', 'MR_SUBMITTED')"
NEW_RV80 = "is_rv80 = source_id.startswith('SIG-MIR-') and mr.docstatus == 1"
OLD_ERP = "is_erp = source_id.startswith('ERP-MR-') and mr.docstatus == 1 and state == 'MR_SUBMITTED'"
NEW_ERP = "is_erp = source_id.startswith('ERP-MR-') and mr.docstatus == 1"


def rewrite(source):
    lines = source.splitlines(keepends=True)
    seen = {NEW_RV80: 0, NEW_ERP: 0}
    out = []
    for line in lines:
        body = line.strip()
        if body in (OLD_RV80, OLD_ERP):
            replacement = NEW_RV80 if body == OLD_RV80 else NEW_ERP
            line = line.replace(body, replacement, 1)
            body = replacement
        if body in seen:
            seen[body] += 1
        out.append(line)
    if any(count != 1 for count in seen.values()):
        raise ValueError('Unexpected sig_list_ready_mrs source; review before migration')
    return ''.join(out)


def execute():
    import frappe

    name = 'sig_list_ready_mrs'
    if not frappe.db.exists('Server Script', name):
        frappe.throw('Cannot update warehouse feed: sig_list_ready_mrs is missing.')
    source = frappe.db.get_value('Server Script', name, 'script') or ''
    try:
        updated = rewrite(source)
    except ValueError as exc:
        frappe.throw(str(exc))
    if updated != source:
        frappe.db.set_value('Server Script', name, 'script', updated)
        frappe.clear_cache(doctype='Server Script')

