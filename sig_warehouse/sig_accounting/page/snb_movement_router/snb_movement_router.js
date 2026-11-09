frappe.pages['snb-movement-router'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Bank Router'), single_column: true});
    const root = $('<main class="snb-router"></main>').appendTo(page.main), el = root[0];
    const esc = v => frappe.utils.escape_html(String(v == null ? '' : v));
    const api = 'sig_warehouse.sig_accounting.snb_movement_router.';
    const tabs = {needs: __('Needs you'), drafts: __('Drafts'), posted: __('Posted'), deferred: __('Deferred')};
    const kinds = {SUPPLIER_PAYMENT: __('Supplier payment'), CUSTOMER_RECEIPT: __('Customer receipt'), EXPENSE_PAYMENT: __('Expense, no party'), UNKNOWN: __('Unclassified outgoing'),
        PETTY_CASH: __('Petty Cash'), EMPLOYEE: __('Employee'), OWN_TRANSFER: __('Own transfer'), SPECIALIST: __('Specialist workflow'),
        BANK_CHARGE: __('Bank charge'), OTHER: __('Other')};
    const needs = {ROUTE_PARTY: __('Choose who this is'), CREATE_DRAFT: __('No draft yet'), PICK_DOCUMENT: __('Pick the matching document'),
        CONFLICT: __('Two parties claim this payer'), NEEDS_HR_LINK: __('Waiting for the HR custody link'),
        CHOOSE_TREATMENT: __('Choose PE or JE for this movement'), CONFIRM_TREATMENT: __('Confirm the payee default for this movement'),
        TREATMENT_MISMATCH: __('Linked document type differs from the selected treatment')};
    const categories = {XXPC: __('Petty Cash'), XXSL: __('Salary'), XXHR: __('HR'), XXCL: __('Deferred'), XXMT: __('Maintenance'), XXMR: __('Materials'), XXSC: __('Subcontractor'), XXLG: __('Logistics')};
    const state = {tab: 'needs', bank: 'ALL', search: '', items: [], counts: {}, selected: '', status: null, bulkSelected: new Set()};
    const q = s => el.querySelector(s);
    const money = (n, c) => `${Number(n || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${esc(c || 'SAR')}`;
    const docStatus = s => s === 1 ? __('Posted') : s === 0 ? __('Draft') : s === 2 ? __('Cancelled') : __('Unknown');
    const selected = () => state.items.find(x => x.name === state.selected);
    const visibleItems = () => state.items.filter(x => {
        const pair = x.signals && x.signals.paired_transfer;
        return !pair || pair.primary || !state.items.some(other => other.name === pair.name);
    });
    const docLink = (t, n, s) => n ? `<a href="#" data-erp-doctype="${esc(t)}" data-erp-name="${esc(n)}">${esc(n)}</a> · ${esc(docStatus(s))}` : '';

    root.html(`<header><h2>${__('Bank movements')}</h2><div class="snb-banner" data-banner></div></header>
        <div class="snb-controls"><select data-bank><option value="ALL">${__('All banks')}</option><option value="SNB">SNB</option><option value="ALINMA">Alinma</option></select>
        <input class="form-control" data-search type="search" placeholder="${__('Search name, reference or document')}"><button class="btn btn-default" data-refresh>${__('Refresh')}</button></div>
        <nav data-tabs></nav><section class="snb-grid"><aside><div class="snb-bulk"><button class="btn btn-default" data-bulk>${__('Confirm selected unique matches')}</button></div><div data-queue></div></aside><article data-card></article></section>`);

    function renderTabs() {
        q('[data-tabs]').innerHTML = Object.entries(tabs).map(([k, label]) =>
            `<button class="btn ${state.tab === k ? 'btn-primary' : 'btn-default'}" data-tab="${k}">${label} · ${state.counts[k] ?? 0}</button>`).join('');
        const s = state.status;
        q('[data-banner]').textContent = s ? (s.auto_draft ? __('Drafts are created automatically from {0}.', [s.auto_draft_from]) : __('Automatic drafting is off: the router links and shows only.')) : '';
    }
    function renderList() {
        q('[data-queue]').innerHTML = visibleItems().map(x => `<div class="snb-row-wrap">${x.decision_type === 'PICK_DOCUMENT' && (x.candidates.documents || []).length === 1 ? `<label class="snb-bulk-check"><input type="checkbox" data-bulk-select value="${esc(x.name)}" ${state.bulkSelected.has(x.name) ? 'checked' : ''}></label>` : ''}<button class="snb-row ${state.selected === x.name ? 'selected' : ''}" data-row="${esc(x.name)}">
            <strong>${money(x.amount, x.currency)}</strong><span>${esc(x.event_date)} · ••${esc(x.account_tail)} · ${esc(kinds[x.kind] || '')}</span>
            <span>${esc(x.counterparty_name || x.display_name || __('Not identified'))}</span>${needs[x.decision_type] ? `<small>${esc(needs[x.decision_type])}</small>` : ''}</button></div>`).join('') || `<p>${__('Nothing here.')}</p>`;
    }
    function actions(x) {
        if (x.decision_type === 'PICK_DOCUMENT') {
            return `<h4>${__('Which document is this?')}</h4>` + (x.candidates.documents || []).map((d, i) => `<label><input type="radio" name="pick" value="${i}"> ${esc(d.doctype)} · ${esc(d.name)} · ${esc(d.date)} · ${esc(docStatus(d.docstatus))}</label>`).join('') +
                `<button class="btn btn-primary" data-pick>${__('Link')}</button>`;
        }
        if (x.decision_type === 'NEEDS_HR_LINK') return `<p>${__('This petty-cash transfer cannot be matched to an Employee until HR links the custody account.')}</p>`;
        const canRoute = (!x.erp_document || x.doc_status === 0) && ['SUPPLIER_PAYMENT', 'CUSTOMER_RECEIPT', 'EXPENSE_PAYMENT', 'UNKNOWN', 'EMPLOYEE'].includes(x.kind) &&
            (x.decision_type || x.link_method === 'AUTO_DRAFT' || (x.direction === 'DEBIT' && ['UNKNOWN', 'EMPLOYEE'].includes(x.kind)));
        if (!canRoute) return '';
        const treatment = x.accounting_treatment || x.signals?.suggested_treatment || '';
        const expense = treatment === 'JOURNAL_ENTRY';
        const partyType = x.direction === 'CREDIT' ? 'Customer' : 'Supplier';
        return `<h4>${__('How should Finance account for this movement?')}</h4>
            <select class="form-control" data-treatment><option value="">${__('Choose treatment…')}</option>
                <option value="PAYMENT_ENTRY" ${treatment === 'PAYMENT_ENTRY' ? 'selected' : ''}>${__('Payment Entry')}</option>
                <option value="JOURNAL_ENTRY" ${treatment === 'JOURNAL_ENTRY' ? 'selected' : ''} ${x.direction === 'CREDIT' ? 'disabled' : ''}>${__('Journal Entry')}</option>
                <option value="FINANCE_HANDLES" ${treatment === 'FINANCE_HANDLES' ? 'selected' : ''}>${__('Finance handles outside this router')}</option></select>
            ${treatment === 'FINANCE_HANDLES' ? `<button class="btn btn-primary" data-route>${__('Save decision')}</button>` : ''}
            ${treatment && treatment !== 'FINANCE_HANDLES' ? `<h4>${expense ? __('Expense account') : __('ERP party')}</h4><input class="form-control" data-find placeholder="${__('Type at least two characters')}" data-type="${expense ? 'Account' : partyType}">
            <select class="form-control" data-choice><option value="">${__('Choose…')}</option>${expense && (x.accounting_account || x.signals?.suggested_account) ? `<option value="${esc(x.accounting_account || x.signals.suggested_account)}" selected>${esc(x.accounting_account || x.signals.suggested_account)}</option>` : ''}</select><button class="btn btn-primary" data-route>${__('Route here')}</button>
            <label><input type="checkbox" data-remember> ${__('Remember the default treatment for this payee')}</label>
            ${expense ? '' : `<details><summary>${__('New {0}', [__(partyType)])}</summary><input class="form-control" data-new-name placeholder="${__('Full name')}"><input class="form-control" data-new-vat placeholder="${__('VAT number (optional)')}">${partyType === 'Customer' ? `<label>${__('Country')}</label><input class="form-control" data-new-country value="Saudi Arabia" placeholder="${__('Country name')}">` : ''}<button class="btn btn-default" data-new>${__('Create and route')}</button></details>`}` : ''}`;
    }
    function renderCard() {
        const x = selected(), c = q('[data-card]');
        if (!x) { c.innerHTML = `<p>${__('Select a movement.')}</p>`; return; }
        const feeRows = (x.fees || []), feeTotal = feeRows.reduce((sum, f) => sum + Math.abs(Number(f.amount || 0)), 0);
        const fees = feeRows.length ? `<details class="snb-fees"><summary>${__('Related fees and VAT')} · ${money(feeTotal, x.currency)}</summary>${feeRows.map(f => `<p>${f.family === 'FEE_VAT' ? 'VAT' : __('Fee')} ${money(f.amount, x.currency)} · ${f.erp_document ? '✓ ' + docLink(f.erp_doctype, f.erp_document, f.doc_status) : '○ ' + __('not posted')}</p>`).join('')}</details>` : '';
        c.innerHTML = `<div class="snb-amount">${money(x.amount, x.currency)}</div>
            <p>${esc(x.bank)} · ${esc(x.event_date)} · ••${esc(x.account_tail)} · ${__('Ref')} ${esc(x.reference || '—')}</p>
            <p><strong>${esc(x.counterparty_name || x.display_name || __('Not identified'))}</strong> · ${esc(kinds[x.kind] || '')}${x.category ? ' · ' + esc(categories[x.category] || x.category) : ''}</p>
            ${x.signals && x.signals.biller_code ? `<p>${__('SADAD biller')} · ${esc(x.signals.biller_code)}</p>` : ''}
            ${x.signals && x.signals.paired_transfer ? `<p>${__('Paired own-account transfer')} · ${esc(x.signals.paired_transfer.source_key || '')}</p>` : ''}
            ${x.erp_document ? `<p>${docLink(x.erp_doctype, x.erp_document, x.doc_status)} <small>(${esc(x.link_method)})</small>${x.link_method !== 'MARKER' ? ` <button class="btn btn-xs btn-default" data-unlink>${__('Wrong match')}</button>` : ''}</p>` : ''}
            ${x.signals && x.signals.error ? `<p class="snb-error">${esc(x.signals.error)}</p>` : ''}${fees}
            <div class="snb-actions">${actions(x)}${x.decision_type === 'CREATE_DRAFT' && !x.erp_document ? `<button class="btn btn-primary" data-create-draft>${__('Create reviewed draft')}</button>` : ''}</div><div data-message></div>
            <details><summary>${__('Statement')}</summary><pre>${esc(x.narrative || '—')}</pre><small>${esc(x.name)}</small></details>`;
    }
    const render = () => { renderTabs(); renderList(); renderCard(); };
    async function load() {
        try {
            const r = (await frappe.call({method: api + 'list_inbox', args: {tab: state.tab, bank: state.bank, search: state.search, limit: 100}})).message;
            state.items = r.items; state.counts = r.counts;
            if (!visibleItems().some(x => x.name === state.selected)) state.selected = visibleItems()[0]?.name || '';
            state.status = (await frappe.call({method: api + 'engine_status'})).message;
        } catch (e) { frappe.msgprint(__('Could not load bank movements. Check your access.')); }
        render();
    }
    async function act(method, args) {
        const x = selected(), msg = q('[data-message]');
        try { await frappe.call({method: api + method, type: 'POST', args: {name: x.name, modified: x.modified, ...args}}); await load(); frappe.show_alert({message: __('Saved'), indicator: 'green'}); }
        catch (e) { msg.textContent = __('Could not save. Refresh and try again.'); }
    }
    let timer;
    root.on('click', '[data-erp-doctype]', function (e) { e.preventDefault(); frappe.set_route('Form', this.dataset.erpDoctype, this.dataset.erpName); });
    root.on('click', '[data-tab]', function () { state.tab = this.dataset.tab; state.selected = ''; load(); });
    root.on('change', '[data-bulk-select]', function () { this.checked ? state.bulkSelected.add(this.value) : state.bulkSelected.delete(this.value); });
    root.on('click', '[data-bulk]', async function () {
        const names = [...state.bulkSelected];
        if (!names.length) { frappe.msgprint(__('Select one or more rows with exactly one offered match.')); return; }
        try {
            const result = (await frappe.call({method: api + 'bulk_confirm_unique_matches', type: 'POST', args: {items: names.map(name => ({name}))}})).message;
            state.bulkSelected.clear();
            await load();
            frappe.msgprint(__('Linked {0}; held {1} for review.', [result.linked, result.held]));
        } catch (e) { frappe.msgprint(__('Bulk linking failed. Refresh and review each row.')); }
    });
    root.on('click', '[data-row]', function () { state.selected = this.dataset.row; render(); });
    root.on('click', '[data-refresh]', load);
    root.on('click', '[data-create-draft]', () => act('create_reviewed_draft', {}));
    root.on('change', '[data-bank]', function () { state.bank = this.value; load(); });
    root.on('change', '[data-treatment]', function () { const x = selected(); if (x) x.accounting_treatment = this.value; renderCard(); });
    root.on('input', '[data-search]', function () { const v = this.value; clearTimeout(timer); timer = setTimeout(() => { state.search = v; load(); }, 300); });
    root.on('input', '[data-find]', function () {
        const input = this, type = input.dataset.type; clearTimeout(timer);
        timer = setTimeout(async () => {
            if (input.value.trim().length < (type === 'Account' ? 1 : 2)) return;
            const rows = (await frappe.call({method: api + (type === 'Account' ? 'search_expense_accounts' : 'search_parties'), args: type === 'Account' ? {query: input.value} : {doctype: type, query: input.value}})).message || [];
            q('[data-choice]').innerHTML = `<option value="">${__('Choose…')}</option>` + rows.map(r => `<option value="${esc(r.name)}">${esc(r.label)}</option>`).join('');
        }, 250);
    });
    root.on('click', '[data-route]', function () {
        const x = selected(), treatment = q('[data-treatment]').value, remember = q('[data-remember]')?.checked ? '1' : '0';
        if (!treatment) { q('[data-message]').textContent = __('Choose the treatment first.'); return; }
        if (treatment === 'FINANCE_HANDLES') { act('route_movement', {target: {type: 'FINANCE_HANDLES', treatment}}); return; }
        const value = q('[data-choice]')?.value;
        if (!value) { q('[data-message]').textContent = __('Choose first.'); return; }
        act('route_movement', {target: treatment === 'JOURNAL_ENTRY' ? {type: 'EXPENSE', treatment, account: value, remember_default: remember} : {type: 'PARTY', treatment, party_type: x.direction === 'CREDIT' ? 'Customer' : 'Supplier', party: value, remember_default: remember}});
    });
    root.on('click', '[data-new]', function () {
        const x = selected(), name = q('[data-new-name]').value.trim();
        if (name.length < 3) { q('[data-message]').textContent = __('Enter the full name.'); return; }
        act('route_movement', {target: {type: 'NEW_PARTY', treatment: q('[data-treatment]').value, party_type: x.direction === 'CREDIT' ? 'Customer' : 'Supplier', name, vat: q('[data-new-vat]').value, country: q('[data-new-country]')?.value || '', remember_default: q('[data-remember]')?.checked ? '1' : '0'}});
    });
    root.on('click', '[data-pick]', function () {
        const x = selected(), i = (q('input[name="pick"]:checked') || {}).value;
        if (i === undefined) { q('[data-message]').textContent = __('Choose a document.'); return; }
        const d = x.candidates.documents[Number(i)]; act('pick_document', {doctype: d.doctype, document: d.name});
    });
    root.on('click', '[data-unlink]', () => act('unlink_movement', {}));
    load();
};
