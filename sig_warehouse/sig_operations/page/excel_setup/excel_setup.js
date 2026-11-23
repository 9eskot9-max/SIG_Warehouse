frappe.pages['excel-setup'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Excel Setup'), single_column: true});
    const method = 'sig_warehouse.sig_operations.excel_setup.';
    const poSetupMethod = 'sig_warehouse.sig_operations.excel_setup_v3.';
    const root = $('<div class="sig-excel-setup"></div>').appendTo(page.main);
    let state, poState = null, selected = 'family_tawal_defaults', dirty = false, peopleState = null, routingState = null, routingDirty = false, poSetupButton = null;
    const peopleLabels = {employees: __('Employees'), pc_routing: __('Employee petty cash routing'), project_assignments: __('Employee project assignments'), reporter_maps: __('Field reporter mappings'), candidates: __('Candidate onboarding'), onboarding: __('Employee onboarding checks')};
    const labels = {projects: __('Projects in workbook sync'), family_tawal_defaults: __('TAWAL PM by family'),
        ops_team_members: __('Operations team (PM, coordinator, Warehouse)'), operational_teams: __('Field crews'), team_memberships: __('Crew leader and members (dated)'),
        tag_definitions: __('Tags definitions'), tag_upl_links: __('Tags to UPL'), material_upl_links: __('Item to UPL'), builder_defaults: __('TCN wording and defaults'),
        pc_family_defaults: __('Petty cash family defaults')};
    // Each area names what its Publish button changes. Every list still publishes as one setup revision.
    const setupGroups = [
        {key: 'projects', publish: __('Publish workbook setup'), label: __('Projects and TAWAL PM'), description: __('A PO takes its Project family from the ERP Project, and the family takes its dated TAWAL PM. For a one-off different PM, choose the contact in the RV80 TCN batch prompt; nothing is stored here for exceptions.'), datasets: ['family_tawal_defaults', 'projects']},
        {key: 'operations', publish: __('Publish Operations team'), label: __('Operations team'), description: __('One row per person: family (blank for Warehouse), role, optional Project exception (list the whole replacement team) and dates. This list controls who sees Workbench tasks, who is named as owner, who may close cycles and who receives the weekly PM check. A PM sees PM tasks, a coordinator coordinator tasks; Warehouse owners cover every family.'), datasets: ['ops_team_members']},
        {key: 'crews', publish: __('Publish field crews'), label: __('Field crews'), description: __('A crew is planned by the Field Planner when it is enabled and has exactly one active leader. Tick "No-visit message" to include its leader in the daily no-visit message. Staff move between crews by dated membership; cover a leader on leave with a dated row.'), datasets: ['operational_teams', 'team_memberships']},
        {key: 'mapping', publish: __('Publish workbook setup'), label: __('WhatsApp Tags and workbook mappings'), description: __('WhatsApp Tags are normalized and linked to UPL values for the workbooks. The UPL catalogue and detailed Mapping Master remain maintained in Excel; this page stores the reusable ERP-side rules.'), datasets: ['tag_definitions', 'tag_upl_links', 'material_upl_links']},
        {key: 'tcn', publish: __('Publish workbook setup'), label: __('TCN generation rules'), description: __('Wording defaults used by RV80 TCN generation. PO family selects the existing Sync MOP template in the workbook.'), datasets: ['builder_defaults']},
        {key: 'people', publish: __('Publish petty cash routing'), label: __('Petty cash and HR records'), description: __('Petty cash routing is reviewed and published separately by Finance. Employees, project assignments (an HR record with no operational effect), reporter phones and onboarding stay in their own HR records.'), datasets: ['pc_family_defaults', 'people:pc_routing', 'people:employees', 'people:project_assignments', 'people:reporter_maps', 'people:candidates', 'people:onboarding']}
    ];
    const setupGroupFor = value => setupGroups.find(group => group.datasets.includes(value)) || setupGroups[0];
    const setupControls = (group, current) => '<div class="es-tools es-navigation"><label>' + esc(__('Setup area')) + ' <select class="form-control es-group">' + setupGroups.map(item => '<option value="' + esc(item.key) + '" ' + (item.key === group.key ? 'selected' : '') + '>' + esc(item.label) + '</option>').join('') + '</select></label>' +
        '<label>' + esc(__('Configuration')) + ' <select class="form-control es-dataset">' + group.datasets.map(key => '<option value="' + esc(key) + '" ' + (key === current ? 'selected' : '') + '>' + esc(key.startsWith('people:') ? peopleLabels[key.slice(7)] : labels[key]) + '</option>').join('') + '</select></label></div>';
    const fieldLabels = {project: 'ERP Project', profile: 'Builder profile', po: 'PO / Agreement', alias: 'Builder alias', family: 'Project family',
        stream: 'Project stream', stream_alias: 'Stream alias', template: 'Word template key', internal_pm: 'Internal SIG PM', tawal_contact: 'TAWAL contact',
        contact_name: 'Contact name', contact_phone: 'Phone', contact_email: 'Email', upl_revision: 'UPL revision', enabled: 'Enabled',
        item: 'Tags item', rule: 'Matching rule', priority: 'Match priority', tag_item: 'Tags item', cuc: 'UPL CUC',
        description: 'UPL description', tag_matcher: 'Tags description qualifier', builder_rule: 'Tags normalization rule',
        item_code: 'ERP item code', source_uom: 'ERP unit', target_uom: 'Mapping unit', treatment: 'Treatment',
        quantity_basis: 'Reviewed quantity basis', origin: 'Imported source', leader: 'Team leader (employee)', team: 'Team', team_name: 'Team name', employee: 'Employee', role: 'Role', weekly_pm: 'Weekly PM check', no_visit_message: 'No-visit message', review_group: 'Default review group', effective_from: 'Effective from', effective_to: 'Effective to', mode: 'Contact rule', phone: 'Phone', archetype: 'Archetype', kind: 'Setting type', key: 'Match value', value: 'Output value', value2: 'Additional value'};
    const optionLabels = {purpose_reason: 'TCN purpose and reason', csv_remarks: 'TCN CSV wording', tms_implementer: 'TMS implementer'};
    const referenceFields = {
        projects: {project: 'projects'},
        material_upl_links: {item_code: 'items', target_uom: 'uoms'},
        family_tawal_defaults: {tawal_contact: 'active_contacts'},
        team_memberships: {team: 'operational_teams', employee: 'employees'},
        ops_team_members: {project: 'projects', employee: 'employees'}
    };
    const referenceLabel = (type, row) => {
        if (type === 'projects') return [row.project_name, row.name].filter(Boolean).join(' · ');
        if (type === 'contacts' || type === 'active_contacts') return [row.full_name, row.name].filter(Boolean).join(' · ');
        if (type === 'operational_teams') return [row.team_name, row.family, row.name].filter(Boolean).join(' · ');
        if (type === 'items') return [row.item_name, row.name, row.stock_uom].filter(Boolean).join(' · ');
        if (type === 'employees') return [row.employee_name, row.name].filter(Boolean).join(' · ');
        return row.name || '';
    };
    const choices = type => type === 'operational_teams'
        ? state.datasets.operational_teams.filter(row => row.enabled).map(row => ({...row, name: row.id}))
        : state.references[type] || [];
    const displayValue = (type, value) => {
        if (!value) return '';
        let row = choices(type).find(item => item.name === value);
        // Inactive contacts may still be referenced by historical rows.
        if (!row && type === 'active_contacts') row = (state.references.contacts || []).find(item => item.name === value);
        if (!row) return value;
        if (type === 'employees') return row.employee_name || value;
        if (type === 'contacts' || type === 'active_contacts') return row.full_name || value;
        if (type === 'operational_teams') return row.team_name || value;
        if (type === 'projects') return row.project_name || value;
        if (type === 'items') return row.item_name || value;
        return value;
    };
    const referenceCell = (type, value, rowIndex, field) => '<div class="es-lookup" data-ref-type="' + type + '" data-row="' + rowIndex + '" data-field="' + field + '">' +
        '<input class="form-control es-lookup-input" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" value="' + esc(displayValue(type, value)) + '" placeholder="' + esc(__('Search ERP records')) + '">' +
        '<div class="es-lookup-menu" role="listbox" hidden></div></div>';
    const referenceOptions = (type, query, rowIndex) => {
        const rows = choices(type);
        const needle = String(query || '').trim().toLocaleLowerCase();
        return rows.filter(row => !needle || referenceLabel(type, row).toLocaleLowerCase().includes(needle))
            .slice(0, 40).map(row => '<button type="button" class="es-lookup-option" role="option" data-value="' + esc(row.name) + '">' + esc(referenceLabel(type, row)) + '</button>').join('');
    };
    const openLookup = (input, showAll = false) => {
        const box = input.closest('.es-lookup');
        const menu = box.querySelector('.es-lookup-menu');
        const field = box.dataset.field;
        const canClear = (selected === 'ops_team_members' && field === 'project') || (selected === 'material_upl_links' && field === 'target_uom');
        menu.innerHTML = (canClear ? '<button type="button" class="es-lookup-option es-lookup-clear" role="option" data-value="">' + esc(__('Clear selection')) + '</button>' : '') + referenceOptions(box.dataset.refType, showAll ? '' : input.value, Number(box.dataset.row));
        menu.hidden = !menu.childElementCount;
        input.setAttribute('aria-expanded', String(!menu.hidden));
    };
    const commitLookup = (box, value) => {
        const row = state.datasets[selected][Number(box.dataset.row)], field = box.dataset.field, type = box.dataset.refType;
        if (!value && ((selected === 'ops_team_members' && field === 'project') || (selected === 'material_upl_links' && field === 'target_uom'))) {
            row[field] = '';
            dirty = true;
            render();
            return;
        }
        const source = choices(type).find(candidate => candidate.name === value);
        if (!source) return;
        row[field] = source.name;
        dirty = true;
        if (selected === 'projects' && field === 'project') {
            row.po = source.custom_agreement_no || source.custom_tawal_ba || source.custom_po_number || (/^\d+$/.test(source.name) ? source.name : '');
        } else if (selected === 'material_upl_links' && field === 'item_code') {
            const priorSourceUom = row.source_uom || '';
            row.source_uom = source.stock_uom || '';
            if (!row.target_uom || row.target_uom === priorSourceUom) row.target_uom = source.stock_uom || '';
        }
        render();
    };
    const esc = v => frappe.utils.escape_html(String(v == null ? '' : v)).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    const call = async (name, args={}) => (await frappe.call({method: method + name, args, freeze: true})).message;
    const callPoSetup = async (name, args={}) => (await frappe.call({method: poSetupMethod + name, args, freeze: true})).message;
    const render = () => {
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        if (page.btn_primary) page.btn_primary.text(setupGroupFor(selected).publish);
        if (poSetupButton) {
            if (typeof poSetupButton.toggle === 'function') poSetupButton.toggle(selected === 'projects');
            else $(poSetupButton).toggle(selected === 'projects');
        }
        if (selected.startsWith('people:')) {
            const key = selected.slice(7), result = peopleState, group = setupGroupFor(selected);
            if (key === 'pc_routing') {
                const matrix = routingState.matrix, groups = Object.keys(matrix.review_groups);
                const select = (field, value, i) => '<select class="form-control es-pc-field" data-index="' + i + '" data-pc-field="' + field + '">' + groups.map(g => '<option value="' + esc(g) + '" ' + (g === value ? 'selected' : '') + '>' + esc(matrix.review_groups[g].label || g) + '</option>').join('') + '</select>';
                root.html(setupControls(group, selected) + '<p class="es-group-note">' + esc(group.description) + '</p>' +
                    '<p class="text-warning">' + esc(__('Changes here remain a proposal until reviewed and published. Family defaults take effect when routing is republished.')) + '</p><button class="btn btn-default es-pc-preview">' + esc(__('Compare current reviewer scopes')) + '</button> <button class="btn btn-default es-pc-proposal">' + esc(__('Preview proposed changes')) + '</button> <button class="btn btn-default es-pc-history">' + esc(__('Routing history')) + '</button> <button class="btn btn-default es-pc-add">' + esc(__('Add employee')) + '</button><fieldset><div class="es-scroll"><table class="table table-bordered"><thead><tr><th>' + esc(__('Employee')) + '</th><th>' + esc(__('Name')) + '</th><th>' + esc(__('Project group')) + '</th><th>' + esc(__('PC review group')) + '</th><th>' + esc(__('Additional groups (comma separated keys)')) + '</th></tr></thead><tbody>' +
                    matrix.employees.map((row, i) => '<tr><td>' + esc(row.employee) + '</td><td>' + esc(row.employee_name) + '</td><td>' + select('work_group', row.work_group, i) + '</td><td>' + select('pc_review_group', row.pc_review_group, i) + '<span class="text-muted">' + esc(row.pc_mode === 'inherit' ? __('Family default') : __('Employee override')) + '</span> <button type="button" class="btn btn-default btn-sm es-pc-family-default" data-index="' + i + '">' + esc(__('Use family default')) + '</button></td><td><input class="form-control es-pc-field" data-index="' + i + '" data-pc-field="additional_review_groups" value="' + esc((row.additional_review_groups || []).join(', ')) + '"></td></tr>').join('') + '</tbody></table></div>' +
                    '<h4>' + esc(__('Reviewers by group')) + '</h4><p class="text-muted">' + esc(__('Separate employee names with semicolons. Reviewers must appear in the employee routing list.')) + '</p><table class="table table-bordered"><tbody>' + groups.map(g => '<tr><td>' + esc(matrix.review_groups[g].label || g) + '</td><td><input class="form-control es-pc-reviewers" data-group="' + esc(g) + '" value="' + esc((matrix.review_groups[g].reviewers || []).join('; ')) + '"></td></tr>').join('') + '</tbody></table></fieldset>');
                return;
            }
            const fields = result.fields.filter(f => f !== 'modified');
            const editable = result.can_write && ['project_assignments', 'reporter_maps'].includes(key);
            root.html(setupControls(group, selected) + '<p class="es-group-note">' + esc(group.description) + '</p>' +
                (key === 'project_assignments' && result.can_create ? '<button type="button" class="btn btn-default es-people-add">' + esc(__('Add row')) + '</button>' : '') +
                '<p class="text-muted">' + esc(key === 'project_assignments' ? __('Employee Project role records are an HR record with their own approval and history. They do not change Workbench visibility, the Planner or TCN.') : __('These are existing ERP records. Changes use their own permissions and history.')) + '</p>' +
                '<div class="es-scroll"><table class="table table-bordered"><thead><tr>' + fields.map(f => '<th>' + esc(__(fieldLabels[f] || f)) + '</th>').join('') + (editable ? '<th></th>' : '') + '</tr></thead><tbody>' +
                result.rows.map((row, i) => '<tr>' + fields.map(f => '<td>' + esc(row[f] || '') + '</td>').join('') + (editable ? '<td><button type="button" class="btn btn-default es-people-edit" data-index="' + i + '">' + esc(__('Edit')) + '</button></td>' : '') + '</tr>').join('') + '</tbody></table></div>');
            return;
        }
        const rows = state.datasets[selected];
        // UPL descriptions belong to the UPL/Mapping data; preserve existing values in the payload.
        const fields = state.fields[selected].filter(f => f !== 'id' && !(selected === 'tag_upl_links' && f === 'description'));
        const notes = {
            projects: __('Projects included in workbook sync. Family and the effective TAWAL PM are read live from the ERP Project and the family list and cannot be typed here.'),
            tag_definitions: __('Normalize and identify incoming WhatsApp Tags values. These rules are separate from the Tags-to-UPL links; changing one does not replace the other.'),
            tag_upl_links: __('Link each Tags item to its UPL code; UPL descriptions and the detailed mapping are maintained in Mapping Master Excel. Use the optional qualifier only for a matching Tags sheet description. Blank PO and revision mean a shared rule; a PO-specific rule can replace shared links for that Tags item, so review all its codes.'),
            material_upl_links: __('Link warehouse items to UPL codes for AsBuilt. Direct 1:1 requires matching units; use Manual for review and Excluded for reviewed items with no link. Blank PO and revision mean a shared rule.'),
            builder_defaults: __('RV80 TCN purpose/reason, wording and implementer defaults. MOP template choice follows PO family in the workbook.'),
            family_tawal_defaults: __('The client TAWAL PM used for every PO of a family during its dates. To change the PM from a date, end the current row the day before and add a new row. This is not the internal SIG project manager.'),
            operational_teams: __('Enabled crews appear in the Field Planner with their current leader. "No-visit message" includes the leader in the daily no-visit message.'),
            team_memberships: __('Crew leader and members with dates. Cover a leader on leave by ending their row and adding the cover; a crew needs exactly one active leader.'),
            ops_team_members: __('Role pm / coordinator / warehouse. Leave Project blank for the family team; a Project row replaces that role in the family team for that Project. Warehouse owners have no family. "Weekly PM check" applies to PMs only.'),
            pc_family_defaults: __('A default for employees who explicitly inherit it during a reviewed petty cash routing publication. Existing overrides are unchanged and no ERP permission is granted.')
        };
        const note = notes[selected] || '';
        const group = setupGroupFor(selected);
        const booleans = ['enabled', 'weekly_pm', 'no_visit_message'];
        const po = selected === 'projects' ? ((poState && poState.projects) || []).reduce((a, r) => { a[r.project] = r; return a; }, {}) : null;
        const contactName = id => { const c = ((poState && poState.contacts) || []).find(x => x.id === id); return c ? c.full_name : (id || ''); };
        const warnings = (state.warnings || []).map(w => '<li>' + esc(w) + '</li>').join('');
        root.html('<div class="es-summary"><b>' + __('Published revision') + ': ' + esc(state.revision) + '</b><span>' +
            esc(state.published_at || __('Not published')) + '</span><span>' + __('Excel workbooks refresh from this ERP setup') + '</span></div>' +
            (warnings ? '<div class="es-state-note"><b>' + esc(__('Needs attention')) + '</b><ul>' + warnings + '</ul></div>' : '') +
            setupControls(group, selected) +
            '<div class="es-tools es-actions"><button class="btn btn-default es-add">' + __('Add row') + '</button>' +
            '<button class="btn btn-default es-import">' + __('Import existing setup') + '</button>' +
            '<button class="btn btn-default es-history">' + __('Revision history') + '</button></div>' +
            '<p class="es-group-note">' + esc(group.description) + '</p>' +
            '<p class="text-muted">' + esc(note) + '</p>' +
            '<div class="es-scroll"><table class="table table-bordered"><thead><tr>' + fields.map(f => '<th>' + esc(__(fieldLabels[f] || f)) + '</th>').join('') +
            (po ? '<th>' + esc(__('Family (from ERP Project)')) + '</th><th>' + esc(__('TAWAL PM now')) + '</th>' : '') +
            '</tr></thead><tbody>' + rows.map((row, i) => '<tr>' + fields.map(f => '<td>' +
                (booleans.includes(f) ? '<input type="checkbox" data-row="' + i + '" data-field="' + f + '" ' + (row[f] ? 'checked' : '') + '>' :
                state.options[selected + '.' + f] ? '<select class="form-control" data-row="' + i + '" data-field="' + f + '"><option value=""></option>' +
                    state.options[selected + '.' + f].map(value => '<option value="' + esc(value) + '" ' + (row[f] === value ? 'selected' : '') + '>' + esc(__(f === 'archetype' && value === 'Project' ? 'DC' : (optionLabels[value] || value))) + '</option>').join('') + '</select>' :
                referenceFields[selected] && referenceFields[selected][f] ? referenceCell(referenceFields[selected][f], row[f], i, f) :
                '<input class="form-control" data-row="' + i + '" data-field="' + f + '" value="' + esc(row[f]) + '" ' +
                    (f === 'id' || (selected === 'projects' && f === 'po') || (selected === 'material_upl_links' && f === 'source_uom') ? 'readonly ' : '') + '>') + '</td>').join('') +
                (po ? '<td>' + esc((po[row.project] || {}).family_label || (po[row.project] || {}).family || __('not set on the ERP Project')) + '</td><td>' +
                    esc(contactName((po[row.project] || {}).default_contact) || __('none: no family default')) + '</td>' : '') + '</tr>').join('') + '</tbody></table></div>');
    };
    const load = async () => {
        state = await call('get_page_state');
        poState = await callPoSetup('get_po_setup_state').catch(() => null);
        if (selected === 'people:pc_routing') routingState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.get_state', freeze: true})).message;
        else if (selected.startsWith('people:')) peopleState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.get_section', args: {section: selected.slice(7)}, freeze: true})).message;
        dirty = false; routingDirty = false; render();
    };
    const selectDataset = async next => {
        if (next === 'people:pc_routing') {
            if (!routingState) { try { routingState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.get_state', freeze: true})).message; } catch (error) { render(); return; } }
        } else if (next.startsWith('people:')) {
            try { peopleState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.get_section', args: {section: next.slice(7)}, freeze: true})).message; }
            catch (error) { render(); return; }
        }
        selected = next; render();
    };
    root.on('change', '.es-group', function () {
        const group = setupGroups.find(item => item.key === this.value);
        if (group && group.datasets.length) selectDataset(group.datasets[0]);
    });
    root.on('change', '.es-dataset', function () { selectDataset(this.value); });
    root.on('change', '.es-pc-field', function () {
        const row = routingState.matrix.employees[Number(this.dataset.index)], field = this.dataset.pcField;
        if (field === 'additional_review_groups') row[field] = this.value.split(',').map(s => s.trim()).filter(Boolean);
        else { row[field] = this.value; if (field === 'pc_review_group') row.pc_mode = 'override'; }
        routingDirty = true; render();
    });
    root.on('click', '.es-pc-family-default', function () {
        const row = routingState.matrix.employees[Number(this.dataset.index)];
        const family = {capex: 'Capex', incident: 'Incident', colocation: '5G / Colocation'}[row.work_group];
        const match = (state.datasets.pc_family_defaults || []).filter(item => item.enabled && item.family === family);
        if (!family || match.length !== 1 || !routingState.matrix.review_groups[match[0].review_group]) {
            frappe.msgprint(__('Configure one valid petty cash default for this family first.')); return;
        }
        row.pc_review_group = match[0].review_group;
        row.pc_mode = 'inherit';
        row.additional_review_groups = (row.additional_review_groups || []).filter(group => group !== row.pc_review_group);
        routingDirty = true; render();
    });
    root.on('click', '.es-pc-preview', async () => {
        try {
            const result = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.preview_current_scope_change', freeze: true})).message;
            const detail = result.changes.map(row => '<tr><td>' + esc(row.employee) + '</td><td>' + esc(row.added.join(', ')) + '</td><td>' + esc(row.removed.join(', ')) + '</td></tr>').join('');
            const dialog = new frappe.ui.Dialog({title: __('Reviewer scope comparison'), fields: [{fieldname: 'details', fieldtype: 'HTML'}]});
            dialog.fields_dict.details.$wrapper.html('<p>' + esc(__('Published revision {0}: {1} additions and {2} removals compared with the existing static scope. Native roles and user permissions also apply.', [result.revision, result.added, result.removed])) + '</p><table class="table table-bordered"><thead><tr><th>' + esc(__('Employee')) + '</th><th>' + esc(__('Added reviewers')) + '</th><th>' + esc(__('Removed reviewers')) + '</th></tr></thead><tbody>' + detail + '</tbody></table>');
            dialog.show();
        } catch (error) { frappe.msgprint(esc(error.message || __('Could not compare scopes.'))); }
    });
    root.on('click', '.es-pc-proposal', async () => {
        try {
            const rows = routingState.matrix.employees.map(({employee, work_group, pc_review_group, additional_review_groups, pc_mode}) => ({employee, work_group, pc_review_group, additional_review_groups, pc_mode: pc_mode || 'override'}));
            const reviewer_groups = Object.fromEntries(Object.entries(routingState.matrix.review_groups).map(([key, value]) => [key, value.reviewers]));
            const result = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.preview_proposed_routing', args: {rows: JSON.stringify(rows), reviewer_groups: JSON.stringify(reviewer_groups), base_revision: routingState.revision}, freeze: true})).message;
            const detail = result.changes.map(row => '<tr><td>' + esc(row.employee) + '</td><td>' + esc(row.added.join(', ')) + '</td><td>' + esc(row.removed.join(', ')) + '</td></tr>').join('');
            const dialog = new frappe.ui.Dialog({title: __('Proposed reviewer changes'), fields: [{fieldname: 'details', fieldtype: 'HTML'}]});
            dialog.fields_dict.details.$wrapper.html('<p>' + esc(__('Revision {0}: {1} reviewer additions and {2} removals. This proposal has not been saved; native permissions also apply.', [result.revision, result.added, result.removed])) + '</p><table class="table table-bordered"><thead><tr><th>' + esc(__('Employee')) + '</th><th>' + esc(__('Added reviewers')) + '</th><th>' + esc(__('Removed reviewers')) + '</th></tr></thead><tbody>' + detail + '</tbody></table>');
            dialog.show();
        } catch (error) { frappe.msgprint(esc(error.message || __('Could not validate the proposal.'))); }
    });
    root.on('click', '.es-pc-history', async () => {
        const history = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.history', freeze: true})).message;
        if (!history.length) { frappe.msgprint(__('No saved prior routing revisions.')); return; }
        frappe.prompt([{fieldname: 'revision', fieldtype: 'Select', label: __('Prior revision'), options: history.map(item => String(item.revision)).join('\n'), reqd: 1}], async values => {
            const args = {revision: values.revision, base_revision: routingState.revision};
            const preview = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.preview_restore', args, freeze: true})).message;
            const detail = preview.changes.map(row => esc(row.employee) + ': +' + esc(row.added.join(', ')) + ' / −' + esc(row.removed.join(', '))).join('<br>');
            frappe.confirm(esc(__('Restore as a new revision? {0} reviewer additions and {1} removals.', [preview.added, preview.removed])) + '<br>' + detail, async () => {
                await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.restore', args: {...args, preview_hash: preview.hash}, freeze: true});
                await load();
            });
        }, __('Restore routing'), __('Preview'));
    });
    root.on('change', '.es-pc-reviewers', function () {
        routingState.matrix.review_groups[this.dataset.group].reviewers = this.value.split(';').map(s => s.trim()).filter(Boolean);
        routingDirty = true;
    });
    root.on('click', '.es-pc-import', () => {
        const dialog = new frappe.ui.Dialog({title: __('Paste existing routing'), fields: [{fieldname: 'package', fieldtype: 'Code', options: 'JSON', label: __('Routing data'), reqd: 1}], primary_action_label: __('Review rows'), primary_action: values => {
            try {
                if (values.package.length > 1000000) throw new Error(__('Routing data is too large.'));
                const data = JSON.parse(values.package), matrix = routingState.matrix;
                if (!Array.isArray(data.rows) || !data.reviewer_groups || typeof data.reviewer_groups !== 'object' || Array.isArray(data.reviewer_groups)) throw new Error(__('Invalid routing data.'));
                const groups = Object.keys(matrix.review_groups), incoming = Object.keys(data.reviewer_groups);
                if (groups.length !== incoming.length || groups.some(g => !incoming.includes(g) || !Array.isArray(data.reviewer_groups[g]))) throw new Error(__('Review groups do not match the current setup.'));
                const existing = new Map(matrix.employees.map(row => [row.employee, row])), seen = new Set();
                const rows = data.rows.map(row => {
                    if (!row || typeof row.employee !== 'string' || seen.has(row.employee) || !groups.includes(row.work_group) || !groups.includes(row.pc_review_group) || !Array.isArray(row.additional_review_groups) || row.additional_review_groups.some(g => !groups.includes(g))) throw new Error(__('Invalid or duplicate employee routing row.'));
                    seen.add(row.employee);
                    return {...(existing.get(row.employee) || {employee: row.employee, employee_name: row.employee}), work_group: row.work_group, pc_review_group: row.pc_review_group, additional_review_groups: row.additional_review_groups};
                });
                if (Array.from(existing.keys()).some(id => !seen.has(id))) throw new Error(__('The pasted data omits existing employees.'));
                matrix.employees = rows;
                groups.forEach(g => { matrix.review_groups[g].reviewers = data.reviewer_groups[g]; });
                routingDirty = true; dialog.hide(); render();
                frappe.msgprint(__('Review the imported rows and reviewers, then use Save and publish.'));
            } catch (error) { frappe.msgprint(esc(error.message)); }
        }}); dialog.show();
    });
    root.on('click', '.es-pc-add', () => frappe.prompt([{fieldname: 'employee', fieldtype: 'Link', options: 'Employee', label: __('Employee'), reqd: 1}], async values => {
        if (routingState.matrix.employees.some(row => row.employee === values.employee)) { frappe.msgprint(__('Employee already exists in routing.')); return; }
        routingState.matrix.employees.push({employee: values.employee, employee_name: values.employee, work_group: 'unassigned', pc_review_group: 'unassigned', additional_review_groups: []});
        routingDirty = true; render();
    }, __('Add employee'), __('Add')));
    root.on('click', '.es-people-edit, .es-people-add', function () {
        const key = selected.slice(7), creating = this.classList.contains('es-people-add');
        const row = creating ? {} : peopleState.rows[Number(this.dataset.index)];
        const fields = key === 'reporter_maps' ? [{fieldname: 'employee', fieldtype: 'Link', options: 'Employee', label: __('Employee')}] : [
            {fieldname: 'employee', fieldtype: 'Link', options: 'Employee', label: __('Employee'), reqd: 1},
            {fieldname: 'project', fieldtype: 'Link', options: 'Project', label: __('Project'), reqd: 1},
            {fieldname: 'project_role', fieldtype: 'Select', options: 'Team Leader\nProject Manager\nCoordinator\nSupervisor\nTeam Member\nOther', label: __('Project Role'), reqd: 1},
            {fieldname: 'start_date', fieldtype: 'Date', label: __('Start Date'), reqd: 1},
            {fieldname: 'end_date', fieldtype: 'Date', label: __('End Date')}
        ];
        fields.forEach(field => { field.default = row[field.fieldname] || ''; });
        const dialog = new frappe.ui.Dialog({title: creating ? __('Add project assignment') : __('Edit record'), fields, primary_action_label: __('Save'), primary_action: async values => {
            const method = creating ? 'create_project_assignment' : 'update_section_record';
            const args = creating ? {values: JSON.stringify(values)} : {section: key, name: row.name, modified: row.modified, values: JSON.stringify(values)};
            await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.' + method, args, freeze: true});
            peopleState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.get_section', args: {section: key}, freeze: true})).message;
            dialog.hide(); render();
        }}); dialog.show();
    });
    root.on('input change', '[data-field]:not(.es-lookup)', function (event) {
        const row = state.datasets[selected][Number(this.dataset.row)], field = this.dataset.field;
        row[field] = this.type === 'checkbox' ? this.checked : this.value;
        dirty = true;
    });
    root.on('focus', '.es-lookup-input', function () { openLookup(this, true); });
    root.on('input', '.es-lookup-input', function () { openLookup(this); });
    root.on('keydown', '.es-lookup-input', function (event) {
        const menu = this.closest('.es-lookup').querySelector('.es-lookup-menu');
        const options = Array.from(menu.querySelectorAll('.es-lookup-option'));
        let index = options.indexOf(menu.querySelector('.es-lookup-option.active'));
        if (event.key === 'ArrowDown' && options.length) { event.preventDefault(); index = (index + 1) % options.length; options.forEach(option => option.classList.remove('active')); options[index].classList.add('active'); }
        else if (event.key === 'ArrowUp' && options.length) { event.preventDefault(); index = index <= 0 ? options.length - 1 : index - 1; options.forEach(option => option.classList.remove('active')); options[index].classList.add('active'); }
        else if (event.key === 'Enter' && index >= 0) { event.preventDefault(); commitLookup(this.closest('.es-lookup'), options[index].dataset.value); }
        else if (event.key === 'Escape') { menu.hidden = true; this.setAttribute('aria-expanded', 'false'); }
    });
    root.on('mousedown', '.es-lookup-option', function (event) { event.preventDefault(); commitLookup(this.closest('.es-lookup'), this.dataset.value); });
    root.on('blur', '.es-lookup-input', function () {
        const box = this.closest('.es-lookup'), row = state.datasets[selected][Number(box.dataset.row)];
        const menu = box.querySelector('.es-lookup-menu');
        window.setTimeout(() => { if (!box.isConnected) return; this.value = displayValue(box.dataset.refType, row[box.dataset.field] || ''); menu.hidden = true; this.setAttribute('aria-expanded', 'false'); }, 120);
    });
    root.on('click', '.es-add', () => {
        const row = Object.fromEntries(state.fields[selected].map(f => [f, f === 'enabled' ? true : '']));
        row.id = crypto.randomUUID(); state.datasets[selected].push(row); dirty = true; render();
    });
    root.on('click', '.es-history', async () => {
        const rows = await call('get_history');
        const dialog = new frappe.ui.Dialog({title: __('Revision history'), fields: [{fieldname: 'history', fieldtype: 'HTML'}]});
        dialog.fields_dict.history.$wrapper.html('<table class="table"><tbody>' + rows.map(row =>
            '<tr><td>' + esc(row.revision) + '</td><td>' + esc(row.published_at) + '</td><td>' + esc(row.published_by) + '</td><td>' + esc((row.changed || []).map(name => labels[name.split(' (')[0]] ? labels[name.split(' (')[0]] + name.slice(name.indexOf(' (')) : name).join(', ')) + '</td></tr>').join('') + '</tbody></table>');
        dialog.show();
    });
    root.on('click', '.es-import', () => {
        if (dirty) { frappe.msgprint(__('Publish or reload your edits before importing.')); return; }
        const input = document.createElement('input'); input.type = 'file'; input.accept = '.json,application/json';
        input.onchange = async () => {
            try {
                const file = input.files[0]; if (!file) return;
                if (file.size > 5000000) throw new Error(__('Import is too large.'));
                const packageValue = JSON.parse((await file.text()).replace(/^\uFEFF/, ''));
                const preview = await call('preview_import', {package: JSON.stringify(packageValue), base_revision: state.revision});
                frappe.confirm(__('Import preview: {0} additions, {1} changes, {2} unchanged. Import and publish?',
                    [preview.counts.added, preview.counts.changed, preview.counts.unchanged]), async () => {
                    await call('apply_import', {package: JSON.stringify(packageValue), base_revision: state.revision}); await load();
                });
            } catch (error) { frappe.msgprint(esc(error.message)); }
        }; input.click();
    });
    page.set_primary_action(__('Publish workbook setup'), async () => {
        if (selected === 'people:pc_routing') {
            const rows = routingState.matrix.employees.map(({employee, work_group, pc_review_group, additional_review_groups, pc_mode}) => ({employee, work_group, pc_review_group, additional_review_groups, pc_mode: pc_mode || 'override'}));
            const reviewer_groups = Object.fromEntries(Object.entries(routingState.matrix.review_groups).map(([key, value]) => [key, value.reviewers]));
            const args = {rows: JSON.stringify(rows), reviewer_groups: JSON.stringify(reviewer_groups), base_revision: routingState.revision};
            const preview = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.preview_proposed_routing', args, freeze: true})).message;
            const detail = preview.changes.map(row => esc(row.employee) + ': +' + esc(row.added.join(', ')) + ' / −' + esc(row.removed.join(', '))).join('<br>');
            frappe.confirm(esc(__('Publish this routing revision? Reviewer scope changes: {0} additions, {1} removals.', [preview.added, preview.removed])) + '<br>' + detail, async () => {
                await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.publish', args: {...args, preview_hash: preview.hash}, freeze: true});
                await load();
            });
            return;
        }
        if (selected.startsWith('people:')) { frappe.msgprint(__('Use the record edit action to save changes in this section.')); return; }
        await call('save_and_publish', {datasets: JSON.stringify(state.datasets), base_revision: state.revision}); await load();
        frappe.show_alert({message: __('Excel setup published'), indicator: 'green'});
    });
    page.add_inner_button(__('Reload'), () => { if (dirty || routingDirty) frappe.confirm(__('Discard unsaved edits?'), load); else load(); });
    poSetupButton = page.add_inner_button(__('PO workbook labels'), async () => {
        if (dirty) { frappe.msgprint(__('Publish or reload your setup edits first.')); return; }
        try {
            const fresh = await callPoSetup('get_po_setup_state');
            const contacts = fresh.contacts || [];
            const contactName = id => { const c = contacts.find(item => item.id === id); return c ? c.full_name : ''; };
            const rowsHtml = (fresh.projects || []).map((row, index) => '<tr data-index="' + index + '">' +
                '<td>' + esc(row.po) + '</td><td>' + esc(row.project_name || row.project) + '</td>' +
                '<td>' + esc(row.family_label || row.family || __('not set')) + '</td>' +
                '<td>' + esc(contactName(row.default_contact) || __('none')) + '</td>' +
                '<td><input class="form-control" data-field="csv_alias" maxlength="140" value="' + esc(row.csv_alias) + '"></td></tr>').join('');
            const dialog = new frappe.ui.Dialog({title: __('PO workbook labels'), fields: [{fieldname: 'settings', fieldtype: 'HTML'}]});
            dialog.fields_dict.settings.$wrapper.html('<div class="es-scroll"><table class="table table-bordered"><thead><tr>' +
                '<th>' + esc(__('PO / Agreement')) + '</th><th>' + esc(__('ERP Project')) + '</th><th>' + esc(__('Family')) + '</th>' +
                '<th>' + esc(__('TAWAL PM now')) + '</th><th>' + esc(__('Optional Excel CSV label')) + '</th></tr></thead><tbody>' + rowsHtml + '</tbody></table></div>' +
                '<p class="text-muted small">' + esc(__('The TAWAL PM comes from the PO family. For a one-off different PM, choose the contact in the RV80 TCN batch prompt. This dialog saves CSV labels only.')) + '</p>');
            dialog.set_primary_action(__('Save labels'), async () => {
                try {
                    const rows = Array.from(dialog.fields_dict.settings.$wrapper[0].querySelectorAll('tbody tr')).map(tr => ({
                        project: fresh.projects[Number(tr.dataset.index)].project, csv_alias: tr.querySelector('[data-field="csv_alias"]').value}));
                    await callPoSetup('save_po_setup', {rows: JSON.stringify(rows), base_revision: fresh.revision, base_hash: fresh.hash});
                    dialog.hide(); await load();
                    frappe.show_alert({message: __('PO labels saved. Excel workbooks receive them on Sync From ERP.'), indicator: 'green'});
                } catch (error) { frappe.msgprint(esc(error.message)); }
            });
            dialog.show();
        } catch (error) { frappe.msgprint(esc(error.message)); }
    });
    load();
};
