frappe.pages['excel-setup'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Excel Setup'), single_column: true});
    const method = 'sig_warehouse.sig_operations.excel_setup.';
    const poSetupMethod = 'sig_warehouse.sig_operations.excel_setup_v3.';
    const root = $('<div class="sig-excel-setup"></div>').appendTo(page.main);
    let state, selected = 'projects', dirty = false, peopleState = null, routingState = null, routingDirty = false;
    const peopleLabels = {employees: __('Employees'), pc_routing: __('Employee project groups / petty cash'), project_assignments: __('Employee project assignments'), reporter_maps: __('Field reporter mappings'), candidates: __('Candidate onboarding'), onboarding: __('Employee onboarding checks')};
    const labels = {projects: __('Projects / PO scope'), builder_profiles: __('Builder profiles (legacy)'),
        builder_contacts: __('Profile-linked contacts (legacy)'), project_builder_links: __('Project → Builder assignments (legacy)'), tag_definitions: __('Tags definitions'),
        tag_upl_links: __('Tags to UPL'), material_upl_links: __('Item to UPL'), builder_defaults: __('TCN wording and defaults'), teams: __('Field teams (leaders)')};
    const legacyDatasets = new Set(['builder_profiles', 'builder_contacts', 'project_builder_links']);
    const fieldLabels = {project: 'ERP Project', profile: 'Builder profile', po: 'PO / Agreement', alias: 'Builder alias', family: 'Project family',
        stream: 'Project stream', stream_alias: 'Stream alias', template: 'Word template key', internal_pm: 'Internal SIG PM', tawal_contact: 'TAWAL contact',
        contact_name: 'Contact name', contact_phone: 'Phone', contact_email: 'Email', upl_revision: 'UPL revision', enabled: 'Enabled',
        item: 'Tags item', rule: 'Matching rule', priority: 'Match priority', tag_item: 'Tags item', cuc: 'UPL CUC',
        description: 'UPL description', tag_matcher: 'Tags description qualifier', builder_rule: 'Tags normalization rule',
        item_code: 'ERP item code', source_uom: 'ERP unit', target_uom: 'Mapping unit', treatment: 'Treatment',
        quantity_basis: 'Reviewed quantity basis', origin: 'Imported source', leader: 'Team leader (employee)', team: 'Team', phone: 'Phone', archetype: 'Archetype', kind: 'Setting type', key: 'Match value', value: 'Output value', value2: 'Additional value'};
    const optionLabels = {purpose_reason: 'TCN purpose and reason', csv_remarks: 'TCN CSV wording', tms_implementer: 'TMS implementer'};
    const referenceFields = {
        projects: {project: 'projects'},
        builder_contacts: {profile: 'profiles', tawal_contact: 'contacts'},
        project_builder_links: {project: 'projects', profile: 'profiles', stream: 'streams'},
        material_upl_links: {item_code: 'items', target_uom: 'uoms'},
        teams: {leader: 'employees'}
    };
    const referenceLabel = (type, row) => {
        if (type === 'projects') return [row.project_name, row.name].filter(Boolean).join(' · ');
        if (type === 'contacts') return [row.full_name, row.name].filter(Boolean).join(' · ');
        if (type === 'items') return [row.item_name, row.name, row.stock_uom].filter(Boolean).join(' · ');
        if (type === 'streams') return [row.alias, row.name].filter(Boolean).join(' · ');
        if (type === 'employees') return [row.employee_name, row.name].filter(Boolean).join(' · ');
        if (type === 'profiles') return row.alias;
        return row.name || '';
    };
    const choices = type => type === 'profiles'
        ? state.datasets.builder_profiles.filter(row => row.enabled).map(row => ({...row, name: row.id}))
        : state.references[type] || [];
    const displayValue = (type, value) => type === 'profiles'
        ? ((choices(type).find(row => row.name === value) || {}).alias || value) : value;
    const referenceCell = (type, value, rowIndex, field) => '<div class="es-lookup" data-ref-type="' + type + '" data-row="' + rowIndex + '" data-field="' + field + '">' +
        '<input class="form-control es-lookup-input" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" value="' + esc(displayValue(type, value)) + '" placeholder="' + esc(__('Search ERP records')) + '">' +
        '<div class="es-lookup-menu" role="listbox" hidden></div></div>';
    const referenceOptions = (type, query, rowIndex) => {
        let rows = choices(type);
        if (type === 'streams') {
            const project = state.datasets[selected][rowIndex].project;
            rows = project ? rows.filter(row => row.project === project) : [];
        }
        const needle = String(query || '').trim().toLocaleLowerCase();
        return rows.filter(row => !needle || referenceLabel(type, row).toLocaleLowerCase().includes(needle))
            .slice(0, 40).map(row => '<button type="button" class="es-lookup-option" role="option" data-value="' + esc(row.name) + '">' + esc(referenceLabel(type, row)) + '</button>').join('');
    };
    const openLookup = input => {
        const box = input.closest('.es-lookup');
        const menu = box.querySelector('.es-lookup-menu');
        const field = box.dataset.field;
        const canClear = (selected === 'builder_contacts' && field === 'tawal_contact') ||
            (selected === 'project_builder_links' && field === 'stream') || (selected === 'material_upl_links' && field === 'target_uom');
        menu.innerHTML = (canClear ? '<button type="button" class="es-lookup-option es-lookup-clear" role="option" data-value="">' + esc(__('Clear selection')) + '</button>' : '') + referenceOptions(box.dataset.refType, input.value, Number(box.dataset.row));
        menu.hidden = !menu.childElementCount;
        input.setAttribute('aria-expanded', String(!menu.hidden));
    };
    const commitLookup = (box, value) => {
        const row = state.datasets[selected][Number(box.dataset.row)], field = box.dataset.field, type = box.dataset.refType;
        if (!value && ((selected === 'builder_contacts' && field === 'tawal_contact') ||
                (selected === 'project_builder_links' && field === 'stream') || (selected === 'material_upl_links' && field === 'target_uom'))) {
            row[field] = '';
            if (selected === 'builder_contacts' && field === 'tawal_contact') { row.contact_name = ''; row.contact_phone = ''; row.contact_email = ''; }
            if (selected === 'project_builder_links' && field === 'stream') row.stream_alias = '';
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
            row.family = source.custom_project_family || source.custom_family || '';
        } else if (selected === 'project_builder_links' && field === 'project') {
            if (row.stream && !(state.references.streams || []).some(stream => stream.name === row.stream && stream.project === source.name)) { row.stream = ''; row.stream_alias = ''; }
        } else if (selected === 'project_builder_links' && field === 'stream') {
            row.stream_alias = source.alias || '';
        } else if (selected === 'builder_contacts' && field === 'tawal_contact') {
            row.contact_name = source.full_name || '';
            row.contact_phone = source.mobile || '';
            row.contact_email = source.email || '';
        } else if (selected === 'teams' && field === 'leader') {
            row.team = source.employee_name || '';
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
        if (selected.startsWith('people:')) {
            const key = selected.slice(7), result = peopleState;
            const options = Object.keys(labels).map(k => '<option value="' + k + '">' + esc(labels[k]) + '</option>').join('') +
                '<optgroup label="' + esc(__('People')) + '">' + Object.keys(peopleLabels).map(k => '<option value="people:' + k + '" ' + (key === k ? 'selected' : '') + '>' + esc(peopleLabels[k]) + '</option>').join('') + '</optgroup>';
            if (key === 'pc_routing') {
                const matrix = routingState.matrix, groups = Object.keys(matrix.review_groups);
                const select = (field, value, i) => '<select class="form-control es-pc-field" data-index="' + i + '" data-pc-field="' + field + '">' + groups.map(g => '<option value="' + esc(g) + '" ' + (g === value ? 'selected' : '') + '>' + esc(matrix.review_groups[g].label || g) + '</option>').join('') + '</select>';
                root.html('<div class="es-tools"><label>' + esc(__('Setup list')) + ' <select class="form-control es-dataset">' + options + '</select></label></div>' +
                    '<p class="text-warning">' + esc(__('People routing is read-only until petty-cash clearance permissions are aligned with the published routing.')) + '</p><fieldset disabled><div class="es-scroll"><table class="table table-bordered"><thead><tr><th>' + esc(__('Employee')) + '</th><th>' + esc(__('Name')) + '</th><th>' + esc(__('Project group')) + '</th><th>' + esc(__('PC review group')) + '</th><th>' + esc(__('Additional groups (comma separated keys)')) + '</th></tr></thead><tbody>' +
                    matrix.employees.map((row, i) => '<tr><td>' + esc(row.employee) + '</td><td>' + esc(row.employee_name) + '</td><td>' + select('work_group', row.work_group, i) + '</td><td>' + select('pc_review_group', row.pc_review_group, i) + '</td><td><input class="form-control es-pc-field" data-index="' + i + '" data-pc-field="additional_review_groups" value="' + esc((row.additional_review_groups || []).join(', ')) + '"></td></tr>').join('') + '</tbody></table></div>' +
                    '<h4>' + esc(__('Reviewers by group')) + '</h4><p class="text-muted">' + esc(__('Separate employee names with semicolons. Reviewers must appear in the employee routing list.')) + '</p><table class="table table-bordered"><tbody>' + groups.map(g => '<tr><td>' + esc(matrix.review_groups[g].label || g) + '</td><td><input class="form-control es-pc-reviewers" data-group="' + esc(g) + '" value="' + esc((matrix.review_groups[g].reviewers || []).join('; ')) + '"></td></tr>').join('') + '</tbody></table></fieldset>');
                return;
            }
            const fields = result.fields.filter(f => f !== 'modified');
            const editable = result.can_write && ['project_assignments', 'reporter_maps'].includes(key);
            root.html('<div class="es-tools"><label>' + esc(__('Setup list')) + ' <select class="form-control es-dataset">' + options + '</select></label>' +
                (key === 'project_assignments' && result.can_create ? '<button type="button" class="btn btn-default es-people-add">' + esc(__('Add row')) + '</button>' : '') + '</div>' +
                '<p class="text-muted">' + esc(__('These are existing ERP records. Changes use their own permissions and history.')) + '</p>' +
                '<div class="es-scroll"><table class="table table-bordered"><thead><tr>' + fields.map(f => '<th>' + esc(__(fieldLabels[f] || f)) + '</th>').join('') + (editable ? '<th></th>' : '') + '</tr></thead><tbody>' +
                result.rows.map((row, i) => '<tr>' + fields.map(f => '<td>' + esc(row[f] || '') + '</td>').join('') + (editable ? '<td><button type="button" class="btn btn-default es-people-edit" data-index="' + i + '">' + esc(__('Edit')) + '</button></td>' : '') + '</tr>').join('') + '</tbody></table></div>');
            return;
        }
        const rows = state.datasets[selected];
        // UPL descriptions belong to the UPL/Mapping data; preserve legacy values in the payload.
        const fields = state.fields[selected].filter(f => f !== 'id' && !(selected === 'tag_upl_links' && f === 'description'));
        const notes = {
            projects: __('Canonical ERP Projects and PO scope used by Excel. Family and the usual TAWAL PM are maintained on the Project / PO setup.'),
            builder_profiles: __('Historical compatibility data. These aliases no longer determine PO family, TAWAL contact or MOP template selection.'),
            builder_contacts: __('Historical profile-linked contact rows. The current TAWAL directory has one record per person; PO defaults reference those records directly.'),
            project_builder_links: __('Historical Builder profile assignments. Kept for old workbook revisions and audit; not required by V3 Sync From ERP.'),
            tag_upl_links: __('Link each Tags item to its UPL code. UPL descriptions come from Mapping. Use the optional qualifier only for a matching Tags sheet description, not the UPL code. Blank PO and revision mean a shared rule. A PO-specific rule can replace shared links for that Tags item; review all its codes.'),
            material_upl_links: __('Link warehouse items to UPL codes for AsBuilt. Direct 1:1 requires matching units; use Manual for review and Excluded for reviewed items with no link. Blank PO and revision mean a shared rule.'),
            builder_defaults: __('Shared TCN purpose, CSV wording and implementer defaults consumed by RV80.'),
            teams: __('Each team is its leader and carries the name of its leader. The Field Planner counts enabled teams and starts each one from the latest check-in or check-out site. Not sent to Excel workbooks.')
        };
        const note = notes[selected] || __('Blank PO and UPL revision mean a shared rule. Disable obsolete rows; keep their IDs.');
        root.html('<div class="es-summary"><b>' + __('Published revision') + ': ' + esc(state.revision) + '</b><span>' +
            esc(state.published_at || __('Not published')) + '</span><span>' + __('Excel workbooks refresh from this ERP setup') + '</span></div>' +
            '<div class="es-tools"><label>' + __('Setup list') + ' <select class="form-control es-dataset">' +
            Object.keys(labels).filter(k => !legacyDatasets.has(k)).map(k => '<option value="' + k + '" ' + (k === selected ? 'selected' : '') + '>' + esc(labels[k]) +
                ' (' + state.datasets[k].length + ')</option>').join('') +
            '<optgroup label="' + esc(__('People')) + '">' + Object.keys(peopleLabels).map(k => '<option value="people:' + k + '">' + esc(peopleLabels[k]) + '</option>').join('') + '</optgroup>' +
            '<optgroup label="' + esc(__('Legacy maintenance · retained for compatibility')) + '">' +
            Object.keys(labels).filter(k => legacyDatasets.has(k)).map(k => '<option value="' + k + '" ' + (k === selected ? 'selected' : '') + '>' + esc(labels[k]) +
                ' (' + state.datasets[k].length + ')</option>').join('') + '</optgroup></select></label>' +
            '<button class="btn btn-default es-add">' + __('Add row') + '</button>' +
            '<button class="btn btn-default es-import">' + __('Import existing setup') + '</button>' +
            '<button class="btn btn-default es-history">' + __('Revision history') + '</button></div>' +
            (legacyDatasets.has(selected) ? '<p class="text-muted">' + esc(__('Legacy records are preserved. V3 workbook sync and PO configuration no longer depend on these profile associations.')) + '</p>' : '') +
            (selected === 'builder_contacts' && state.pending_builder_contacts ? '<p class="text-warning">' + esc(__('{0} legacy contact rows do not resolve to the person directory. This does not block V3 Sync From ERP.', [state.pending_builder_contacts])) + '</p>' : '') +
            '<p class="text-muted">' + esc(note) + '</p>' +
            '<div class="es-scroll"><table class="table table-bordered"><thead><tr>' + fields.map(f => '<th>' + esc(__(fieldLabels[f] || f)) + '</th>').join('') +
            '</tr></thead><tbody>' + rows.map((row, i) => '<tr>' + fields.map(f => '<td>' +
                (f === 'enabled' ? '<input type="checkbox" data-row="' + i + '" data-field="enabled" ' + (row.enabled ? 'checked' : '') + '>' :
                state.options[selected + '.' + f] ? '<select class="form-control" data-row="' + i + '" data-field="' + f + '"><option value=""></option>' +
                    state.options[selected + '.' + f].map(value => '<option value="' + esc(value) + '" ' + (row[f] === value ? 'selected' : '') + '>' + esc(__(optionLabels[value] || value)) + '</option>').join('') + '</select>' :
                referenceFields[selected] && referenceFields[selected][f] ? referenceCell(referenceFields[selected][f], row[f], i, f) :
                '<input class="form-control" data-row="' + i + '" data-field="' + f + '" value="' + esc(row[f]) + '" ' +
                    (f === 'id' || (selected === 'projects' && ['po','family'].includes(f)) ||
                        (selected === 'builder_contacts' && ['contact_name','contact_phone','contact_email','origin'].includes(f)) ||
                        (selected === 'project_builder_links' && f === 'stream_alias') ||
                        (selected === 'teams' && ['team','phone'].includes(f)) ||
                        (selected === 'material_upl_links' && f === 'source_uom') ? 'readonly ' : '') + '>') + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
    };
    const load = async () => {
        state = await call('get_page_state');
        if (selected === 'people:pc_routing') routingState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.get_state', freeze: true})).message;
        else if (selected.startsWith('people:')) peopleState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.get_section', args: {section: selected.slice(7)}, freeze: true})).message;
        dirty = false; routingDirty = false; render();
    };
    root.on('change', '.es-dataset', async function () {
        const next = this.value;
        if (next === 'people:pc_routing') {
            if (!routingState) { try { routingState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_routing.get_state', freeze: true})).message; } catch (error) { render(); return; } }
        } else if (next.startsWith('people:')) {
            try { peopleState = (await frappe.call({method: 'sig_warehouse.sig_operations.people_setup.get_section', args: {section: next.slice(7)}, freeze: true})).message; }
            catch (error) { render(); return; }
        }
        selected = next; render();
    });
    root.on('change', '.es-pc-field', function () {
        const row = routingState.matrix.employees[Number(this.dataset.index)], field = this.dataset.pcField;
        if (field === 'additional_review_groups') row[field] = this.value.split(',').map(s => s.trim()).filter(Boolean);
        else { const old = row[field]; row[field] = this.value; if (field === 'work_group' && row.pc_review_group === old) row.pc_review_group = this.value; }
        routingDirty = true; render();
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
    root.on('focus', '.es-lookup-input', function () { openLookup(this); });
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
            '<tr><td>' + esc(row.revision) + '</td><td>' + esc(row.published_at) + '</td><td>' + esc(row.published_by) + '</td></tr>').join('') + '</tbody></table>');
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
    page.set_primary_action(__('Save and publish'), async () => {
        if (selected === 'people:pc_routing') {
            frappe.msgprint(__('People routing is read-only until petty-cash clearance permissions are aligned.')); return;
        }
        if (selected.startsWith('people:')) { frappe.msgprint(__('Use the record edit action to save changes in this section.')); return; }
        await call('save_and_publish', {datasets: JSON.stringify(state.datasets), base_revision: state.revision}); await load();
        frappe.show_alert({message: __('Excel setup published'), indicator: 'green'});
    });
    page.add_inner_button(__('Reload'), () => { if (dirty || routingDirty) frappe.confirm(__('Discard unsaved edits?'), load); else load(); });
    page.add_inner_button(__('Projects / PO setup'), async () => {
        if (dirty) { frappe.msgprint(__('Publish or reload your setup edits before changing PO defaults.')); return; }
        try {
            const poState = await callPoSetup('get_po_setup_state');
            const contacts = poState.contacts || [];
            const contactName = id => {
                const contact = contacts.find(item => item.id === id);
                return contact ? [contact.full_name, contact.serial].filter(Boolean).join(' · ') : (id || __('None'));
            };
            const rowsHtml = (poState.projects || []).map((row, index) => '<tr data-index="' + index + '">' +
                '<td>' + esc(row.po) + '</td><td>' + esc(row.project_name || row.project) +
                '<div class="text-muted">' + esc(row.family) + '</div>' +
                (row.needs_reconciliation ? '<div class="es-po-conflict" style="margin-top:8px;padding:8px 10px;border-inline-start:3px solid #e0a100;background:var(--alert-bg,#fff8e1);font-size:12px;line-height:1.45"><strong>' + esc(__('PM mismatch')) +
                    '</strong><br>' + esc(__('Project: ')) + esc(contactName(row.project_default_contact)) +
                    '<br>' + esc(__('Active assignment: ')) + esc(contactName(row.assignment_default_contact)) +
                    '<br><label><input type="checkbox" data-field="resolve_conflict"> ' + esc(__('Confirm the selected PM to align both records')) + '</label></div>' : '') + '</td>' +
                '<td><input class="form-control" data-field="csv_alias" maxlength="140" value="' + esc(row.csv_alias) + '"></td>' +
                '<td><select class="form-control" data-field="default_contact"><option value="">' + esc(__('No default')) + '</option>' +
                (row.default_contact && !contacts.some(contact => contact.id === row.default_contact) ?
                    '<option value="' + esc(row.default_contact) + '" selected>' + esc(__('Inactive or unavailable default')) + ' · ' + esc(row.default_contact) + '</option>' : '') +
                contacts.map(contact => '<option value="' + esc(contact.id) + '" ' +
                    (contact.id === row.default_contact ? 'selected' : '') + '>' +
                    esc([contact.serial, contact.full_name].filter(Boolean).join(' · ')) + '</option>').join('') +
                '</select></td></tr>').join('');
            const dialog = new frappe.ui.Dialog({title: __('Projects / PO setup'), fields: [{fieldname: 'settings', fieldtype: 'HTML'}]});
            dialog.fields_dict.settings.$wrapper.html('<div class="es-scroll"><table class="table table-bordered"><thead><tr>' +
                '<th>' + esc(__('PO / Agreement')) + '</th><th>' + esc(__('ERP Project / Family')) + '</th>' +
                '<th>' + esc(__('Optional Excel CSV label')) + '</th><th>' + esc(__('Default TAWAL PM')) +
                '</th></tr></thead><tbody>' + rowsHtml + '</tbody></table></div>' +
                '<button type="button" class="btn btn-default btn-sm es-manage-contacts">' +
                esc(__('Manage TAWAL contact directory')) + '</button>' +
                '<p class="text-muted small" style="margin-top:8px">' +
                esc(__('The ERP contact serial is the stable choice key. Contacts can be reused on any PO; this selection only sets a PO default.')) + '</p>');
            dialog.fields_dict.settings.$wrapper.find('.es-manage-contacts').on('click', () => {
                dialog.hide();
                frappe.set_route('List', 'SIG TAWAL Contact');
            });
            dialog.set_primary_action(__('Save PO settings'), async () => {
                try {
                    const rows = Array.from(dialog.fields_dict.settings.$wrapper[0].querySelectorAll('tbody tr')).map(tr => ({
                        project: poState.projects[Number(tr.dataset.index)].project,
                        csv_alias: tr.querySelector('[data-field="csv_alias"]').value,
                        default_contact: tr.querySelector('[data-field="default_contact"]').value,
                        resolve_conflict: !!tr.querySelector('[data-field="resolve_conflict"]:checked')
                    }));
                    await callPoSetup('save_po_setup', {rows: JSON.stringify(rows), base_revision: poState.revision, base_hash: poState.hash});
                    dialog.hide(); await load();
                    frappe.show_alert({message: __('PO settings saved. Excel workbooks will receive them on Sync From ERP.'), indicator: 'green'});
                } catch (error) { frappe.msgprint(esc(error.message)); }
            });
            dialog.show();
        } catch (error) { frappe.msgprint(esc(error.message)); }
    });
    load();
};
