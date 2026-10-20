frappe.pages['excel-setup'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Excel Setup'), single_column: true});
    const method = 'sig_warehouse.sig_operations.excel_setup.';
    const root = $('<div class="sig-excel-setup"></div>').appendTo(page.main);
    let state, selected = 'projects', dirty = false;
    const labels = {projects: __('Projects & Builder'), tag_definitions: __('Tags definitions'),
        tag_upl_links: __('Tags to UPL'), material_upl_links: __('Item to UPL'), builder_defaults: __('Builder defaults')};
    const fieldLabels = {project: 'ERP Project', po: 'PO / Agreement', alias: 'Builder alias', family: 'Project family',
        stream: 'Project stream', template: 'Word template key', internal_pm: 'Internal SIG PM', tawal_contact: 'TAWAL contact',
        contact_name: 'Contact name', contact_phone: 'Phone', contact_email: 'Email', upl_revision: 'UPL revision', enabled: 'Enabled',
        item: 'Tags item', rule: 'Matching rule', priority: 'Match priority', tag_item: 'Tags item', cuc: 'UPL CUC',
        description: 'UPL description', tag_matcher: 'Tags description qualifier', builder_rule: 'Tags normalization rule',
        item_code: 'ERP item code', source_uom: 'ERP unit', target_uom: 'Mapping unit', treatment: 'Treatment',
        quantity_basis: 'Reviewed quantity basis', kind: 'Setting type', key: 'Match value', value: 'Output value', value2: 'Additional value'};
    const optionLabels = {purpose_reason: 'TCN purpose and reason', csv_remarks: 'TCN CSV wording', tms_implementer: 'TMS implementer'};
    const esc = v => frappe.utils.escape_html(String(v == null ? '' : v)).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    const call = async (name, args={}) => (await frappe.call({method: method + name, args, freeze: true})).message;
    const render = () => {
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        const rows = state.datasets[selected];
        const fields = state.fields[selected].filter(f => f !== 'id');
        const note = selected === 'projects'
            ? __('Builder aliases are reusable local keys and may link to multiple ERP Projects. Choose the canonical ERP Project; PO / BA may remain blank until available.')
            : __('Blank PO and UPL revision mean a shared rule. Disable obsolete rows; keep their IDs.');
        root.html('<div class="es-summary"><b>' + __('Published revision') + ': ' + esc(state.revision) + '</b><span>' +
            esc(state.published_at || __('Not published')) + '</span><span>' + __('Excel import status unknown') + '</span></div>' +
            '<div class="es-tools"><label>' + __('Setup list') + ' <select class="form-control es-dataset">' +
            Object.keys(labels).map(k => '<option value="' + k + '" ' + (k === selected ? 'selected' : '') + '>' + esc(labels[k]) +
                ' (' + state.datasets[k].length + ')</option>').join('') + '</select></label>' +
            '<button class="btn btn-default es-add">' + __('Add row') + '</button>' +
            '<button class="btn btn-default es-import">' + __('Import existing setup') + '</button>' +
            '<button class="btn btn-default es-history">' + __('Revision history') + '</button></div>' +
            '<p class="text-muted">' + esc(note) + '</p>' +
            '<div class="es-scroll"><table class="table table-bordered"><thead><tr>' + fields.map(f => '<th>' + esc(__(fieldLabels[f] || f)) + '</th>').join('') +
            '</tr></thead><tbody>' + rows.map((row, i) => '<tr>' + fields.map(f => '<td>' +
                (f === 'enabled' ? '<input type="checkbox" data-row="' + i + '" data-field="enabled" ' + (row.enabled ? 'checked' : '') + '>' :
                state.options[selected + '.' + f] ? '<select class="form-control" data-row="' + i + '" data-field="' + f + '"><option value=""></option>' +
                    state.options[selected + '.' + f].map(value => '<option value="' + esc(value) + '" ' + (row[f] === value ? 'selected' : '') + '>' + esc(__(optionLabels[value] || value)) + '</option>').join('') + '</select>' :
                '<input class="form-control" data-row="' + i + '" data-field="' + f + '" value="' + esc(row[f]) + '" ' +
                    (f === 'id' || (selected === 'projects' && ['family','contact_name','contact_phone','contact_email'].includes(f)) ? 'readonly ' : '') +
                    (selected === 'projects' && f === 'project' ? 'list="es-ref-projects"' : selected === 'projects' && f === 'tawal_contact' ? 'list="es-ref-contacts"' : selected === 'projects' && f === 'stream' ? 'list="es-ref-streams"' : selected === 'material_upl_links' && f === 'item_code' ? 'list="es-ref-items"' : '') + '>') + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
        for (const [type, rows] of Object.entries(state.references)) {
            const list = $('<datalist></datalist>').attr('id', 'es-ref-' + type);
            rows.forEach(row => $('<option></option>').attr('value', row.name).text(row.project_name || row.full_name || row.item_name || row.name).appendTo(list));
            list.appendTo(root);
        }
    };
    const load = async () => { state = await call('get_page_state'); dirty = false; render(); };
    root.on('change', '.es-dataset', function () { selected = this.value; render(); });
    root.on('input change', '[data-field]', function (event) {
        const row = state.datasets[selected][Number(this.dataset.row)], field = this.dataset.field;
        row[field] = this.type === 'checkbox' ? this.checked : this.value;
        dirty = true;
        if (event.type === 'change' && selected === 'projects' && field === 'project') {
            const source = state.references.projects.find(p => p.name === this.value);
            if (source) {
                row.po = source.custom_agreement_no || source.custom_tawal_ba || source.custom_po_number || (/^\d+$/.test(source.name) ? source.name : '');
                row.family = source.custom_project_family || source.custom_family || '';
                render();
            }
        } else if (event.type === 'change' && selected === 'projects' && field === 'tawal_contact') {
            const source = state.references.contacts.find(p => p.name === this.value);
            row.contact_name = source ? source.full_name || '' : '';
            row.contact_phone = source ? source.mobile || '' : '';
            row.contact_email = source ? source.email || '' : '';
            render();
        } else if (event.type === 'change' && selected === 'material_upl_links' && field === 'item_code') {
            const source = state.references.items.find(p => p.name === this.value);
            if (source) { row.source_uom = source.stock_uom; if (!row.target_uom) row.target_uom = source.stock_uom; render(); }
        }
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
    load();
};
