frappe.pages['snb-movement-router'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Bank Router'), single_column: true});
    const root = $('<main class="snb-router"></main>').appendTo(page.main), el = root[0];
    const esc = v => frappe.utils.escape_html(String(v == null ? '' : v));
    const api = 'sig_warehouse.sig_accounting.snb_movement_router.';
    const tabs = {needs: __('Needs you'), drafts: __('Drafts'), posted: __('Posted'), deferred: __('Deferred')};
    const kinds = {SUPPLIER_PAYMENT: __('Supplier payment'), CUSTOMER_RECEIPT: __('Customer receipt'), EXPENSE_PAYMENT: __('Expense, no party'),
        PETTY_CASH: __('Petty Cash'), EMPLOYEE: __('Employee'), OWN_TRANSFER: __('Own transfer'), SPECIALIST: __('Specialist workflow'),
        BANK_CHARGE: __('Bank charge'), OTHER: __('Other')};
    const needs = {ROUTE_PARTY: __('Choose who this is'), CREATE_DRAFT: __('No draft yet'), PICK_DOCUMENT: __('Pick the matching document'),
        CONFLICT: __('Two parties claim this payer'), NEEDS_HR_LINK: __('Waiting for the HR custody link')};
    const categories = {XXPC: __('Petty Cash'), XXSL: __('Salary'), XXHR: __('HR'), XXCL: __('Deferred'), XXMT: __('Maintenance'), XXMR: __('Materials'), XXSC: __('Subcontractor'), XXLG: __('Logistics')};
    const state = {tab: 'needs', bank: 'ALL', search: '', items: [], counts: {}, selected: '', status: null};
    const q = s => el.querySelector(s);
    const money = (n, c) => `${Number(n || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${esc(c || 'SAR')}`;
    const docStatus = s => s === 1 ? __('Posted') : s === 0 ? __('Draft') : s === 2 ? __('Cancelled') : __('Unknown');
    const selected = () => state.items.find(x => x.name === state.selected);
    const docLink = (t, n, s) => n ? `<a href="#" data-erp-doctype="${esc(t)}" data-erp-name="${esc(n)}">${esc(n)}</a> · ${esc(docStatus(s))}` : '';

    root.html(`<header><h2>${__('Bank movements')}</h2><div class="snb-banner" data-banner></div></header>
        <div class="snb-controls"><select data-bank><option value="ALL">${__('All banks')}</option><option value="SNB">SNB</option><option value="ALINMA">Alinma</option></select>
        <input class="form-control" data-search type="search" placeholder="${__('Search name, reference or document')}"><button class="btn btn-default" data-refresh>${__('Refresh')}</button></div>
        <nav data-tabs></nav><section class="snb-grid"><aside data-queue></aside><article data-card></article></section>`);

    function renderTabs() {
        q('[data-tabs]').innerHTML = Object.entries(tabs).map(([k, label]) =>
            `<button class="btn ${state.tab === k ? 'btn-primary' : 'btn-default'}" data-tab="${k}">${label} · ${state.counts[k] ?? 0}</button>`).join('');
        const s = state.status;
        q('[data-banner]').textContent = s ? (s.auto_draft ? __('Drafts are created automatically from {0}.', [s.auto_draft_from]) : __('Automatic drafting is off: the router links and shows only.')) : '';
    }
    function renderList() {
        q('[data-queue]').innerHTML = state.items.map(x => `<button class="snb-row ${state.selected === x.name ? 'selected' : ''}" data-row="${esc(x.name)}">
            <strong>${money(x.amount, x.currency)}</strong><span>${esc(x.event_date)} · ••${esc(x.account_tail)} · ${esc(kinds[x.kind] || '')}</span>
            <span>${esc(x.counterparty_name || x.display_name || __('Not identified'))}</span>${needs[x.decision_type] ? `<small>${esc(needs[x.decision_type])}</small>` : ''}</button>`).join('') || `<p>${__('Nothing here.')}</p>`;
    }
    function actions(x) {
        const receipt = x.kind === 'CUSTOMER_RECEIPT', type = receipt ? 'Customer' : 'Supplier';
        if (x.decision_type === 'PICK_DOCUMENT') {
            return `<h4>${__('Which document is this?')}</h4>` + (x.candidates.documents || []).map((d, i) => `<label><input type="radio" name="pick" value="${i}"> ${esc(d.doctype)} · ${esc(d.name)} · ${esc(d.date)} · ${esc(docStatus(d.docstatus))}</label>`).join('') +
                `<button class="btn btn-primary" data-pick>${__('Link')}</button>`;
        }
        if (x.decision_type === 'NEEDS_HR_LINK') return `<p>${__('This petty-cash transfer cannot be matched to an Employee until HR links the custody account.')}</p>`;
        const canRoute = ['SUPPLIER_PAYMENT', 'CUSTOMER_RECEIPT', 'EXPENSE_PAYMENT'].includes(x.kind) && (x.decision_type || x.link_method === 'AUTO_DRAFT');
        if (!canRoute) return '';
        const expense = x.kind === 'EXPENSE_PAYMENT';
        return `<h4>${expense ? __('Expense account') : __('Who is this?')}</h4><input class="form-control" data-find placeholder="${__('Type at least two characters')}" data-type="${expense ? 'Account' : type}">
            <select class="form-control" data-choice><option value="">${__('Choose…')}</option></select><button class="btn btn-primary" data-route>${__('Route here')}</button>
            ${expense ? '' : `<details><summary>${__('New {0}', [__(type)])}</summary><input class="form-control" data-new-name placeholder="${__('Full name')}"><input class="form-control" data-new-vat placeholder="${__('VAT number (optional)')}"><button class="btn btn-default" data-new>${__('Create and route')}</button></details>`}`;
    }
    function renderCard() {
        const x = selected(), c = q('[data-card]');
        if (!x) { c.innerHTML = `<p>${__('Select a movement.')}</p>`; return; }
        const fees = (x.fees || []).map(f => `<p>${f.family === 'FEE_VAT' ? 'VAT' : __('Fee')} ${money(f.amount, x.currency)} · ${f.erp_document ? '✓ ' + docLink(f.erp_doctype, f.erp_document, f.doc_status) : '○ ' + __('not posted')}</p>`).join('');
        c.innerHTML = `<div class="snb-amount">${money(x.amount, x.currency)}</div>
            <p>${esc(x.bank)} · ${esc(x.event_date)} · ••${esc(x.account_tail)} · ${__('Ref')} ${esc(x.reference || '—')}</p>
            <p><strong>${esc(x.counterparty_name || x.display_name || __('Not identified'))}</strong> · ${esc(kinds[x.kind] || '')}${x.category ? ' · ' + esc(categories[x.category] || x.category) : ''}</p>
            ${x.erp_document ? `<p>${docLink(x.erp_doctype, x.erp_document, x.doc_status)} <small>(${esc(x.link_method)})</small>${x.link_method !== 'MARKER' ? ` <button class="btn btn-xs btn-default" data-unlink>${__('Wrong match')}</button>` : ''}</p>` : ''}
            ${x.signals && x.signals.error ? `<p class="snb-error">${esc(x.signals.error)}</p>` : ''}${fees ? `<div class="snb-fees">${fees}</div>` : ''}
            <div class="snb-actions">${actions(x)}</div><div data-message></div>
            <details><summary>${__('Statement')}</summary><pre>${esc(x.narrative || '—')}</pre><small>${esc(x.name)}</small></details>`;
    }
    const render = () => { renderTabs(); renderList(); renderCard(); };
    async function load() {
        try {
            const r = (await frappe.call({method: api + 'list_inbox', args: {tab: state.tab, bank: state.bank, search: state.search, limit: 100}})).message;
            state.items = r.items; state.counts = r.counts;
            if (!state.items.some(x => x.name === state.selected)) state.selected = state.items[0]?.name || '';
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
    root.on('click', '[data-row]', function () { state.selected = this.dataset.row; render(); });
    root.on('click', '[data-refresh]', load);
    root.on('change', '[data-bank]', function () { state.bank = this.value; load(); });
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
        const x = selected(), value = q('[data-choice]').value, receipt = x.kind === 'CUSTOMER_RECEIPT';
        if (!value) { q('[data-message]').textContent = __('Choose first.'); return; }
        act('route_movement', {target: x.kind === 'EXPENSE_PAYMENT' ? {type: 'EXPENSE', account: value} : {type: 'PARTY', party_type: receipt ? 'Customer' : 'Supplier', party: value}});
    });
    root.on('click', '[data-new]', function () {
        const x = selected(), name = q('[data-new-name]').value.trim();
        if (name.length < 3) { q('[data-message]').textContent = __('Enter the full name.'); return; }
        act('route_movement', {target: {type: 'NEW_PARTY', party_type: x.kind === 'CUSTOMER_RECEIPT' ? 'Customer' : 'Supplier', name, vat: q('[data-new-vat]').value}});
    });
    root.on('click', '[data-pick]', function () {
        const x = selected(), i = (q('input[name="pick"]:checked') || {}).value;
        if (i === undefined) { q('[data-message]').textContent = __('Choose a document.'); return; }
        const d = x.candidates.documents[Number(i)]; act('pick_document', {doctype: d.doctype, document: d.name});
    });
    root.on('click', '[data-unlink]', () => act('unlink_movement', {}));
    load();
};
