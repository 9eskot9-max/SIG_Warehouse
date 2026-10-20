// Read-only status workbench. Data and authorization remain owned by pc_journal.
frappe.pages['pc-transaction-status'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: '', single_column: true});
    $(wrapper).find('.page-head').hide();
    const roles = ['System Manager', 'Accounts User', 'Accounts Manager', 'Operations User', 'Operations Manager', 'SIG PC Clearance'];
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-pc-status"></main>').attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr').attr('lang', language).appendTo(page.main);
    const el = root[0], q = (selector) => el.querySelector(selector);
    const esc = (value) => frappe.utils.escape_html(value == null ? '' : String(value));
    const money = (value) => (Number(value) || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : '—';
    const isPdf = (url) => /\.pdf(?:[?#]|$)/i.test(url) || /[?&]\w*=pdf(?:&|$)/i.test(url);
    const status = (row) => row.finance_status === 'Pending Review' ? __('Pending Manager') : __(row.finance_status || 'Unknown');
    const total = (rows) => rows.reduce((sum, row) => sum + (Number(row.amount) || 0), 0);
    const state = {rows: [], employees: new Map(), employee: '', selected: '', search: '', status: '', applied: {scope: 'all'}, request: 0, loading: false};
    const view = {s: 1, x: 0, y: 0, r: 0, mode: 'page'};

    root.html('<header class="sig-pc-status-head">' +
        '<div><div class="sig-pc-status-eyebrow">' + __('Accounts') + '</div><h1>' + __('Petty Cash Status') + '</h1><p data-subtitle>' + __('Review approval and accounting status') + '</p></div>' +
        '<div class="sig-pc-status-actions"><button class="btn btn-default" data-review>' + __('Open PC Review') + '</button><button class="btn btn-default" data-refresh>' + __('Refresh') + '</button><button class="btn btn-primary" data-print disabled>' + __('Print report') + '</button></div></header>' +
        '<section class="sig-pc-status-stats" aria-label="' + __('Transaction totals') + '"></section>' +
        '<section class="sig-pc-status-context" aria-live="polite"></section>' +
        '<section class="sig-pc-status-workarea"><aside class="sig-pc-status-queue" aria-label="' + __('Employee transactions') + '">' +
        '<label class="sr-only" for="pc-status-employee">' + __('Employee') + '</label><select id="pc-status-employee" data-employee><option value="">' + __('Loading employees…') + '</option></select>' +
        '<input type="search" data-search placeholder="' + __('Search receipts…') + '" aria-label="' + __('Search receipts') + '">' +
        '<select data-status aria-label="' + __('Transaction status') + '"><option value="">' + __('All statuses') + '</option></select>' +
        '<div class="sig-pc-status-queue-summary"></div><div class="sig-pc-status-queue-list" role="listbox" aria-label="' + __('Transactions') + '"></div></aside>' +
        '<article class="sig-pc-status-selected" aria-label="' + __('Selected transaction') + '"><div class="sig-pc-status-empty">' + __('Loading transactions…') + '</div></article></section>' +
        '<section class="sig-pc-status-report-section"><h2>' + __('Transaction register') + '</h2><p>' + __('Select a period for this employee. Select a row to inspect its receipt above.') + '</p>' +
        '<section class="sig-pc-status-filters"><label>' + __('Transactions') + '<select data-scope><option value="all">' + __('All transactions') + '</option><option value="cycle">' + __('Cycle') + '</option><option value="range">' + __('Date range') + '</option></select></label>' +
        '<label data-from-wrap hidden>' + __('From') + '<input type="date" data-from></label><label data-to-wrap hidden>' + __('To') + '<input type="date" data-to></label><button class="btn btn-default" data-apply>' + __('Apply') + '</button></section>' +
        '<div class="sig-pc-status-cycle-note" data-cycle-note hidden>' + __('Cycle selection will be available when employee payments/advances are connected. Each payment to the employee will start a new cycle.') + '</div>' +
        '<div class="sig-pc-status-message" role="status" hidden></div><section class="sig-pc-printdoc"></section></section>');

    function employeeRows() { return state.rows.filter((row) => row.employee_key === state.employee); }
    function visibleRows() {
        const term = state.search.toLowerCase();
        return employeeRows().filter((row) => (!state.status || row.finance_status === state.status) &&
            (!term || [row.transaction_category, row.transaction_date, row.amount, row.reviewed_by, status(row)].join(' ').toLowerCase().includes(term)));
    }
    function badge(value) {
        const key = String(value || '').toLowerCase();
        const cls = key.includes('posted') || key === 'submitted' ? 'is-ok' : /reject|cancel|mismatch|no linked/.test(key) ? 'is-bad' : 'is-pending';
        return '<span class="sig-pc-status-badge ' + cls + '">' + esc(value || '—') + '</span>';
    }
    function message(text) { q('.sig-pc-status-message').hidden = !text; q('.sig-pc-status-message').textContent = text || ''; }
    function updateScopeControls() {
        const scope = q('[data-scope]').value;
        q('[data-from-wrap]').hidden = scope !== 'range';
        q('[data-to-wrap]').hidden = scope !== 'range';
        q('[data-cycle-note]').hidden = scope !== 'cycle';
        q('[data-apply]').disabled = scope === 'cycle' || state.loading;
        q('[data-employee]').disabled = scope === 'cycle' || state.loading;
        q('[data-print]').disabled = scope === 'cycle' || state.loading || !visibleRows().length;
    }
    async function load() {
        if (q('[data-scope]').value === 'cycle') return;
        const scope = q('[data-scope]').value;
        const args = {};
        if (state.employee) args.employee = state.employee;
        if (scope === 'range') {
            args.from_date = q('[data-from]').value || null;
            args.to_date = q('[data-to]').value || null;
            if (!args.from_date || !args.to_date || args.from_date > args.to_date) {
                message(__('Choose a valid start and end date.')); return;
            }
        }
        const request = ++state.request;
        state.loading = true; message(__('Loading transactions…')); updateScopeControls();
        q('[data-employee]').disabled = true;
        q('.sig-pc-status-selected').setAttribute('aria-busy', 'true');
        try {
            const rows = await frappe.call({method: 'sig_warehouse.sig_warehouse.pc_journal.transaction_status_report', type: 'POST', args}).then((response) => response.message || []);
            if (request !== state.request) return;
            rows.forEach((row) => { if (row.employee_key) state.employees.set(row.employee_key, row.employee_name); });
            state.rows = rows;
            if (!state.employee) state.employee = [...state.employees.keys()][0] || '';
            state.applied = {scope, from: args.from_date, to: args.to_date};
            state.selected = ''; state.search = ''; state.status = '';
            q('[data-search]').value = '';
            q('[data-employee]').innerHTML = [...state.employees].sort((a, b) => String(a[1]).localeCompare(String(b[1])))
                .map(([key, name]) => '<option value="' + esc(key) + '">' + esc(name) + '</option>').join('') || '<option value="">' + __('No assigned employees') + '</option>';
            q('[data-employee]').value = state.employee;
            q('[data-status]').innerHTML = '<option value="">' + __('All statuses') + '</option>' +
                [...new Set(employeeRows().map((row) => row.finance_status))].sort().map((value) => '<option value="' + esc(value) + '">' + esc(status({finance_status: value})) + '</option>').join('');
            message(''); render();
        } catch (error) {
            if (request !== state.request) return;
            state.rows = [];
            render();
            message(error.message || __('Unable to load petty-cash status.'));
        } finally {
            if (request === state.request) {
                state.loading = false; q('[data-employee]').disabled = false;
                q('.sig-pc-status-selected').removeAttribute('aria-busy'); updateScopeControls();
            }
        }
    }
    function render() {
        const rows = visibleRows(), all = employeeRows();
        if (!rows.some((row) => row.name === state.selected)) state.selected = rows[0]?.name || '';
        q('[data-subtitle]').textContent = (state.employees.get(state.employee) || __('No assigned employees')) + ' · ' + __('{0} transactions', [all.length]) + ' · ' + money(total(all)) + ' SAR';
        q('.sig-pc-status-stats').innerHTML = ['Pending Review', 'Pending Finance', 'Posted', 'Rejected'].map((value) =>
            '<div class="sig-pc-status-stat"><strong>' + all.filter((row) => row.finance_status === value).length + '</strong><span>' + esc(status({finance_status: value})) + '</span></div>').join('');
        q('.sig-pc-status-queue-summary').textContent = __('{0} transactions', [rows.length]) + ' · ' + money(total(rows)) + ' SAR';
        let lastDate = '';
        q('.sig-pc-status-queue-list').innerHTML = rows.map((row) => {
            const day = row.transaction_date;
            const heading = day !== lastDate ? '<div class="sig-pc-status-day">' + esc(date(day)) + '</div>' : '';
            lastDate = day;
            return heading + '<button type="button" role="option" aria-selected="' + (row.name === state.selected) + '" data-select="' + esc(row.name) + '" class="sig-pc-status-queue-item">' +
                '<strong>' + esc(money(row.amount)) + '</strong><span>' + esc(row.transaction_category || '—') + '</span>' + badge(status(row)) + '</button>';
        }).join('') || '<div class="sig-pc-status-empty">' + __('No matching transactions.') + '</div>';
        renderDocument(rows); renderSelected(); updateScopeControls();
    }
    function detail(row) {
        return '<dl>' + [
            [__('Date'), esc(date(row.transaction_date))],
            [__('Amount (incl. VAT)'), '<strong class="sig-pc-status-gross">' + esc(money(row.amount)) + ' <small>SAR</small></strong>'],
            [__('Category'), esc(row.transaction_category || '—')],
            [__('Status'), badge(status(row))],
            [__('Approved by'), esc(row.reviewed_by || '—')],
            [__('Reviewed on'), esc(date(row.reviewed_at))],
            [__('Journal Entry status'), esc(row.journal_status || '—')],
            [__('PC review delegation'), esc(row.review_group || __('Unassigned')) + (row.review_group_lead ? '<small>' + __('Lead') + ': ' + esc(row.review_group_lead) + '</small>' : '')],
        ].map(([label, value]) => '<div><dt>' + label + '</dt><dd>' + value + '</dd></div>').join('') + '</dl>';
    }
    function viewer(url) {
        if (!url) return '<div class="sig-pc-status-no-receipt">' + __('No receipt is attached to this transaction.') + '</div>';
        if (isPdf(url)) return '<iframe class="sig-pc-status-pdf" src="' + esc(url) + '" title="' + __('Invoice PDF') + '"></iframe>';
        return '<div class="sig-pc-status-viewer"><div class="sig-pc-status-vtools">' +
            '<button type="button" data-z="out" aria-label="' + __('Zoom out') + '">−</button><span class="sig-pc-status-zoomlabel">' + __('Fit page') + '</span><button type="button" data-z="in" aria-label="' + __('Zoom in') + '">+</button>' +
            '<button type="button" data-z="mode" class="sig-pc-status-mode">' + __('Fit width') + '</button><button type="button" data-z="actual">100%</button><button type="button" data-z="rot">' + __('Rotate') + '</button>' +
            '<span class="sig-pc-status-vhint">' + __('Ctrl+wheel to zoom · drag to move') + '</span></div><div class="sig-pc-status-vstage"><img src="' + esc(url) + '" alt="' + __('Invoice receipt') + '" draggable="false"></div></div>';
    }
    function renderSelected() {
        const rows = visibleRows(), index = rows.findIndex((row) => row.name === state.selected), row = rows[index];
        q('.sig-pc-status-context').innerHTML = '<div><strong>' + esc(state.employees.get(state.employee) || '—') + '</strong> <span>' +
            (row ? __('Transaction {0} of {1}', [index + 1, rows.length]) + ' · ' + date(row.transaction_date) : __('No transaction selected')) + '</span></div>' +
            '<div><button class="btn btn-default btn-sm" data-prev ' + (index <= 0 ? 'disabled' : '') + '>' + __('← Previous') + '</button> <button class="btn btn-default btn-sm" data-next ' + (index < 0 || index === rows.length - 1 ? 'disabled' : '') + '>' + __('Next →') + '</button></div>';
        q('.sig-pc-status-selected').innerHTML = row ? '<div class="sig-pc-status-photo">' + viewer(row.source_media_url) + '</div>' +
            '<div class="sig-pc-status-side"><h3>' + __('Transaction status') + '</h3>' + detail(row) +
            (row.source_media_url ? '<a href="' + esc(row.source_media_url) + '" target="_blank" rel="noopener">' + __('Open original receipt') + '</a>' : '') + '</div>' :
            '<div class="sig-pc-status-empty">' + __('No transactions match this selection.') + '</div>';
        Object.assign(view, {s: 1, x: 0, y: 0, r: 0, mode: 'page'});
        wireViewer(q('.sig-pc-status-selected'));
        el.querySelectorAll('[data-select]').forEach((button) => button.setAttribute('aria-selected', String(button.dataset.select === state.selected)));
        el.querySelectorAll('[data-row]').forEach((tr) => tr.classList.toggle('is-selected', tr.dataset.row === state.selected));
    }
    function select(name, scroll) {
        state.selected = name; renderSelected();
        if (scroll) q('.sig-pc-status-context').scrollIntoView({behavior: 'smooth', block: 'start'});
    }
    function step(delta) {
        const rows = visibleRows(), index = rows.findIndex((row) => row.name === state.selected);
        const row = rows[Math.max(0, Math.min(rows.length - 1, index + delta))];
        if (row) select(row.name, false);
    }
    function renderDocument(rows) {
        const period = state.applied.scope === 'range' ? date(state.applied.from) + ' — ' + date(state.applied.to) : __('All dates');
        q('.sig-pc-printdoc').innerHTML = '<div class="sig-pc-status-brand"><div class="sig-pc-status-brand-mark">SIG</div><div><strong>SIG</strong><span>' + __('Petty Cash') + '</span></div><div class="sig-pc-status-document-title"><h2>' + __('Petty Cash Transaction Status') + '</h2></div></div>' +
            '<div class="sig-pc-status-meta"><div><small>' + __('Employee') + '</small><strong>' + esc(state.employees.get(state.employee) || '—') + '</strong></div><div><small>' + __('Period') + '</small><strong>' + esc(period) + '</strong></div><div><small>' + __('Generated') + '</small><strong>' + esc(date(frappe.datetime.get_today())) + '</strong></div></div>' +
            '<p class="sig-pc-status-selection-note">' + esc([state.status ? status({finance_status: state.status}) : __('All statuses'), state.search ? __('Search: {0}', [state.search]) : ''].filter(Boolean).join(' · ')) + '</p>' +
            '<div class="sig-pc-status-table-wrap"><table class="sig-pc-status-table"><thead><tr><th>#</th><th>' + __('Date') + '</th><th>' + __('Category') + '</th><th>' + __('Amount (incl. VAT)') + '</th><th>' + __('Status') + '</th><th>' + __('Approved by') + '</th><th>' + __('Journal Entry status') + '</th><th class="sig-pc-status-screen-only">' + __('Receipt') + '</th></tr></thead><tbody>' +
            (rows.map((row, index) => '<tr data-row="' + esc(row.name) + '"><td>' + (index + 1) + '</td><td>' + esc(date(row.transaction_date)) + '</td><td>' + esc(row.transaction_category || '—') + '</td><td class="sig-pc-status-money">' + esc(money(row.amount)) + '</td><td>' + badge(status(row)) + '</td><td>' + esc(row.reviewed_by || '—') + '</td><td>' + esc(row.journal_status || '—') + '</td><td class="sig-pc-status-screen-only"><button data-select="' + esc(row.name) + '" data-jump class="sig-pc-status-view-receipt">' + __('View') + '</button></td></tr>').join('') ||
            '<tr><td colspan="8" class="sig-pc-status-empty">' + __('No transactions match this selection.') + '</td></tr>') +
            '</tbody><tfoot><tr><th colspan="3">' + __('Total (SAR)') + '</th><th class="sig-pc-status-money">' + esc(money(total(rows))) + '</th><td colspan="3">' + __('{0} transactions', [rows.length]) + '</td><td class="sig-pc-status-screen-only"></td></tr></tfoot></table></div><section class="sig-pc-status-receipts"></section>' +
            '<footer class="sig-pc-status-foot">' + __('Draft Journal Entries are pending Finance review; Submitted means posted.') + '</footer>';
    }

    // Same image inspection behavior as PC Review, scoped to this read-only workbench.
    const vstage = () => q('.sig-pc-status-vstage');
    const vimg = () => q('.sig-pc-status-vstage img');
    function dims() {
        const st = vstage(), img = vimg();
        if (!st || !img || !img.naturalWidth) return null;
        const rot = view.r % 180 !== 0, nw = rot ? img.naturalHeight : img.naturalWidth, nh = rot ? img.naturalWidth : img.naturalHeight;
        const cw = st.clientWidth, ch = st.clientHeight;
        return {cw, ch, nw, nh, contain: Math.min(cw / nw, ch / nh), wide: cw / nw};
    }
    const baseScale = (d) => view.mode === 'width' ? d.wide : d.contain;
    function layout(reset) {
        const d = dims(), img = vimg(); if (!d) return;
        if (!view.mode) view.mode = 'page';
        const b = baseScale(d);
        img.style.width = (img.naturalWidth * b) + 'px';
        img.style.height = (img.naturalHeight * b) + 'px';
        if (reset) { view.s = 1; view.x = 0; view.y = view.mode === 'width' ? Math.max(0, (d.nh * b - d.ch) / 2) : 0; }
        applyView();
    }
    function applyView() {
        const d = dims(), img = vimg(); if (!d || !img) return;
        const b = baseScale(d), W = d.nw * b * view.s, H = d.nh * b * view.s;
        const mx = Math.max(0, (W - d.cw) / 2) + d.cw * 0.3, my = Math.max(0, (H - d.ch) / 2) + d.ch * 0.3;
        view.x = Math.max(-mx, Math.min(mx, view.x)); view.y = Math.max(-my, Math.min(my, view.y));
        img.style.transform = `translate(${view.x}px,${view.y}px) rotate(${view.r}deg) scale(${view.s})`;
        const zl = q('.sig-pc-status-zoomlabel'); if (zl) zl.textContent = view.s === 1 ? (view.mode === 'width' ? __('Fit width') : __('Fit page')) : Math.round(b * view.s * 100) + '%';
        const mb = q('.sig-pc-status-mode'); if (mb) mb.textContent = view.mode === 'width' ? __('Fit page') : __('Fit width');
    }
    function zoomAt(factor, px, py) {
        const st = vstage(), d = dims(); if (!st || !d) return;
        const r = st.getBoundingClientRect(), cx = px - (r.left + r.width / 2), cy = py - (r.top + r.height / 2);
        let ns = Math.max(0.3, Math.min(16, view.s * factor)), k = ns / view.s;
        if (Math.abs(ns - 1) < 0.03) { ns = 1; k = ns / view.s; }
        view.x = cx - (cx - view.x) * k; view.y = cy - (cy - view.y) * k; view.s = ns;
        applyView();
    }
    function zoomCenter(f) { const r = vstage().getBoundingClientRect(); zoomAt(f, r.left + r.width / 2, r.top + r.height / 2); }
    const toggleMode = () => { view.mode = view.mode === 'width' ? 'page' : 'width'; layout(true); };
    const rotate = () => { view.r = (view.r + 90) % 360; view.mode = null; layout(true); };
    function actualSize() { const d = dims(); if (!d) return; view.s = Math.min(16, 1 / baseScale(d)); view.x = 0; view.y = 0; applyView(); }

    function wireViewer(c) {
        const stage = vstage(), img = vimg();
        if (!stage) return;
        if (img.complete && img.naturalWidth) layout(true); else img.addEventListener('load', () => layout(true));
        stage.addEventListener('wheel', (e) => {
            e.preventDefault();
            if (e.ctrlKey) zoomAt(Math.pow(1.0015, -e.deltaY), e.clientX, e.clientY);
            else { view.x -= e.deltaX; view.y -= e.deltaY; applyView(); }
        }, {passive: false});
        stage.addEventListener('dblclick', (e) => { if (view.s === 1) zoomAt(2.5, e.clientX, e.clientY); else layout(true); });
        let drag = null;
        stage.addEventListener('pointerdown', (e) => { drag = {x: e.clientX - view.x, y: e.clientY - view.y}; stage.classList.add('dragging'); stage.setPointerCapture(e.pointerId); });
        stage.addEventListener('pointermove', (e) => { if (!drag) return; view.x = e.clientX - drag.x; view.y = e.clientY - drag.y; applyView(); });
        const end = () => { drag = null; stage.classList.remove('dragging'); };
        stage.addEventListener('pointerup', end); stage.addEventListener('pointercancel', end);
        c.querySelector('.sig-pc-status-vtools').addEventListener('click', (e) => {
            const b = e.target.closest('[data-z]'); if (!b) return;
            const a = b.dataset.z;
            if (a === 'in') zoomCenter(1.3); else if (a === 'out') zoomCenter(1 / 1.3);
            else if (a === 'mode') toggleMode(); else if (a === 'actual') actualSize(); else if (a === 'rot') rotate();
        });
        img.addEventListener('error', () => { const v = q('.sig-pc-status-viewer'); if (v) v.outerHTML = `<div class="sig-pc-status-no-receipt">${__('Receipt preview unavailable — use Open receipt')}</div>`; });
    }

    let resizeTimer;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (vstage()) layout(true); }, 120); });

    q('[data-scope]').addEventListener('change', updateScopeControls);
    q('[data-apply]').addEventListener('click', load);
    q('[data-refresh]').addEventListener('click', load);
    q('[data-employee]').addEventListener('change', (event) => { state.employee = event.target.value; load(); });
    q('[data-search]').addEventListener('input', (event) => { state.search = event.target.value; render(); });
    q('[data-status]').addEventListener('change', (event) => { state.status = event.target.value; render(); });
    q('[data-review]').addEventListener('click', () => frappe.set_route('pc-invoice-review'));
    el.addEventListener('click', (event) => {
        const button = event.target.closest('[data-select], [data-prev], [data-next]');
        if (state.loading) return;
        if (!button) {
            const row = event.target.closest('[data-row]');
            if (row) select(row.dataset.row, true);
            return;
        }
        if (button.disabled) return;
        if (button.hasAttribute('data-prev')) step(-1);
        else if (button.hasAttribute('data-next')) step(1);
        else select(button.dataset.select, button.hasAttribute('data-jump'));
    });
    document.addEventListener('keydown', (event) => {
        if (frappe.get_route()[0] !== 'pc-transaction-status' || state.loading ||
            /INPUT|SELECT|TEXTAREA/.test(event.target.tagName) || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'ArrowLeft') { event.preventDefault(); step(-1); }
        if (event.key === 'ArrowRight') { event.preventDefault(); step(1); }
    });
    // Keep hundreds of off-screen receipt previews out of the interactive Desk DOM.
    // Build the sequential print appendix only when Print report is requested.
    function preparePrint(rows) {
        q('.sig-pc-status-receipts').innerHTML = rows.map((row, index) => {
            const file = String(row.source_media_url || '');
            const media = !file ? '<div class="sig-pc-status-no-receipt">' + __('No receipt attached.') + '</div>' :
                isPdf(file) ? '<iframe class="sig-pc-status-receipt-pdf" src="' + esc(file) + '" title="' + __('Receipt {0}', [index + 1]) + '"></iframe>' :
                '<img class="sig-pc-status-receipt-image" src="' + esc(file) + '" alt="' + __('Receipt {0}', [index + 1]) + '">';
            return '<article class="sig-pc-status-receipt"><div class="sig-pc-status-receipt-info"><div class="sig-pc-status-receipt-count">' + __('Transaction {0} of {1}', [index + 1, rows.length]) + '</div><h3>' + esc(row.employee_name) + '</h3>' + detail(row) + '</div><div class="sig-pc-status-receipt-media">' + media + '</div></article>';
        }).join('');
        return Promise.all([...q('.sig-pc-status-receipts').querySelectorAll('img,iframe')].map((item) => new Promise((resolve) => {
            if (item.tagName === 'IMG' && item.complete) {
                if (!item.naturalWidth) unavailable(item);
                resolve(); return;
            }
            const timer = setTimeout(() => { unavailable(item); resolve(); }, 30000);
            item.addEventListener('load', () => { clearTimeout(timer); resolve(); }, {once: true});
            item.addEventListener('error', () => { clearTimeout(timer); unavailable(item); resolve(); }, {once: true});
        })));
    }
    function unavailable(item) {
        const note = document.createElement('div');
        note.className = 'sig-pc-status-no-receipt';
        note.textContent = __('Receipt preview unavailable. Check the original receipt before issuing this report.');
        item.replaceWith(note);
    }
    q('[data-print]').addEventListener('click', async () => {
        const button = q('[data-print]'), rows = visibleRows();
        if (state.loading || !rows.length) return;
        button.disabled = true; button.textContent = __('Preparing receipts…');
        // Prevent the print selection changing while its media loads.
        const controls = [...el.querySelectorAll('input,select,button')];
        const disabled = controls.map((control) => control.disabled);
        controls.forEach((control) => { control.disabled = true; });
        try { await preparePrint(rows); window.print(); }
        finally {
            controls.forEach((control, index) => { control.disabled = disabled[index]; });
            button.textContent = __('Print report'); updateScopeControls();
        }
    });
    window.addEventListener('afterprint', () => { const appendix = q('.sig-pc-status-receipts'); if (appendix) appendix.innerHTML = ''; });
    if (!roles.some((role) => frappe.user.has_role(role)) || !frappe.model.can_read('SIG PC Transaction')) {
        q('.sig-pc-status-selected').innerHTML = '<div class="sig-pc-status-empty">' + __('Your ERP role cannot view petty-cash transactions.') + '</div>';
    } else load();
};
