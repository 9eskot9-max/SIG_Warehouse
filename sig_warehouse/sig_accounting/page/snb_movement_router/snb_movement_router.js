frappe.pages['snb-movement-router'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Bank Router'), single_column: true});
    const root = $('<main class="snb-router"></main>').appendTo(page.main), el = root[0];
    const esc = v => frappe.utils.escape_html(String(v == null ? '' : v));
    const api = 'sig_warehouse.sig_accounting.snb_movement_router.';
    const tabs = {needs: __('Needs you'), confirm: __('Confirm'), drafts: __('Drafts'), posted: __('Posted'), deferred: __('Deferred')};
    const kinds = {SUPPLIER_PAYMENT: __('Supplier payment'), CUSTOMER_RECEIPT: __('Customer receipt'), EXPENSE_PAYMENT: __('Expense, no party'), UNKNOWN: __('Unclassified outgoing'),
        PETTY_CASH: __('Petty Cash'), EMPLOYEE: __('Employee'), OWN_TRANSFER: __('Own transfer'), SPECIALIST: __('Specialist workflow'),
        BANK_CHARGE: __('Bank charge'), OTHER: __('Other')};
    const needs = {ROUTE_PARTY: __('Choose who this is'), CREATE_DRAFT: __('No draft yet'), PICK_DOCUMENT: __('Pick the matching document'),
        CONFLICT: __('Two parties claim this payer'), NEEDS_HR_LINK: __('Waiting for the HR custody link'),
        CHOOSE_TREATMENT: __('Choose PE or JE for this movement'), CHOOSE_PURPOSE: __('Choose the purpose of this employee transfer'), CONFIRM_TREATMENT: __('Confirm the payee default for this movement'),
        TREATMENT_MISMATCH: __('Linked document type differs from the selected treatment')};
    const categories = {XXPC: __('Petty Cash'), XXSL: __('Salary'), XXHR: __('HR'), XXCL: __('Deferred'), XXMT: __('Maintenance'), XXMR: __('Materials'), XXSC: __('Subcontractor'), XXLG: __('Logistics')};
    const kindGroups = {ALL: __('All'), SADAD: __('SADAD'), UNCLASSIFIED: __('Unclassified'), PETTY_CASH: __('Petty cash'), RECEIPTS: __('Receipts'), OWN_TRANSFER: __('Own transfers'),
        SUPPLIER: __('Supplier & expense'), OTHER: __('Other')};
    const state = {tab: 'needs', bank: 'ALL', search: '', items: [], counts: {}, kindCounts: {}, kindGroup: 'ALL', groupByPayee: false, selected: '', status: null,
        bulkSelected: new Set(), missingSelected: new Set(), confirmSelected: new Set(), businessChanged: new Set(), hasMore: false, openDocs: {}, supplyChoice: {}, businessChoice: {}};
    const businessRoutes = {
        supplier: [__('Supplier payment'), 'PAYMENT_ENTRY'], person_work: [__('Person or subcontractor'), ''],
        custody_topup: [__('Petty cash top-up'), 'JOURNAL_ENTRY'], employee_salary: [__('Salary'), 'JOURNAL_ENTRY'], employee_advance: [__('Employee advance'), 'JOURNAL_ENTRY'],
        employee_expense: [__('Employee expense or clearance'), 'JOURNAL_ENTRY'], own_ledger: [__('Company-use account'), 'JOURNAL_ENTRY'],
        bill: [__('SADAD bill'), 'JOURNAL_ENTRY'], bank_service: [__('Bank service'), 'JOURNAL_ENTRY'],
        client_payout: [__('Client payout'), 'PAYMENT_ENTRY'], other_out: [__('Other payment'), 'JOURNAL_ENTRY'],
        client_receipt: [__('Client receipt'), 'PAYMENT_ENTRY'], finance_manual: [__('Finance handles separately'), 'FINANCE_HANDLES']
    };
    const payeeName = x => (x.counterparty_name && x.counterparty_name !== 'Unnamed counterparty' ? x.counterparty_name : x.linked_party || x.display_name) || __('Not identified');
    // Say each thing once: the type, and the purpose only when it adds something.
    const tagLine = x => {
        const seen = new Set(), out = [];
        const reviewedRoute = businessRoutes[x.business_route]?.[0] || ({custody_topup: __('Petty cash'), own_transfer: __('Own transfer')})[x.business_route];
        [reviewedRoute || kinds[x.kind], x.category ? (categories[x.category] || x.category) : ''].forEach(t => { if (t && !seen.has(t)) { seen.add(t); out.push(t); } });
        return out.join(' · ');
    };
    const q = s => el.querySelector(s);
    let partyControl = null, invoiceControl = null, orderControl = null, employeeControl = null, custodyControl = null, counterpartyControl = null;
    const money = (n, c) => `${Number(n || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${esc(c || 'SAR')}`;
    const docStatus = s => s === 1 ? __('Posted') : s === 0 ? __('Draft') : s === 2 ? __('Cancelled') : __('Unknown');
    const selected = () => state.items.find(x => x.name === state.selected);
    const suggestedTreatment = x => x.accounting_treatment || x.purpose_default_treatment ||
        (!x.category ? x.signals?.suggested_treatment : '') || (x.is_sadad && x.direction === 'DEBIT' ? 'JOURNAL_ENTRY' : '') ||
        (x.direction === 'DEBIT' && (x.custody_choice?.company_use || x.purpose_account) ? 'JOURNAL_ENTRY' : '') ||
        (x.direction === 'CREDIT' || (!x.request_supplier_conflict && (x.linked_party || x.request_supplier)) ? 'PAYMENT_ENTRY' : '');
    const partyTypeOf = x => x.direction === 'CREDIT' ? 'Customer' : (state.partyType?.[x.name] || x.linked_party_type || 'Supplier');
    const visibleItems = () => state.items.filter(x => {
        const pair = x.signals && x.signals.paired_transfer;
        return !pair || pair.primary || !state.items.some(other => other.name === pair.name);
    });
    const docLink = (t, n, s) => n ? `<a href="#" data-erp-doctype="${esc(t)}" data-erp-name="${esc(n)}">${esc(n)}</a> · ${esc(docStatus(s))}` : '';

    root.html(`<header><h2>${__('Bank movements')}</h2><div class="snb-banner" data-banner></div></header>
        <div class="snb-controls"><select data-bank><option value="ALL">${__('All banks')}</option><option value="SNB">SNB</option><option value="ALINMA">Alinma</option></select>
        <input class="form-control" data-search type="search" placeholder="${__('Search name, reference or document')}"><button class="btn btn-default" data-refresh>${__('Refresh')}</button>
        <label class="snb-group-toggle"><input type="checkbox" data-group-payee> ${__('Group by payee')}</label></div>
        <nav data-tabs></nav><nav class="snb-types" data-types></nav><section class="snb-grid"><aside><div class="snb-bulk" data-standard-bulk><button class="btn btn-default" data-bulk>${__('Confirm selected unique matches')}</button><button class="btn btn-default" data-select-missing>${__('Select missing links on this page')}</button><button class="btn btn-default" data-clear-selected>${__('Clear selected missing links')}</button><button class="btn btn-default" data-confirm-employees>${__('Confirm verified employees')}</button></div><div class="snb-bulk" data-confirm-bulk hidden><button class="btn btn-default" data-confirm-drafts>${__('Create selected drafts')}</button><button class="btn btn-default" data-confirm-posts>${__('Post selected')}</button></div><div data-queue></div><button class="btn btn-default" data-more hidden>${__('Load more')}</button></aside><article data-card></article></section>`);

    function renderTabs() {
        q('[data-tabs]').innerHTML = Object.entries(tabs).map(([k, label]) =>
            `<button class="btn ${state.tab === k ? 'btn-primary' : 'btn-default'}" data-tab="${k}">${label} · ${state.counts[k] ?? 0}</button>`).join('');
        q('[data-types]').innerHTML = Object.entries(kindGroups).map(([k, label]) =>
            `<button class="btn btn-sm ${state.kindGroup === k ? 'btn-primary' : 'btn-default'}" data-kind="${k}">${label} · ${state.kindCounts[k] ?? 0}</button>`).join('');
        q('[data-types]').hidden = state.tab === 'confirm';
        q('[data-standard-bulk]').hidden = state.tab === 'confirm';
        q('[data-confirm-bulk]').hidden = state.tab !== 'confirm';
        q('[data-confirm-posts]').hidden = !state.status?.can_submit_journal_entry;
        const s = state.status;
        q('[data-banner]').textContent = s ? __('Review each movement before creating its draft.') : '';
    }
    function renderList() {
        q('[data-more]').hidden = !state.hasMore;
        let rows = visibleItems(), lastGroup = null;
        if (state.groupByPayee) rows = rows.slice().sort((a, b) => payeeName(a).localeCompare(payeeName(b)) || String(b.event_date).localeCompare(String(a.event_date)));
        const groupSize = n => rows.filter(r => payeeName(r) === n).length;
        q('[data-queue]').innerHTML = rows.map(x => `${state.groupByPayee && payeeName(x) !== lastGroup ? `<h5 class="snb-group-head">${esc(lastGroup = payeeName(x))} · ${groupSize(payeeName(x))}</h5>` : ''}<div class="snb-row-wrap">${x.confirmation ? `<label class="snb-bulk-check"><input type="checkbox" data-confirm-select value="${esc(x.name)}" ${state.confirmSelected.has(x.name) ? 'checked' : ''}></label>` : ''}${x.erp_document && x.doc_status == null ? `<label class="snb-bulk-check"><input type="checkbox" data-missing-select value="${esc(x.name)}" ${state.missingSelected.has(x.name) ? 'checked' : ''}></label>` : ''}${x.decision_type === 'PICK_DOCUMENT' && (x.candidates.documents || []).length === 1 ? `<label class="snb-bulk-check"><input type="checkbox" data-bulk-select value="${esc(x.name)}" ${state.bulkSelected.has(x.name) ? 'checked' : ''}></label>` : ''}<button class="snb-row ${state.selected === x.name ? 'selected' : ''}" data-row="${esc(x.name)}">
            <strong>${money(x.amount, x.currency)}</strong><span>${esc(x.event_date)} · ••${esc(x.account_tail)} · ${esc(tagLine(x))}</span>
            <span>${esc(payeeName(x))}</span>${x.confirmation ? `<small>${__('Debit')} ${esc(x.confirmation.debit)} · ${__('Credit')} ${esc(x.confirmation.credit)}</small>${(x.confirmation.fee_accounts || []).map(fee => `<small>${esc(fee.family === 'FEE_VAT' ? __('VAT') : __('Fee'))} · ${esc(fee.account || __('Account not configured'))} · ${money(fee.amount, x.currency)}</small>`).join('')}` : ''}${needs[x.decision_type] ? `<small>${esc(needs[x.decision_type])}</small>` : ''}</button></div>`).join('') || `<p>${__('Nothing here.')}</p>`;
    }
    const supplyOf = x => state.supplyChoice[x.name] ?? x.supply_type ?? '';
    const supplyHtml = x => `<label>${__('Type of supply')}</label><select class="form-control" data-supply><option value="">${__('Choose…')}</option>${x.supply_types.map(t =>
        `<option value="${esc(t.code)}" ${supplyOf(x) === t.code ? 'selected' : ''}>${esc(t.label)}</option>`).join('')}</select>`;
    // What this supplier's payment can rest on. A receipt is only a hint: the invoice is made from it, then paid.
    async function loadOpenDocs(x) {
        const host = q('[data-open-docs]'), supplier = partyControl?.get_value();
        if (!host) return;
        if (!supplier) { host.innerHTML = ''; return; }
        const amount = Math.abs(Number(x.amount || 0)), orderChosen = !!orderControl?.get_value();
        const flag = amount > (x.supply_threshold || 20000) && !orderChosen
            ? `<p class="snb-error">${__('Above SAR {0} (VAT included): a Purchase Order is expected for this supplier payment.', [Number(x.supply_threshold || 20000).toLocaleString()])}</p>` : '';
        let docs = state.openDocs[x.name + '|' + supplier];
        if (!docs) {
            try { docs = state.openDocs[x.name + '|' + supplier] = (await frappe.call({method: api + 'supplier_open_documents', args: {name: x.name, supplier}})).message; }
            catch (e) { host.innerHTML = flag; return; }
        }
        if (partyControl?.get_value() !== supplier) return;
        const line = d => `<p>${d.exact ? '<strong>' : ''}${esc(d.doctype)} <a href="#" data-erp-doctype="${esc(d.doctype)}" data-erp-name="${esc(d.name)}">${esc(d.name)}</a> · ${esc(d.date)} · ${money(d.open ?? d.total)}${d.exact ? ' · ' + __('same amount') + '</strong>' : ''}`;
        const usable = d => `${line(d)} <button class="btn btn-xs btn-default" data-use-doc="${esc(d.doctype)}|${esc(d.name)}">${__('Use')}</button></p>`;
        const hint = d => `${line(d)}${d.exact ? ' · ' + __('make the Purchase Invoice from this receipt first, then pay that invoice') : ''}</p>`;
        const parts = [];
        if (docs.invoices?.length) parts.push(`<h5>${__('Open Purchase Invoices')}</h5>${docs.invoices.map(usable).join('')}`);
        if (docs.orders?.length) parts.push(`<h5>${__('Open Purchase Orders')}</h5>${docs.orders.map(usable).join('')}`);
        if (docs.receipts?.length) parts.push(`<h5>${__('Receipts waiting to be billed')}</h5>${docs.receipts.map(hint).join('')}`);
        if (docs.restricted?.length) parts.push(`<p><small>${__('Not shown: you cannot read {0}.', [docs.restricted.join(', ')])}</small></p>`);
        host.innerHTML = flag + (parts.join('') || `<p><small>${__('Nothing open for this supplier.')}</small></p>`);
    }
    function actions(x) {
        if (x.decision_type === 'PICK_DOCUMENT') {
            return `<h4>${__('Which document is this?')}</h4>` + (x.candidates.documents || []).map((d, i) => `<label><input type="radio" name="pick" value="${i}"> ${esc(d.doctype)} · ${esc(d.name)} · ${esc(d.date)} · ${esc(docStatus(d.docstatus))}</label>`).join('') +
                `<button class="btn btn-primary" data-pick>${__('Link')}</button>`;
        }
        if (x.kind === 'OWN_TRANSFER' && !x.erp_document && x.signals?.paired_transfer) return `<p>${__('This pair moves money between company bank accounts. Review both legs before creating one draft.')}</p><button class="btn btn-primary" data-own-transfer>${__('Create one transfer draft')}</button> ${state.status?.can_submit_journal_entry ? `<button class="btn btn-default" data-own-transfer-post>${__('Create and post')}</button>` : ''}`;
        if (x.kind === 'PETTY_CASH' && !x.erp_document && x.pc_employee) return `<button class="btn btn-default" data-clear-pc>${__('Change purpose')}</button>`;
        if (x.kind === 'PETTY_CASH' && !x.erp_document) return `${x.pc_employee_suggestion ? `<p>${__('Employee')}: <strong>${esc(x.pc_employee_suggestion.name)}</strong> · ${esc(x.pc_employee_suggestion.account)}</p><button class="btn btn-primary" data-confirm-pc>${__('Confirm')}</button> <button class="btn btn-default" data-change-employee>${__('Change')}</button>` : `<p>${__('Choose the Employee who holds this custody.')}</p><button class="btn btn-primary" data-confirm-pc>${__('Confirm Employee')}</button>`}<div data-employee-control ${x.pc_employee_suggestion ? 'hidden' : ''}></div><details><summary>${__('Not an Employee: use a company custody account')}</summary><div data-custody-control></div><button class="btn btn-default" data-confirm-custody>${__('Confirm custody account')}</button></details>`;
        const canRoute = (!x.erp_document || x.doc_status === 0) && ['SUPPLIER_PAYMENT', 'CUSTOMER_RECEIPT', 'EXPENSE_PAYMENT', 'UNKNOWN', 'EMPLOYEE'].includes(x.kind) &&
            (x.decision_type || x.link_method === 'AUTO_DRAFT' || (x.direction === 'DEBIT' && ['UNKNOWN', 'EMPLOYEE'].includes(x.kind)));
        if (!canRoute) return '';
        const chosenRoute = state.businessChoice[x.name] ?? x.business_route ?? '';
        const treatment = chosenRoute ? suggestedTreatment(x) : '';
        const expense = treatment === 'JOURNAL_ENTRY';
        const partyType = partyTypeOf(x);
        const employeePurpose = chosenRoute.startsWith('employee_');
        const options = Object.entries(businessRoutes).filter(([code]) => x.direction === 'CREDIT' ? ['client_receipt', 'finance_manual'].includes(code) : code !== 'client_receipt' && (code !== 'custody_topup' || !x.erp_document));
        if (chosenRoute === 'custody_topup' && x.direction === 'DEBIT' && !x.erp_document) return `<h4>${__('Purpose')}</h4><select class="form-control" data-business-route><option value="">${__('Choose purpose…')}</option>${options.map(([code, [label]]) => `<option value="${esc(code)}" ${chosenRoute === code ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select><p>${__('Choose the Employee who received the top-up. Confirming marks the movement for petty cash; creating the Journal Entry is a separate step.')}</p><div data-employee-control></div><button class="btn btn-primary" data-confirm-pc>${__('Confirm petty cash')}</button>`;
        return `${x.direction === 'DEBIT' && !x.erp_document && !employeePurpose ? `<details><summary>${__('Designate as employee petty cash')}</summary><div data-employee-control></div><button class="btn btn-default" data-confirm-pc>${__('Confirm petty cash')}</button></details>` : ''}${x.suggested_counterparty ? `<p>${__('Payee (from the bank name)')}: <strong>${esc(x.suggested_counterparty.display_name)}</strong>${x.suggested_counterparty.label ? ' · ' + esc(x.suggested_counterparty.label) : ''}</p>` : ''}<h4>${__('Purpose')}</h4><select class="form-control" data-business-route><option value="">${__('Choose purpose…')}</option>${options.map(([code, [label]]) => `<option value="${esc(code)}" ${chosenRoute === code ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select>${employeePurpose ? '<div data-employee-control></div>' : ''}
            ${chosenRoute === 'person_work' ? `<h4>${__('Accounting treatment')}</h4>` : ''}
            <select class="form-control" data-treatment ${chosenRoute !== 'person_work' ? 'hidden' : ''}><option value="">${__('Choose treatment…')}</option>
                <option value="PAYMENT_ENTRY" ${treatment === 'PAYMENT_ENTRY' ? 'selected' : ''}>${__('Payment Entry')}</option>
                <option value="JOURNAL_ENTRY" ${treatment === 'JOURNAL_ENTRY' ? 'selected' : ''} ${x.direction === 'CREDIT' ? 'disabled' : ''}>${__('Journal Entry')}</option>
                <option value="FINANCE_HANDLES" ${treatment === 'FINANCE_HANDLES' ? 'selected' : ''}>${__('Finance handles outside this router')}</option></select>
            ${treatment === 'FINANCE_HANDLES' ? `<button class="btn btn-primary" data-route>${__('Save decision')}</button>` : ''}
            ${treatment && treatment !== 'FINANCE_HANDLES' ? `<h4>${expense ? __('Account') : __(partyType)}</h4>${!expense && x.direction === 'DEBIT' ? `<select class="form-control" data-party-type><option value="Supplier" ${partyType === 'Supplier' ? 'selected' : ''}>${__('Supplier')}</option><option value="Customer" ${partyType === 'Customer' ? 'selected' : ''}>${__('Customer (money out to a client)')}</option></select>` : ''}${x.request_supplier_conflict ? `<p class="snb-error">${__('The matched transfer request names a different supplier. Review both before routing.')}</p>` : ''}${!expense && x.request_supplier ? `<p>${__('Matched TX Manager supplier:')} ${esc(x.request_supplier)}</p>` : ''}${!expense && x.suggested_parties?.length ? `<p>${__('Possible match; confirm before routing:')} ${x.suggested_parties.map(p => `<button class="btn btn-xs btn-default" data-suggested-party="${esc(p)}">${esc(p)}</button>`).join(' ')}</p>` : ''}<div data-link-control></div>${expense && x.is_sadad ? `<label>${__('Existing bank counterparty (optional)')}</label><div data-counterparty-control></div>` : ''}${expense && x.custody_choice ? `<p>${x.custody_choice.company_use ? __('Company-use ledger of {0}', [esc(x.custody_choice.name)]) : __('Employee custody ledger of {0}', [esc(x.custody_choice.name)])} <button class="btn btn-xs btn-default" data-pick-account="${esc(x.custody_choice.account)}">${esc(x.custody_choice.account)}</button></p>` : ''}${expense && x.account_choices?.length ? `<p>${__('Government fee: choose the account')} ${x.account_choices.map(a => `<button class="btn btn-xs btn-default" data-pick-account="${esc(a)}">${esc(a)}</button>`).join(' ')}</p>` : ''}${x.direction === 'DEBIT' && x.supply_types?.length && !(expense && x.account_choices?.length) ? supplyHtml(x) : ''}${!expense && x.direction === 'DEBIT' ? '<div data-open-docs></div>' : ''}${!expense ? `<div data-invoice-control></div>${x.direction === 'DEBIT' ? '<div data-order-control></div>' : ''}` : ''}<button class="btn btn-primary" data-route>${__('Create draft')}</button> ${(treatment === 'JOURNAL_ENTRY' ? state.status?.can_submit_journal_entry : state.status?.can_submit_payment_entry) ? `<button class="btn btn-default" data-route-post>${__('Create and post')}</button>` : ''}
            ${expense && payeeName(x) === __('Not identified') ? `<input class="form-control" data-label placeholder="${__('Who or what is this for? (optional)')}" value="${esc(x.bill_owner ? x.bill_owner.name : '')}">` : ''}
            <button class="btn btn-default" data-preview-route>${__('Preview accounts')}</button>
            <label><input type="checkbox" data-remember checked> ${__('Remember the default treatment for this payee')}</label>
            ${expense ? '' : `<details><summary>${__('New {0}', [__(partyType)])}</summary><input class="form-control" data-new-name placeholder="${__('Full name')}"><input class="form-control" data-new-vat placeholder="${__('VAT number (optional)')}">${partyType === 'Customer' ? `<label>${__('Country')}</label><input class="form-control" data-new-country value="Saudi Arabia" placeholder="${__('Country name')}">` : ''}<button class="btn btn-default" data-new>${__('Create and route')}</button></details>`}` : ''}`;
    }
    function renderCard() {
        const x = selected(), c = q('[data-card]');
        partyControl = null; invoiceControl = null; orderControl = null; employeeControl = null; custodyControl = null; counterpartyControl = null;
        if (!x) { c.innerHTML = `<p>${__('Select a movement.')}</p>`; return; }
        const feeRows = (x.fees || []), feeTotal = feeRows.reduce((sum, f) => sum + Math.abs(Number(f.amount || 0)), 0);
        const fees = feeRows.length ? `<details class="snb-fees"><summary>${__('Related fees and VAT')} · ${money(feeTotal, x.currency)}</summary>${feeRows.map(f => `<p>${f.family === 'FEE_VAT' ? 'VAT' : __('Fee')} ${money(f.amount, x.currency)} · ${f.erp_document ? (f.doc_status === 1 ? '✓ ' : '○ ') + docLink(f.erp_doctype, f.erp_document, f.doc_status) : '○ ' + __('not posted')}</p>`).join('')}</details>` : '';
        c.innerHTML = `<div class="snb-amount">${money(x.amount, x.currency)}</div>
            <p>${esc(x.bank_account || x.bank)} · ${esc(x.event_date)} · ••${esc(x.account_tail)} · ${__('Ref')} ${esc(x.reference || '—')}</p>
            <p><strong>${esc(payeeName(x))}</strong> · ${esc(tagLine(x))}</p>
            ${!x.business_route && x.business_route_suggestion?.route && state.businessChoice[x.name] === x.business_route_suggestion.route ? `<p><small>${x.business_route_suggestion.evidence?.includes('confirmed_memory') ? __('Suggested from a confirmed payee default') : x.business_route_suggestion.evidence?.includes('tx_category') ? __('Suggested from the transfer purpose') : x.business_route_suggestion.evidence?.includes('sheet_label') ? __('Suggested from the beneficiary label') : __('Suggested from the payee type')}</small></p>` : ''}
            ${x.confirmation ? `<p>${__('Debit')} · ${esc(x.confirmation.debit)}<br>${__('Credit')} · ${esc(x.confirmation.credit)}</p>` : ''}
            ${x.pc_employee ? `<p>${__('Confirmed Employee:')} ${esc(x.pc_employee_name || x.pc_employee)}${x.pc_custody_account ? ' · ' + esc(x.pc_custody_account) : ''}</p>` : ''}
            ${x.request_supplier ? `<p>${__('Matched TX Manager supplier:')} <strong>${esc(x.request_supplier)}</strong>${x.request_supplier_conflict ? ' · ' + __('Differs from the currently linked supplier; review both.') : ''}</p>` : ''}
            ${x.signals && x.signals.biller_code ? `<p>${__('SADAD biller')} ${esc(x.signals.biller_code)}${x.signals.biller_name ? ' · ' + esc(x.signals.biller_name) : ' · ' + __('not on the public SADAD list')}${x.signals.bill_account ? ' · ' + __('bill') + ' ' + esc(x.signals.bill_account) : ''}${x.bill_owner ? ' · ' + __('Iqama of {0}', [esc(x.bill_owner.name)]) : ''}</p>` : ''}
            ${x.signals && x.signals.paired_transfer ? `<p>${__('Paired own-account transfer')} · ${esc(x.signals.paired_transfer.source_key || '')}</p>` : ''}
            ${x.erp_document ? `<p>${x.doc_status === 1 ? '✓ ' : '○ '}${docLink(x.erp_doctype, x.erp_document, x.doc_status)} <small>(${esc(x.link_method)})</small>${x.doc_status != null ? ` <button class="btn btn-xs btn-default" data-preview-entry>${__('Preview entry')}</button>` : ''}${x.doc_status == null ? ` <button class="btn btn-xs btn-default" data-clear-missing>${__('Check and clear missing link')}</button>` : x.link_method !== 'MARKER' ? ` <button class="btn btn-xs btn-default" data-unlink>${__('Wrong match')}</button>` : ''}</p>` : ''}
            ${x.signals && x.signals.error ? `<p class="snb-error">${esc(x.signals.error)}</p>` : ''}${fees}
            <div class="snb-actions">${actions(x)}${x.decision_type === 'CREATE_DRAFT' && !x.erp_document ? `<button class="btn btn-primary" data-create-draft>${__('Create reviewed draft')}</button> ${(x.accounting_treatment === 'JOURNAL_ENTRY' ? state.status?.can_submit_journal_entry : state.status?.can_submit_payment_entry) ? `<button class="btn btn-default" data-reviewed-post>${__('Create and post')}</button>` : ''}` : ''}</div><div data-message></div>
            <details><summary>${__('Statement')}</summary><pre>${esc(x.narrative || '—')}</pre><small>${esc(x.name)}</small></details>`;
        const employeeHost = q('[data-employee-control]');
        if (employeeHost) {
            if (!(state.businessChoice[x.name] ?? x.business_route ?? '').startsWith('employee_')) employeeHost.insertAdjacentHTML('afterend', `<label><input type="checkbox" data-pc-remember checked> ${__('Remember this petty-cash purpose for tagged transfers')}</label>`);
            employeeControl = frappe.ui.form.make_control({parent: $(employeeHost), df: {fieldtype:'Link', fieldname:'router_employee', options:'Employee', label:__('Employee'),
                get_query: () => ({filters:{status:'Active', company:x.company}})}, render_input:true});
            employeeControl.refresh();
            if (x.pc_employee || x.pc_employee_suggestion?.employee) employeeControl.set_value(x.pc_employee || x.pc_employee_suggestion.employee);
        }
        const custodyHost = q('[data-custody-control]');
        if (custodyHost) {
            custodyControl = frappe.ui.form.make_control({parent: $(custodyHost), df: {fieldtype:'Link', fieldname:'router_custody', options:'Account', label:__('Company custody ledger'),
                get_query: () => ({filters:{company:x.company, root_type:'Asset', is_group:0, disabled:0}})}, render_input:true});
            custodyControl.refresh();
            if (x.accounting_account && !x.pc_employee) custodyControl.set_value(x.accounting_account);
        }
        const host = q('[data-link-control]');
        if (host) {
            const treatment = suggestedTreatment(x);
            const doctype = treatment === 'JOURNAL_ENTRY' ? 'Account' : partyTypeOf(x);
            partyControl = frappe.ui.form.make_control({parent: $(host), df: {fieldtype: 'Link', fieldname: 'router_party', options: doctype,
                label: doctype === 'Account' ? __('Account') : __(doctype),
                get_query: () => ({filters: doctype === 'Account' ? {account_type: ['not in', ['Receivable', 'Payable']], is_group: 0, disabled: 0, company: x.company} : {disabled: 0}}),
                change: () => { if (doctype === 'Supplier' && x.direction === 'DEBIT') loadOpenDocs(x); }}, render_input: true});
            partyControl.refresh();
            const typeAccount = code => (x.supply_types || []).find(t => t.code === code)?.account || '';
            const route = state.businessChoice[x.name] ?? x.business_route ?? '';
            const hint = x.business_route_suggestion || {};
            const remembered = hint.route === route && hint.evidence?.includes('confirmed_memory') ? hint : {};
            const matchingTag = hint.route === route && hint.evidence?.includes('tx_category');
            const savedAccount = state.businessChanged.has(x.name) ? '' : x.accounting_account;
            const value = doctype === 'Account' ? (savedAccount || remembered.account || (route === 'own_ledger' && x.custody_choice?.company_use ? x.custody_choice.account : '') || (matchingTag ? x.purpose_account : '') || (route === 'person_work' ? typeAccount(supplyOf(x)) : '') || (matchingTag ? x.signals?.suggested_account : '')) : x.request_supplier_conflict ? '' : ((x.linked_party_type === doctype ? x.linked_party : '') || (remembered.party_type === doctype ? remembered.party : '') || (doctype === 'Supplier' ? x.request_supplier : ''));
            if (value) partyControl.set_value(value);
            const makeReferenceControl = (selector, referenceType, label) => {
                const referenceHost = q(selector);
                if (!referenceHost) return null;
                const control = frappe.ui.form.make_control({parent: $(referenceHost), df: {fieldtype: 'Link', fieldname: 'router_' + referenceType.replaceAll(' ', '_'), options: referenceType, label,
                    get_query: () => ({filters: {...(x.direction === 'CREDIT' ? {customer: partyControl?.get_value() || ''} : {supplier: partyControl?.get_value() || ''}), docstatus: 1, company: x.company}})}, render_input: true});
                control.refresh();
                if (x.payment_reference_doctype === referenceType && x.payment_reference) control.set_value(x.payment_reference);
                return control;
            };
            invoiceControl = makeReferenceControl('[data-invoice-control]', x.direction === 'CREDIT' ? 'Sales Invoice' : 'Purchase Invoice', __('Invoice (optional)'));
            orderControl = makeReferenceControl('[data-order-control]', 'Purchase Order', __('Purchase Order advance (optional)'));
            if (orderControl) orderControl.df.change = () => loadOpenDocs(x);
            if (doctype === 'Supplier' && x.direction === 'DEBIT') loadOpenDocs(x);
        }
        const counterpartyHost = q('[data-counterparty-control]');
        if (counterpartyHost) {
            counterpartyControl = frappe.ui.form.make_control({parent: $(counterpartyHost), df: {fieldtype: 'Link', fieldname: 'router_counterparty', options: 'Bank Counterparty',
                label: __('Existing bank counterparty'), get_query: () => ({filters: {status: 'ACTIVE'}})}, render_input: true});
            counterpartyControl.refresh();
            if (x.counterparty) counterpartyControl.set_value(x.counterparty);
        }
    }
    const render = () => { renderTabs(); renderList(); renderCard(); };
    async function load(append = false) {
        try {
            const confirming = state.tab === 'confirm';
            const args = confirming ? {bank: state.bank, search: state.search, start: append ? state.nextStart || 0 : 0, limit: 100} : {tab: state.tab, bank: state.bank, search: state.search, kind_group: state.kindGroup, start: append ? state.nextStart || 0 : 0, limit: 100};
            const r = (await frappe.call({method: api + (confirming ? 'list_confirmation_queue' : 'list_inbox'), args})).message;
            state.items = append ? state.items.concat(r.items) : r.items;
            if (confirming) state.counts.confirm = r.count; else { state.counts = r.counts; state.kindCounts = r.kind_counts || {}; }
            state.hasMore = r.has_more;
            for (const item of r.items) {
                const hint = item.business_route_suggestion;
                if (item.business_route && businessRoutes[item.business_route] && state.businessChoice[item.name] === undefined) state.businessChoice[item.name] = item.business_route;
                if (!item.erp_document && hint?.evidence?.length && businessRoutes[hint.route] && state.businessChoice[item.name] === undefined) {
                    const rememberedTreatment = businessRoutes[hint.route][1] || (hint.party_type ? 'PAYMENT_ENTRY' : hint.account ? 'JOURNAL_ENTRY' : '');
                    if (!item.accounting_treatment || !rememberedTreatment || item.accounting_treatment === rememberedTreatment) {
                        state.businessChoice[item.name] = hint.route;
                        if (!item.accounting_treatment) item.accounting_treatment = rememberedTreatment;
                        if (hint.party_type) { state.partyType = state.partyType || {}; state.partyType[item.name] = hint.party_type; }
                    }
                }
                if (!item.erp_document && item.direction === 'CREDIT' && state.businessChoice[item.name] === undefined) {
                    state.businessChoice[item.name] = 'client_receipt';
                }
            }
            state.nextStart = r.next_start;
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
    root.on('click', '[data-tab]', function () { state.tab = this.dataset.tab; state.selected = ''; state.missingSelected.clear(); state.confirmSelected.clear(); load(); });
    root.on('click', '[data-kind]', function () { state.kindGroup = this.dataset.kind; state.selected = ''; state.missingSelected.clear(); load(); });
    root.on('change', '[data-group-payee]', function () { state.groupByPayee = this.checked; renderList(); });
    root.on('change', '[data-supply]', function () {
        const x = selected(); if (!x) return;
        const previous = (x.supply_types || []).find(t => t.code === supplyOf(x))?.account || '';
        state.supplyChoice[x.name] = this.value;
        const next = (x.supply_types || []).find(t => t.code === this.value)?.account || '';
        const current = partyControl?.get_value();
        // On a Journal Entry the type picks the expense account, unless Finance already chose a different one.
        if (partyControl && partyControl.df.options === 'Account' && next && (!current || current === previous)) partyControl.set_value(next);
    });
    root.on('click', '[data-use-doc]', function () {
        const [doctype, name] = this.dataset.useDoc.split('|');
        const control = doctype === 'Purchase Order' ? orderControl : invoiceControl, other = doctype === 'Purchase Order' ? invoiceControl : orderControl;
        if (other) other.set_value('');
        if (control) control.set_value(name);
        const x = selected(); if (x) loadOpenDocs(x);
    });
    root.on('change', '[data-bulk-select]', function () { this.checked ? state.bulkSelected.add(this.value) : state.bulkSelected.delete(this.value); });
    root.on('change', '[data-confirm-select]', function () { this.checked ? state.confirmSelected.add(this.value) : state.confirmSelected.delete(this.value); });
    root.on('click', '[data-confirm-drafts], [data-confirm-posts]', function () {
        const items = state.items.filter(x => state.confirmSelected.has(x.name)).map(x => ({name: x.name, modified: x.modified, reviewed_accounts: [x.confirmation.debit, x.confirmation.credit], reviewed_fees: x.confirmation.fee_accounts}));
        if (!items.length || items.length > 100) { frappe.msgprint(__('Select up to 100 movements.')); return; }
        const mode = this.hasAttribute('data-confirm-posts') ? 'post' : 'draft';
        frappe.confirm(__('Review the displayed accounts, then {0} {1} selected movements?', [mode === 'post' ? __('post') : __('create drafts for'), items.length]), async () => {
            try {
                const result = (await frappe.call({method: api + 'bulk_confirm_routes', type: 'POST', args: {items, mode}})).message;
                state.confirmSelected.clear(); await load();
                const lines = result.items.map(row => `${esc(row.name)} · ${esc(row.status)}${row.document ? ' · ' + esc(row.document) : ''}${row.error ? ' · ' + esc(row.error) : ''}`).join('<br>');
                frappe.msgprint({title: __('Confirmation results'), message: lines});
            } catch (e) { frappe.msgprint(__('Could not process the selected movements. Refresh and review them.')); }
        });
    });
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
    root.on('change', '[data-missing-select]', function () { this.checked ? state.missingSelected.add(this.value) : state.missingSelected.delete(this.value); });
    root.on('click', '[data-select-missing]', function () {
        state.items.filter(x => x.erp_document && x.doc_status == null).slice(0, 100).forEach(x => state.missingSelected.add(x.name));
        renderList();
    });
    root.on('click', '[data-clear-selected]', async function () {
        const items = state.items.filter(x => state.missingSelected.has(x.name)).map(x => ({name: x.name, modified: x.modified}));
        if (!items.length || items.length > 100) { frappe.msgprint(__('Select up to 100 missing links.')); return; }
        try {
            const result = (await frappe.call({method: api + 'bulk_clear_missing_documents', type: 'POST', args: {items}})).message;
            state.missingSelected.clear(); await load();
            frappe.show_alert({message: __('Cleared {0} missing links.', [result.cleared]), indicator: 'green'});
        } catch (e) { frappe.msgprint(__('No links were cleared. Refresh and check that each linked document is absent.')); }
    });
    root.on('click', '[data-row]', function () { state.selected = this.dataset.row; render(); });
    root.on('click', '[data-refresh]', () => load());
    root.on('click', '[data-more]', () => load(true));
    root.on('click', '[data-create-draft]', () => act('create_reviewed_draft', {}));
    root.on('click', '[data-own-transfer]', () => act('create_own_transfer_draft', {}));
    root.on('click', '[data-reviewed-post], [data-own-transfer-post]', function () {
        const x = selected(), method = this.hasAttribute('data-own-transfer-post') ? 'create_and_post_own_transfer' : 'create_and_post_reviewed_draft';
        frappe.confirm(__('Create and post this reviewed entry?'), async () => {
            try {
                const result = (await frappe.call({method: api + method, type: 'POST', args: {name: x.name, modified: x.modified}})).message;
                await load();
                if (result.post_error) frappe.msgprint(__('Draft created. Posting failed: {0}', [esc(result.post_error)]));
                else frappe.show_alert({message: __('Posted'), indicator: 'green'});
            } catch (e) { frappe.msgprint(__('Could not create the entry. Refresh and review it.')); }
        });
    });
    root.on('click', '[data-confirm-pc]', () => { const x = selected(), employee = employeeControl?.get_value(); if (!employee) { q('[data-message]').textContent = __('Choose an Employee.'); return; } act('confirm_petty_cash_employee', {employee, counterparty: x.suggested_counterparty?.name || '', remember: q('[data-pc-remember]')?.checked ? 1 : 0}); });
    root.on('click', '[data-clear-pc]', () => act('clear_petty_cash_designation', {}));
    root.on('click', '[data-change-employee]', () => { q('[data-employee-control]').hidden = false; employeeControl?.set_value(''); });
    root.on('click', '[data-confirm-custody]', () => { const account = custodyControl?.get_value(); if (!account) { q('[data-message]').textContent = __('Choose a custody ledger.'); return; } act('confirm_petty_cash_custody', {account}); });
    root.on('change', '[data-bank]', function () { state.bank = this.value; load(); });
    root.on('change', '[data-treatment]', function () { const x = selected(); if (x) x.accounting_treatment = this.value; renderCard(); });
    root.on('change', '[data-business-route]', function () {
        const x = selected(); if (!x) return;
        if (this.value !== (state.businessChoice[x.name] ?? x.business_route ?? '')) state.businessChanged.add(x.name);
        state.businessChoice[x.name] = this.value;
        const treatment = businessRoutes[this.value]?.[1] || '';
        x.accounting_treatment = treatment;
        if (this.value === 'client_payout') { state.partyType = state.partyType || {}; state.partyType[x.name] = 'Customer'; }
        if (this.value === 'supplier' || this.value === 'person_work') { state.partyType = state.partyType || {}; state.partyType[x.name] = 'Supplier'; }
        renderCard();
    });
    root.on('input', '[data-search]', function () { const v = this.value; clearTimeout(timer); timer = setTimeout(() => { state.search = v; load(); }, 300); });
    root.on('click', '[data-suggested-party]', function () { if (partyControl) partyControl.set_value(this.dataset.suggestedParty); });
    root.on('click', '[data-confirm-employees]', async function () {
        try {
            const plan = (await frappe.call({method: api + 'bulk_confirm_verified_employees', type: 'POST', args: {apply: 0}})).message;
            if (!plan.payees.length) { frappe.msgprint(__('No payee has a verified Employee waiting for confirmation.')); return; }
            const list = plan.payees.map(p => `${esc(p.payee)} → ${esc(p.name)} · ${esc(p.account)} (${p.lines})`).join('<br>');
            frappe.confirm(__('Confirm these {0} payees as Employees with their custody ledger?', [plan.payees.length]) + '<br><br>' + list, async () => {
                const done = (await frappe.call({method: api + 'bulk_confirm_verified_employees', type: 'POST', args: {apply: 1}})).message;
                frappe.show_alert({message: __('Confirmed {0} payees.', [done.applied]), indicator: 'green'});
                load();
            });
        } catch (e) { frappe.msgprint(__('Could not confirm employees. Check your access.')); }
    });
    root.on('change', '[data-party-type]', function () { const x = selected(); if (!x) return; state.partyType = state.partyType || {}; state.partyType[x.name] = this.value; renderCard(); });
    root.on('click', '[data-pick-account]', function () { if (partyControl) partyControl.set_value(this.dataset.pickAccount); });
    root.on('click', '[data-preview-route]', async function () {
        const x = selected(), treatment = q('[data-treatment]')?.value, value = partyControl?.get_value();
        if (!value) { q('[data-message]').textContent = __('Choose an account or party first.'); return; }
        const target = treatment === 'JOURNAL_ENTRY' ? {treatment, account: value} : {treatment, party_type: partyTypeOf(x), party: value};
        try {
            const p = (await frappe.call({method: api + 'preview_route', type: 'POST', args: {name: x.name, target}})).message;
            const feeNote = (p.fees || []).map(row => `<p>${esc(row.family === 'FEE_VAT' ? __('VAT') : __('Fee'))} · ${__('Debit')} ${esc(row.debit || __('Account not configured'))} · ${__('Credit')} ${esc(row.credit)} · ${money(row.amount, p.currency)}</p>`).join('');
            const feeDocument = p.fee_document ? `<p>${__('Fees use a separate Journal Entry.')}</p>` : '';
            frappe.msgprint({title: __('Proposed accounts'), message: `<p>${__('Debit')} · ${esc(p.debit)} · ${money(p.amount, p.currency)}</p><p>${__('Credit')} · ${esc(p.credit)} · ${money(p.amount, p.currency)}</p>${feeNote}${feeDocument}`});
        } catch (e) { q('[data-message]').textContent = __('Could not preview these accounts. Check the selected party and account access.'); }
    });
    root.on('click', '[data-route], [data-route-post]', async function () {
        const x = selected(), treatment = q('[data-treatment]').value, remember = q('[data-remember]')?.checked ? '1' : '0';
        if (!treatment) { q('[data-message]').textContent = __('Choose the treatment first.'); return; }
        if (treatment === 'FINANCE_HANDLES') { act('route_movement', {target: {type: 'FINANCE_HANDLES', treatment}}); return; }
        const value = partyControl?.get_value();
        if (!value) { q('[data-message]').textContent = __('Choose first.'); return; }
        const invoice = invoiceControl?.get_value() || '', order = orderControl?.get_value() || '';
        if (invoice && order) { q('[data-message]').textContent = __('Choose an invoice or a purchase order, not both.'); return; }
        const reference_doctype = order ? 'Purchase Order' : invoice ? (x.direction === 'CREDIT' ? 'Sales Invoice' : 'Purchase Invoice') : '';
        const supply_type = q('[data-supply]')?.value || '';
        const business_route = state.businessChoice[x.name] ?? x.business_route ?? '';
        const matchingTags = {supplier: ['XXMR'], person_work: ['XXSC', 'XXMT'], employee_salary: ['XXSL'], employee_advance: ['XXHR']};
        const business_purpose = (matchingTags[business_route] || []).includes(x.category) ? x.category : business_route;
        const target = treatment === 'JOURNAL_ENTRY' ? {type: 'EXPENSE', treatment, account: value, employee: business_route.startsWith('employee_') ? employeeControl?.get_value() || '' : '', counterparty: counterpartyControl?.get_value() || x.suggested_counterparty?.name || '', supply_type, label: q('[data-label]')?.value || '', remember_default: remember, business_route, business_purpose} : {type: 'PARTY', treatment, party_type: partyTypeOf(x), party: value, counterparty: x.suggested_counterparty?.name || '', reference_doctype, reference_name: invoice || order, supply_type, remember_default: remember, business_route, business_purpose};
        if (!business_route) { q('[data-message]').textContent = __('Choose a purpose first.'); return; }
        const mode = this.hasAttribute('data-route-post') ? 'post' : 'draft';
        const run = async () => {
            try {
                const result = (await frappe.call({method: api + 'decide_business_route', type: 'POST', args: {name: x.name, modified: x.modified, target, mode}})).message;
                state.businessChanged.delete(x.name);
                await load();
                if (result.post_error) frappe.msgprint(__('Draft created. Posting failed: {0}', [esc(result.post_error)]));
                else frappe.show_alert({message: result.status === 'posted' ? __('Posted') : __('Draft created'), indicator: 'green'});
            } catch (e) { frappe.msgprint(__('Could not create the entry. Review the movement and try again.')); }
        };
        try {
            const preview = (await frappe.call({method: api + 'preview_route', type: 'POST', args: {name: x.name, target}})).message;
            target.reviewed_preview = preview;
            const fees = (preview.fees || []).map(row => `<p>${esc(row.family)} · ${__('Debit')} ${esc(row.debit || __('Account not configured'))} · ${__('Credit')} ${esc(row.credit)} · ${money(row.amount, preview.currency)}</p>`).join('');
            frappe.confirm(`<p>${__('Debit')} · ${esc(preview.debit)} · ${money(preview.amount, preview.currency)}</p><p>${__('Credit')} · ${esc(preview.credit)} · ${money(preview.amount, preview.currency)}</p>${fees}<p>${mode === 'post' ? __('Create and post?') : __('Create draft?')}</p>`, run);
        } catch (e) { frappe.msgprint(__('Could not review the proposed accounts. Check the selected party and account.')); }
    });
    root.on('click', '[data-new]', function () {
        const x = selected(), name = q('[data-new-name]').value.trim();
        if (name.length < 3) { q('[data-message]').textContent = __('Enter the full name.'); return; }
        act('route_movement', {target: {type: 'NEW_PARTY', treatment: q('[data-treatment]').value, party_type: partyTypeOf(x), counterparty: x.suggested_counterparty?.name || '', name, vat: q('[data-new-vat]').value, country: q('[data-new-country]')?.value || '', supply_type: q('[data-supply]')?.value || '', remember_default: q('[data-remember]')?.checked ? '1' : '0'}});
    });
    root.on('click', '[data-pick]', function () {
        const x = selected(), i = (q('input[name="pick"]:checked') || {}).value;
        if (i === undefined) { q('[data-message]').textContent = __('Choose a document.'); return; }
        const d = x.candidates.documents[Number(i)]; act('pick_document', {doctype: d.doctype, document: d.name});
    });
    root.on('click', '[data-unlink]', () => act('unlink_movement', {}));
    root.on('click', '[data-preview-entry]', async () => {
        const x = selected();
        try {
            const entry = (await frappe.call({method: api + 'preview_linked_document', args: {name: x.name}})).message;
            const rows = entry.lines.map(line => `<tr><td>${esc(line.account)}</td><td>${money(line.debit, line.currency)}</td><td>${money(line.credit, line.currency)}</td></tr>`).join('');
            const options = {title: __('Entry preview'), message: `<p>${esc(entry.doctype)} · ${esc(entry.document)} · ${esc(docStatus(entry.docstatus))}</p><table class="table"><thead><tr><th>${__('Account')}</th><th>${__('Debit')}</th><th>${__('Credit')}</th></tr></thead><tbody>${rows}</tbody></table>`};
            if (entry.can_submit) options.primary_action = {label: __('Post'), action: () => frappe.confirm(__('Post this reviewed entry and its related fee journal?'), async () => {
                try {
                    await frappe.call({method: api + 'post_reviewed_draft', type: 'POST', args: {name: x.name, modified: entry.movement_modified, reviewed_document: entry.document, reviewed_modified: entry.modified}});
                    await load(); frappe.show_alert({message: __('Posted'), indicator: 'green'});
                } catch (e) { frappe.msgprint(__('The entry could not be posted. Refresh and review it again.')); }
            })};
            frappe.msgprint(options);
        } catch (e) { frappe.msgprint(__('Could not read this entry or its linked accounts.')); }
    });
    root.on('click', '[data-clear-missing]', () => act('clear_missing_document', {}));
    load();
};
