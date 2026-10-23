"""Route evidence by canonical Site + PO + WO without adding a subproject key."""

import frappe


def rewrite(source):
    """Replace only the reviewed resolver block in the live evidence Server Script."""
    old_open = (
        "    open_rows = frappe.get_all('SIG Site Cycle', filters={'site_key': sk, 'terminal': 0},\n"
        "                               fields=['name', 'wo', 'po', 'resolution_state'], order_by='modified desc', limit_page_length=100)\n"
    )
    new_open = (
        "    open_rows = frappe.get_all('SIG Site Cycle', filters={'site_key': sk, 'terminal': 0},\n"
        "                               fields=['name', 'wo', 'po', 'resolution_state', 'project', 'erp_project'],\n"
        "                               order_by='creation asc, name asc', limit_page_length=100)\n"
    )
    if source.count(old_open) != 1:
        raise ValueError("Evidence resolver's open-cycle query changed; inspect it before migration.")
    source = source.replace(old_open, new_open, 1)

    start = "    elif wo:\n"
    end = "    created_cycle = 0\n"
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("Evidence resolver branch markers changed; inspect it before migration.")
    before, rest = source.split(start, 1)
    _old, after = rest.split(end, 1)
    replacement = """    elif wo:
        filters = {'wo': wo, 'site_key': sk, 'terminal': 0}
        if po:
            filters['po'] = po
        rows = frappe.get_all('SIG Site Cycle', filters=filters, fields=['name'],
                              order_by='creation desc, name desc', limit_page_length=2)
        if len(rows) == 1:
            cyc = rows[0].name
        elif len(rows) > 1:
            frappe.response['message'] = {'result': 'exception',
                'reason': 'CYCLE_ATTRIBUTION:several active cycles share this Site/PO/WO; select one explicitly'}
            return
        elif event_code == 'SITE_CLOSED':
            closed_filters = {'wo': wo, 'site_key': sk, 'terminal': 1}
            if po:
                closed_filters['po'] = po
            prior = frappe.get_all('SIG Site Cycle', filters=closed_filters, fields=['name'],
                                   order_by='creation desc, name desc', limit_page_length=1)
            if prior:
                cyc = prior[0].name
        else:
            closed_filters = {'wo': wo, 'site_key': sk, 'terminal': 1}
            if po:
                closed_filters['po'] = po
            closed_exact_scope = bool(frappe.db.exists('SIG Site Cycle', closed_filters))
        if not po and cyc is None:
            frappe.response['message'] = {'result': 'exception',
                'reason': 'CYCLE_ATTRIBUTION:WO without PO needs a unique existing cycle'}
            return
        if cyc is None and not closed_exact_scope:
            adoptable = []
            for r0 in blank_open:
                if r0.resolution_state == 'AMBIGUOUS':
                    continue
                if po and r0.po and str(r0.po).strip() != po:
                    continue
                adoptable.append(r0)
            pick = None
            if po:
                same_po = []
                for r0 in adoptable:
                    if r0.po == po:
                        same_po.append(r0)
                if len(same_po) == 1:
                    pick = same_po[0]
                elif len(same_po) > 1:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:several temporary cycles match this PO; select one explicitly'}
                    return
            if pick is None and len(adoptable) == 1:
                pick = adoptable[0]
            if pick is not None:
                cyc = pick.name
    else:
        shared_preparation = event_code in ('TCN_GENERATED', 'MIR_CONFIRMED', 'FIELD_VISIT_COMPLETED')
        if shared_preparation:
            if po:
                rows = frappe.get_all('SIG Site Cycle',
                    filters={'po': po, 'site_key': sk, 'terminal': 0}, fields=['name'],
                    order_by='creation asc, name asc', limit_page_length=100)
                if rows:
                    # The owner accepts one deterministic Site-PO target for shared
                    # preparation. Separate WO documents and cycles remain separate.
                    cyc = rows[0].name
                else:
                    blank_po = []
                    for r0 in blank_open:
                        if r0.wo or r0.resolution_state == 'AMBIGUOUS' or r0.po:
                            continue
                        blank_po.append(r0)
                    if len(blank_po) == 1:
                        cyc = blank_po[0].name
                    else:
                        closed_exact_scope = bool(frappe.db.exists('SIG Site Cycle',
                            {'po': po, 'site_key': sk, 'terminal': 1}))
                        if len(blank_po) > 1:
                            frappe.response['message'] = {'result': 'exception',
                                'reason': 'CYCLE_ATTRIBUTION:several unassigned site cycles; select one in Site Visits'}
                            return
            else:
                expected_family = ''
                project_key = project.lower()
                if 'incident' in project_key:
                    expected_family = 'incident'
                elif 'capex' in project_key:
                    expected_family = 'capex'
                elif '5g' in project_key or 'colo' in project_key:
                    expected_family = '5g'
                compatible = []
                project_meta = frappe.get_meta('Project')
                family_fields = []
                available_family_fields = []
                for field_row in project_meta.get('fields') or []:
                    available_family_fields.append(field_row.get('fieldname'))
                for candidate_field in ('custom_project_family', 'custom_family'):
                    if candidate_field in available_family_fields:
                        family_fields.append(candidate_field)
                for r0 in open_rows:
                    actual_family = ''
                    for family_field in family_fields:
                        if r0.erp_project and not actual_family:
                            actual_family = str(frappe.db.get_value('Project', r0.erp_project, family_field) or '').lower()
                    if not actual_family:
                        actual_family = str(r0.project or '').lower()
                    if 'incident' in actual_family:
                        actual_family = 'incident'
                    elif 'capex' in actual_family:
                        actual_family = 'capex'
                    elif '5g' in actual_family or 'colo' in actual_family:
                        actual_family = '5g'
                    if expected_family and actual_family and expected_family != actual_family:
                        continue
                    compatible.append(r0)
                if len(compatible) == 1:
                    cyc = compatible[0].name
                elif len(compatible) > 1:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:several compatible site cycles; select one in Site Visits'}
                    return
                else:
                    frappe.response['message'] = {'result': 'exception',
                        'reason': 'CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits'}
                    return
        elif event_code not in ('GCL_GENERATED', 'FIS_GENERATED', 'MGCL_GENERATED', 'INVOICE_GENERATED', 'SITE_CLOSED'):
            # Preserve entry into the pipeline for BOQ/Mapping/Tags/photo and
            # other legacy non-financial events. A supplied PO is still binding.
            if po:
                matching = []
                for r0 in open_rows:
                    if str(r0.po or '').strip() == po:
                        matching.append(r0)
                if matching:
                    cyc = matching[0].name
                else:
                    closed_exact_scope = bool(frappe.db.exists('SIG Site Cycle',
                        {'po': po, 'site_key': sk, 'terminal': 1}))
                    unassigned = []
                    for r0 in blank_open:
                        if not r0.po and r0.resolution_state != 'AMBIGUOUS':
                            unassigned.append(r0)
                    if not closed_exact_scope and len(unassigned) == 1:
                        cyc = unassigned[0].name
            elif len(open_rows) == 1:
                cyc = open_rows[0].name
            elif blank_open:
                cyc = blank_open[0].name
                if len(real_open) >= 2:
                    resolution = 'AMBIGUOUS'
            elif len(real_open) >= 2:
                resolution = 'AMBIGUOUS'
        elif po:
            # Non-shared evidence without a WO may use only one PO-only cycle.
            # A cycle belonging to one of several real WOs is not a safe target.
            if event_code == 'SITE_CLOSED':
                frappe.response['message'] = {'result': 'exception',
                    'reason': 'CYCLE_ATTRIBUTION:select the exact cycle before closure'}
                return
            rows = frappe.get_all('SIG Site Cycle',
                filters={'po': po, 'site_key': sk, 'wo': '', 'terminal': 0}, fields=['name'],
                order_by='creation asc, name asc', limit_page_length=2)
            if len(rows) == 1:
                cyc = rows[0].name
            else:
                frappe.response['message'] = {'result': 'exception',
                    'reason': 'CYCLE_ATTRIBUTION:this evidence needs its WO or an explicit cycle selection'}
                return
        else:
            frappe.response['message'] = {'result': 'exception',
                'reason': 'CYCLE_ATTRIBUTION:this evidence needs a PO, WO or explicit cycle selection'}
            return

"""
    return before + replacement + end + after


def execute():
    name = "register_evidence_event"
    if not frappe.db.exists("Server Script", name):
        frappe.throw("Cannot align Operations evidence routing: register_evidence_event is missing.")
    source = frappe.db.get_value("Server Script", name, "script") or ""
    try:
        updated = rewrite(source)
    except ValueError as error:
        frappe.throw(str(error))
    frappe.db.set_value("Server Script", name, "script", updated)
