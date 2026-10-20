// Read-only petty-cash transaction status report. Its data is scoped by the same
// SIG PC Transaction permission hooks as the review workbench; linked JE docstatus
// is returned only for the matching transaction origin link.
frappe.pages['pc-transaction-status'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: '', single_column: true});
    $(wrapper).find('.page-head').hide();
    const roles = ['System Manager', 'Accounts User', 'Accounts Manager', 'Operations User', 'Operations Manager', 'SIG PC Clearance'];
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-pc-status"></main>').attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr').attr('lang', language).appendTo(page.main);
    const el = root[0];
    const q = (selector) => el.querySelector(selector);
    const esc = (value) => frappe.utils.escape_html(value == null ? '' : String(value));
    const money = (value) => (Number(value) || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : '—';
    const state = {rows: [], employee: '', scope: 'all'};

    root.html(`<header class="sig-pc-status-head">
        <div><div class="sig-pc-status-eyebrow">${__('Accounts')}</div><h1>${__('Petty Cash Status')}</h1>
        <p>${__('Transaction review and linked Journal Entry status')}</p></div>
        <div class="sig-pc-status-actions"><button class="btn btn-default" data-refresh>${__('Refresh')}</button>
        <button class="btn btn-primary" data-print>${__('Print report')}</button></div>
    </header>
    <section class="sig-pc-status-filters">
        <label>${__('Transactions')}<select data-scope><option value="all">${__('All transactions')}</option>
            <option value="cycle">${__('Cycle — waiting for ERP employee advance records')}</option>
            <option value="range">${__('Date range')}</option></select></label>
        <label>${__('Employee')}<select data-employee><option value="">${__('All assigned employees')}</option></select></label>
        <label data-from-wrap hidden>${__('From')}<input type="date" data-from></label>
        <label data-to-wrap hidden>${__('To')}<input type="date" data-to></label>
        <button class="btn btn-default" data-apply>${__('Apply')}</button>
    </section>
    <div class="sig-pc-status-cycle-note" data-cycle-note hidden>${__('A cycle must start from a recorded payment or advance to the employee. That funding source is not yet connected to ERP, so this selector will become active when those source records are available.')}</div>
    <section class="sig-pc-printdoc" aria-live="polite"><div class="sig-pc-status-empty">${__('Loading transactions…')}</div></section>`);

    function selectedScope() {
        const scope = q('[data-scope]').value;
        const args = {employee: q('[data-employee]').value || null};
        if (scope === 'range') {
            args.from_date = q('[data-from]').value || null;
            args.to_date = q('[data-to]').value || null;
        }
        return args;
    }
    function updateScopeControls() {
        const range = q('[data-scope]').value === 'range';
        const cycle = q('[data-scope]').value === 'cycle';
        q('[data-from-wrap]').hidden = !range;
        q('[data-to-wrap]').hidden = !range;
        q('[data-cycle-note]').hidden = !cycle;
        q('[data-apply]').disabled = cycle;
        if (cycle) q('.sig-pc-printdoc').innerHTML = `<div class="sig-pc-status-empty">${__('Cycle data is unavailable until ERP has employee advance/payment records.')}</div>`;
    }
    async function load() {
        if (q('[data-scope]').value === 'cycle') return;
        const doc = q('.sig-pc-printdoc');
        doc.innerHTML = `<div class="sig-pc-status-empty">${__('Loading transactions…')}</div>`;
        try {
            state.rows = await frappe.call({
                method: 'sig_warehouse.sig_warehouse.pc_journal.transaction_status_report',
                type: 'POST', args: selectedScope(),
            }).then((response) => response.message || []);
            populateEmployees();
            render();
        } catch (error) {
            doc.innerHTML = `<div class="sig-pc-status-empty">${esc(error.message || __('Unable to load petty-cash status.'))}</div>`;
        }
    }
    function populateEmployees() {
        const select = q('[data-employee]');
        const keep = select.value;
        const employees = [...new Map(state.rows.filter((row) => row.employee_key).map((row) => [row.employee_key, row.employee_name])).entries()]
            .sort((a, b) => String(a[1]).localeCompare(String(b[1])));
        select.innerHTML = `<option value="">${__('All assigned employees')}</option>` + employees.map(([key, name]) => `<option value="${esc(key)}">${esc(name)}</option>`).join('');
        if (employees.some(([key]) => key === keep)) select.value = keep;
    }
    function badge(value) {
        const key = String(value || '').toLowerCase();
        const cls = key.includes('posted') || key === 'submitted' ? 'is-ok' : key.includes('reject') || key.includes('cancel') || key.includes('mismatch') ? 'is-bad' : 'is-pending';
        return `<span class="sig-pc-status-badge ${cls}">${esc(value || '—')}</span>`;
    }
    function render() {
        const rows = state.rows;
        const total = rows.reduce((sum, row) => sum + (Number(row.amount) || 0), 0);
        const employee = q('[data-employee]').value;
        const period = q('[data-scope]').value === 'range' ? `${date(q('[data-from]').value)} — ${date(q('[data-to]').value)}` : __('All dates');
        const generated = frappe.datetime.str_to_user(frappe.datetime.get_today());
        const body = rows.length ? rows.map((row, index) => `<tr>
            <td class="sig-pc-status-num">${index + 1}</td><td>${esc(date(row.transaction_date))}</td>
            <td>${esc(row.employee_name || '—')}</td><td><strong>${esc(row.review_group || __('Unassigned'))}</strong>${row.review_group_lead ? `<small class="sig-pc-status-group-lead">${__('Lead')}: ${esc(row.review_group_lead)}</small>` : ''}</td>
            <td>${esc(row.transaction_category || '—')}</td>
            <td class="sig-pc-status-money">${esc(money(row.amount))}</td><td>${badge(row.finance_status)}</td>
            <td>${esc(row.reviewed_by || '—')}</td><td>${esc(row.journal_status || '—')}</td>
        </tr>`).join('') : `<tr><td colspan="9" class="sig-pc-status-empty">${__('No transactions match this selection.')}</td></tr>`;
        q('.sig-pc-printdoc').innerHTML = `<div class="sig-pc-status-brand"><div class="sig-pc-status-brand-mark">SIG</div><div><strong>${__('SIG')}</strong><span>${__('Petty Cash')}</span></div><div class="sig-pc-status-document-title"><h2>${__('Petty Cash Transaction Status')}</h2><p>${__('Review approval and accounting status')}</p></div></div>
            <div class="sig-pc-status-meta"><div><small>${__('Employee')}</small><strong>${esc(employee || __('All assigned employees'))}</strong></div>
            <div><small>${__('Period')}</small><strong>${esc(period)}</strong></div><div><small>${__('Generated')}</small><strong>${esc(generated)}</strong></div></div>
            <table class="sig-pc-status-table"><thead><tr><th>#</th><th>${__('Date')}</th><th>${__('Employee')}</th><th>${__('PC review delegation')}</th><th>${__('Category')}</th><th>${__('Amount (SAR)')}</th><th>${__('Status')}</th><th>${__('Approved by')}</th><th>${__('Journal Entry status')}</th></tr></thead>
            <tbody>${body}</tbody><tfoot><tr><th colspan="5">${__('Total')}</th><th class="sig-pc-status-money">${esc(money(total))}</th><td colspan="3">${__('{0} transactions', [rows.length])}</td></tr></tfoot></table>
            <footer class="sig-pc-status-foot"><span>${__('Journal Entry status is read from the linked Journal Entry. Draft means pending Finance review; Submitted means posted.')}</span><span>${__('Page generated from ERPNext')}</span></footer>`;
    }

    q('[data-scope]').addEventListener('change', updateScopeControls);
    q('[data-apply]').addEventListener('click', load);
    q('[data-refresh]').addEventListener('click', load);
    q('[data-print]').addEventListener('click', () => window.print());
    q('[data-employee]').addEventListener('change', load);
    if (!roles.some((role) => frappe.user.has_role(role)) || !frappe.model.can_read('SIG PC Transaction')) {
        q('.sig-pc-printdoc').innerHTML = `<div class="sig-pc-status-empty">${__('Your ERP role cannot view petty-cash transactions.')}</div>`;
    } else {
        load();
    }
};
