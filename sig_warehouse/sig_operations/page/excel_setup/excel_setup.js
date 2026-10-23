frappe.pages['excel-setup'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Excel Setup'), single_column: true});
    const method = 'sig_warehouse.sig_operations.excel_setup.';
    const poSetupMethod = 'sig_warehouse.sig_operations.excel_setup_v3.';
    const root = $('<div class="sig-excel-setup"></div>').appendTo(page.main);
    let state, selected = 'projects', dirty = false;
    const labels = {projects: __('ERP Projects'), builder_profiles: __('Builder profiles'),
        builder_contacts: __('Builder contacts'), project_builder_links: __('Project → Builder assignments'), tag_definitions: __('Tags definitions'),
        tag_upl_links: __('Tags to UPL'), material_upl_links: __('Item to UPL'), builder_defaults: __('Builder defaults')};
    const fieldLabels = {project: 'ERP Project', profile: 'Builder profile', po: 'PO / Agreement', alias: 'Builder alias', family: 'Project family',
        stream: 'Project stream', stream_alias: 'Stream alias', template: 'Word template key', internal_pm: 'Internal SIG PM', tawal_contact: 'TAWAL contact',
        contact_name: 'Contact name', contact_phone: 'Phone', contact_email: 'Email', upl_revision: 'UPL revision', enabled: 'Enabled',
        item: 'Tags item', rule: 'Matching rule', priority: 'Match priority', tag_item: 'Tags item', cuc: 'UPL CUC',
        description: 'UPL description', tag_matcher: 'Tags description qualifier', builder_rule: 'Tags normalization rule',
        item_code: 'ERP item code', source_uom: 'ERP unit', target_uom: 'Mapping unit', treatment: 'Treatment',
        quantity_basis: 'Reviewed quantity basis', origin: 'Imported source', kind: 'Setting type', key: 'Match value', value: 'Output value', value2: 'Additional value'};
    const optionLabels = {purpose_reason: 'TCN purpose and reason', csv_remarks: 'TCN CSV wording', tms_implementer: 'TMS implementer'};
    const referenceFields = {
        projects: {project: 'projects'},
        builder_contacts: {profile: 'profiles', tawal_contact: 'contacts'},
        project_builder_links: {project: 'projects', profile: 'profiles', stream: 'streams'},
        material_upl_links: {item_code: 'items', target_uom: 'uoms'}
    };
    const referenceLabel = (type, row) => {
        if (type === 'projects') return [row.project_name, row.name].filter(Boolean).join(' · ');
        if (type === 'contacts') return [row.full_name, row.name].filter(Boolean).join(' · ');
        if (type === 'items') return [row.item_name, row.name, row.stock_uom].filter(Boolean).join(' · ');
        if (type === 'streams') return [row.alias, row.name].filter(Boolean).join(' · ');
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
        const rows = state.datasets[selected];
        const fields = state.fields[selected].filter(f => f !== 'id');
        const notes = {
            projects: __('Canonical ERP Projects and UPL scope only. PO / BA may remain blank. Builder profiles are maintained in their own list.'),
            builder_profiles: __('Reusable Excel aliases, templates and internal PM defaults. A profile can exist before any Project or PO is assigned.'),
            builder_contacts: __('Choose a Builder profile and an existing TAWAL directory contact. The operator selects the active contact in Excel. This list does not change native Project PM assignments.'),
            project_builder_links: __('Explicit links only. The same Builder profile can link to several Projects. No link is inferred from worksheet row order, Project name or family.')
        };
        const note = notes[selected] || __('Blank PO and UPL revision mean a shared rule. Disable obsolete rows; keep their IDs.');
        root.html('<div class="es-summary"><b>' + __('Published revision') + ': ' + esc(state.revision) + '</b><span>' +
            esc(state.published_at || __('Not published')) + '</span><span>' + __('Excel workbooks refresh from this ERP setup') + '</span></div>' +
            '<div class="es-tools"><label>' + __('Setup list') + ' <select class="form-control es-dataset">' +
            Object.keys(labels).map(k => '<option value="' + k + '" ' + (k === selected ? 'selected' : '') + '>' + esc(labels[k]) +
                ' (' + state.datasets[k].length + ')</option>').join('') + '</select></label>' +
            '<button class="btn btn-default es-add">' + __('Add row') + '</button>' +
            '<button class="btn btn-default es-import">' + __('Import existing setup') + '</button>' +
            '<button class="btn btn-default es-history">' + __('Revision history') + '</button></div>' +
            (state.migration_pending ? '<p class="text-warning">' + esc(__('Review and publish the separated lists. Previous combined associations remain in revision history; re-import Builder profiles from their independent source block.')) + '</p>' : '') +
            (state.pending_builder_contacts ? '<p class="text-warning">' + esc(__('{0} enabled Builder contacts need a directory link. Select an existing contact or disable obsolete rows. RV80 will retain its current Builder until these are resolved.', [state.pending_builder_contacts])) + '</p>' : '') +
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
                        (selected === 'material_upl_links' && f === 'source_uom') ? 'readonly ' : '') + '>') + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
    };
    const load = async () => { state = await call('get_page_state'); dirty = false; render(); };
    root.on('change', '.es-dataset', function () { selected = this.value; render(); });
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
        await call('save_and_publish', {datasets: JSON.stringify(state.datasets), base_revision: state.revision}); await load();
        frappe.show_alert({message: __('Excel setup published'), indicator: 'green'});
    });
    page.add_inner_button(__('Reload'), () => { if (dirty) frappe.confirm(__('Discard unsaved edits?'), load); else load(); });
    page.add_inner_button(__('PO defaults and CSV labels'), async () => {
        if (dirty) { frappe.msgprint(__('Publish or reload your setup edits before changing PO defaults.')); return; }
        try {
            const poState = await callPoSetup('get_po_setup_state');
            const contacts = poState.contacts || [];
            const rowsHtml = (poState.projects || []).map((row, index) => '<tr data-index="' + index + '">' +
                '<td>' + esc(row.po) + '</td><td>' + esc(row.project_name || row.project) +
                '<div class="text-muted">' + esc(row.family) + '</div></td>' +
                '<td><input class="form-control" data-field="csv_alias" maxlength="140" value="' + esc(row.csv_alias) + '"></td>' +
                '<td><select class="form-control" data-field="default_contact"><option value="">' + esc(__('No default')) + '</option>' +
                (row.default_contact && !contacts.some(contact => contact.id === row.default_contact) ?
                    '<option value="' + esc(row.default_contact) + '" selected>' + esc(__('Inactive or unavailable default')) + ' · ' + esc(row.default_contact) + '</option>' : '') +
                contacts.map(contact => '<option value="' + esc(contact.id) + '" ' +
                    (contact.id === row.default_contact ? 'selected' : '') + '>' +
                    esc([contact.serial, contact.full_name].filter(Boolean).join(' · ')) + '</option>').join('') +
                '</select></td></tr>').join('');
            const dialog = new frappe.ui.Dialog({title: __('PO defaults and CSV labels'), fields: [{fieldname: 'settings', fieldtype: 'HTML'}]});
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
                        default_contact: tr.querySelector('[data-field="default_contact"]').value
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
