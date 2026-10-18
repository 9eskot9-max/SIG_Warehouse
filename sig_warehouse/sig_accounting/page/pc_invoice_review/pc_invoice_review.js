// Petty Cash - the main petty cash page (app-owned Desk Page; replaces the website Web Page and the SIG Petty Cash workspace).
// Runs inside the Desk shell, so the SIG logo/navbar, session, CSRF and permissions are native.
// Data: SIG PC Transaction + a role-gated resolver over Employee Mobile and linked Contact phones (pc_sender.py).
// Actions are the sig_pc_* Server Scripts.
// Navigation only links to ERPNext records; ERPNext permissions stay authoritative.
frappe.pages['pc-invoice-review'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: '', single_column: true});
    // Keep the Desk shell but remove its duplicate page heading; the workbench has its own header.
    $(wrapper).find('.page-head').hide();
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-pc-home"></main>').attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr').attr('lang', language).appendTo(page.main);
    const el = root[0];
    const q = (sel) => el.querySelector(sel);

    const CATEGORIES = ['Fuel/Disel', 'Hotel Rent', 'Food expenses', 'Equipment Rental', 'Car Maintanence', 'Construction/Operational Material', 'Vehicle OIL change', 'Vehicle Other Misc.', 'Drinking water', 'Medical expenses', 'Phone bill', 'Trailer Rent', 'Dyna Rent', 'Work Labor', 'Car Spare Parts', 'Others', 'Air-Ticket', 'Bus Ticket', 'Fax', 'Iqama fees', 'Office rental', 'Stationaries', 'Taxi', 'Train ticket', 'VISA fees', 'Xerox Copy', 'Fork Lift Rent', 'Pickup Rent', 'Office - Housekeeping', 'Warehouse misc.'];
    const FIELDS = ['name', 'employee_name', 'transaction_date', 'amount', 'purpose', 'transaction_category', 'has_vat', 'vat_amount', 'supplier_vat_number', 'merchant', 'invoice_number', 'details', 'source_id', 'source_media_url', 'source_row_url'];
    const VAT_RATE = 0.15;
    const REVIEWERS = ['System Manager', 'Accounts User', 'Accounts Manager', 'Operations User', 'Operations Manager', 'SIG PC Clearance'];
    const FINANCE = ['System Manager', 'Accounts User', 'Accounts Manager', 'SIG Finance Viewer'];
    const ALL = '__all__';

    const S = {rows: [], senders: {}, filter: 'all', person: null, index: 0, search: '', busy: false, loadedAt: 0};
    let view = {s: 1, x: 0, y: 0, r: 0, mode: null};

    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const isPhone = (v) => {
        const raw = String(v || '').trim();
        const digits = raw.replace(/\D/g, '');
        return /^[+()\d\s.-]+$/.test(raw) && digits.length >= 9 && digits.length <= 15;
    };
    const phoneKey = (v) => {
        let digits = String(v || '').replace(/\D/g, '');
        if (digits.startsWith('00')) digits = digits.slice(2);
        if (digits.length === 10 && digits.startsWith('05')) digits = '966' + digits.slice(1);
        else if (digits.length === 9 && digits.startsWith('5')) digits = '966' + digits;
        return digits;
    };
    const isPdf = (v) => /\.pdf(?:[?#]|$)/i.test(String(v || '')) || /[?&]\w*=pdf(?:&|$)/i.test(String(v || ''));
    const money = (n) => (Math.round((Number(n) || 0) * 100) / 100).toFixed(2);
    const number = (n) => new Intl.NumberFormat(language.replace('_', '-'), {maximumFractionDigits: 0}).format(n);
    const fmtDate = (d) => !d ? '—' : (frappe.datetime && frappe.datetime.str_to_user ? frappe.datetime.str_to_user(String(d).slice(0, 10)) : String(d).slice(0, 10));
    // A receipt's category is the saved one, or the suggestion carried by the receipt source (`purpose`).
    const catOf = (x) => x.transaction_category || (CATEGORIES.includes(x.purpose) ? x.purpose : '');
    const isSuggested = (x) => !x.transaction_category && !!catOf(x);
    const countText = (n) => (n === 1 ? __('1 receipt') : __('{0} receipts', [n]));
    const senderOf = (v) => (S.senders[phoneKey(v)] || {}).employee_name;
    const unmatchedSender = (x) => isPhone(x.employee_name) && !senderOf(x.employee_name);

    function label(v) {
        if (isPhone(v)) return senderOf(v) || (__('Unmatched sender') + ' · ' + v);
        return String(v || __('Unassigned sender'));
    }

    // ---- server calls -------------------------------------------------------------------------
    function plainText(html) { return (new DOMParser().parseFromString(String(html || ''), 'text/html').body.textContent || '').trim(); }

    // Frappe returns _server_messages as a JSON list of JSON strings; unwrap both layers.
    function serverMessages(body) {
        const out = [];
        try {
            if (body && body._server_messages) {
                JSON.parse(body._server_messages).forEach((m) => {
                    try { out.push(plainText(JSON.parse(m).message)); } catch (e) { out.push(plainText(m)); }
                });
            }
        } catch (e) { /* fall through */ }
        if (!out.length && body && body.exception) out.push(String(body.exception).replace(/^[\w.]+:\s*/, ''));
        return out.filter(Boolean);
    }
    function readError(xhr) {
        let body = xhr && xhr.responseJSON;
        if (!body) { try { body = JSON.parse(xhr.responseText); } catch (e) { body = {}; } }
        const msgs = serverMessages(body);
        return msgs.length ? msgs.join('\n') : __('The server rejected the request (HTTP {0}).', [xhr && xhr.status]);
    }
    // silent: we show one readable message ourselves instead of Frappe's popup.
    function call(method, args) {
        return new Promise((resolve, reject) => {
            frappe.call({method, args, type: 'POST', silent: true, callback: (r) => resolve(r.message), error: (xhr) => reject(new Error(readError(xhr)))});
        });
    }

    // ---- data ---------------------------------------------------------------------------------
    async function load() {
        setCount(__('Loading invoices…'));
        try {
            const tx = await call('frappe.client.get_list', {doctype: 'SIG PC Transaction', fields: JSON.stringify(FIELDS), filters: JSON.stringify([['closure_status', 'in', ['Draft', 'Needs Review']]]), order_by: 'employee_name asc, transaction_date asc', limit_page_length: 0});
            S.rows = tx || [];
            const senderPhones = [...new Set(S.rows.filter((x) => isPhone(x.employee_name)).map((x) => phoneKey(x.employee_name)))];
            S.senders = (await call('sig_warehouse.sig_warehouse.pc_sender.resolve_pc_employee_senders', {phone_numbers: JSON.stringify(senderPhones)})) || {};
            S.loadedAt = Date.now();
            prepare();
            render();
        } catch (e) {
            setCount(__('Petty cash unavailable'));
            q('.sig-pc-review').innerHTML = `<div class="sig-pc-empty">${esc(e.message || __('Could not load invoices.'))}</div>`;
        }
    }

    // Possible duplicates: the same receipt image, or the same sender + date + amount, among pending receipts.
    function prepare() {
        const byUrl = {}, byKey = {};
        S.rows.forEach((r) => {
            if (r.source_media_url) (byUrl[r.source_media_url] = byUrl[r.source_media_url] || []).push(r);
            const k = [r.employee_name, r.transaction_date, money(r.amount)].join('|');
            (byKey[k] = byKey[k] || []).push(r);
        });
        const ids = (list, me) => list.filter((o) => o !== me).map((o) => o.source_id || o.name);
        S.rows.forEach((r) => {
            const u = r.source_media_url ? byUrl[r.source_media_url] : null;
            const k = byKey[[r.employee_name, r.transaction_date, money(r.amount)].join('|')];
            r._dup = u && u.length > 1 ? {kind: 'image', others: ids(u, r)} : (k.length > 1 ? {kind: 'same', others: ids(k, r)} : null);
        });
    }

    const matchesSearch = (x) => {
        if (!S.search) return true;
        const hay = [x.source_id, x.name, x.details, x.merchant, catOf(x), money(x.amount), label(x.employee_name)].join(' ').toLowerCase();
        return S.search.toLowerCase().split(/\s+/).every((t) => hay.includes(t));
    };
    const visibleRows = () => S.rows.filter((x) => (S.filter === 'nocat' ? !catOf(x) : S.filter === 'unmatched' ? unmatchedSender(x) : S.filter === 'dup' ? !!x._dup : true) && matchesSearch(x));
    function peopleList() {
        const seen = {}, out = [];
        visibleRows().forEach((x) => { const l = label(x.employee_name); if (!seen[l]) { seen[l] = 1; out.push(l); } });
        return out;
    }
    const byDate = (a, b) => String(a.transaction_date || '').localeCompare(String(b.transaction_date || '')) || String(a.source_id || a.name).localeCompare(String(b.source_id || b.name));
    const personRows = () => visibleRows().filter((x) => S.person === ALL || label(x.employee_name) === S.person).sort(byDate);
    function fixPerson() { const p = peopleList(); if (S.person !== ALL && !p.includes(S.person)) { S.person = p[0] || null; S.index = 0; } }
    function setCount(text) { const c = q('.sig-pc-count'); if (c) c.textContent = text; }

    // ---- navigation (role-aware, like the Finance workbench) -----------------------------------
    function canOpen(item) {
        if (item.roleAny && !item.roleAny.some((r) => frappe.user.has_role(r))) return false;
        return !item.doctype || frappe.model.can_read(item.doctype);
    }
    const NAV = [
        {title: __('Finance workbench'), icon: 'line-chart', roleAny: FINANCE, route: ['finance-workbench']}
    ];
    const LINKS = [
        {variant: 'warn', title: __('Draft purchase invoices'), description: __('Invoices created by confirmed receipts, awaiting finance review and submit.'), doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List'], routeOptions: {naming_series: ['like', 'ACC-PC-PINV%'], docstatus: 0},
            metric: {key: 'pc-draft-pi', doc: 'Purchase Invoice', filters: [['Purchase Invoice', 'naming_series', 'like', 'ACC-PC-PINV%'], ['Purchase Invoice', 'docstatus', '=', 0]]}},
        {variant: 'warn', title: __('Draft payments from custody'), description: __('Payment entries from employee custody, awaiting finance review and submit.'), doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List'], routeOptions: {custom_pc_clearance: 1, docstatus: 0},
            metric: {key: 'pc-draft-pe', doc: 'Payment Entry', filters: [['Payment Entry', 'custom_pc_clearance', '=', 1], ['Payment Entry', 'docstatus', '=', 0]]}},
        {variant: 'cyan', title: __('Confirmed this month'), description: __('Receipts confirmed this month and handed to finance.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List'], routeOptions: {closure_status: 'Closed', reviewed_at: ['Timespan', 'this month']},
            metric: {key: 'pc-closed-month', doc: 'SIG PC Transaction', filters: [['SIG PC Transaction', 'closure_status', '=', 'Closed'], ['SIG PC Transaction', 'reviewed_at', 'Timespan', 'this month']]}},
        {variant: 'slate', title: __('Archive pending'), description: __('Receipts waiting to be archived by the SIGPC sync.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List'], routeOptions: {archive_status: ['in', ['Pending', 'Processing']]},
            metric: {key: 'pc-archive-pending', doc: 'SIG PC Transaction', filters: [['SIG PC Transaction', 'archive_status', 'in', ['Pending', 'Processing']]]}},
        {variant: 'slate', title: __('Rejected receipts'), description: __('Receipts rejected during review.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List'], routeOptions: {closure_status: 'Rejected'},
            metric: {key: 'pc-rejected', doc: 'SIG PC Transaction', filters: [['SIG PC Transaction', 'closure_status', '=', 'Rejected']]}},
        {variant: 'slate', title: __('All PC transactions'), description: __('Every receipt, including rejected and archived ones.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List']},
        {variant: 'navy', title: __('PC clearances'), description: __('Cycle clearance register per employee.'), doctype: 'SIG PC Clearance', route: ['List', 'SIG PC Clearance', 'List']},
    ];

    function navButtons() {
        return NAV.filter(canOpen).map((n, i) => `<button type="button" class="sig-pc-ghost" data-nav="${i}"><i class="fa fa-${n.icon}" aria-hidden="true"></i> ${esc(n.title)}</button>`).join('');
    }
    function linkCard(item) {
        return `<button type="button" class="sig-pc-card sig-pc-card--${item.variant}" data-link="${LINKS.indexOf(item)}">
            <span class="sig-pc-card-top"><i class="fa fa-external-link sig-pc-open" aria-hidden="true"></i></span>
            <span class="sig-pc-card-title">${esc(item.title)}</span>
            ${item.metric ? `<span class="sig-pc-metric" data-metric="${esc(item.metric.key)}">—</span>` : ''}
            <span class="sig-pc-detail">${esc(item.description)}</span></button>`;
    }
    function go(item) {
        if (item.routeOptions) frappe.route_options = item.routeOptions;
        frappe.set_route(...item.route);
    }
    function loadMetrics() {
        LINKS.filter((i) => i.metric && canOpen(i)).forEach((item) => {
            call('frappe.desk.doctype.number_card.number_card.get_result', {doc: JSON.stringify({function: 'Count', document_type: item.metric.doc}), filters: JSON.stringify(item.metric.filters)})
                .then((v) => { const n = Number(v); const t = q(`[data-metric="${item.metric.key}"]`); if (t) t.textContent = Number.isFinite(n) ? number(n) : '—'; })
                .catch(() => { const t = q(`[data-metric="${item.metric.key}"]`); if (t) t.textContent = '—'; });
        });
    }

    // ---- shell --------------------------------------------------------------------------------
    root.html(`<header class="sig-pc-header">
            <div><div class="sig-pc-eyebrow">${__('Accounts')}</div>
                <h1>${__('Petty cash')}</h1>
                <p class="sig-pc-count">${__('Loading invoices…')}</p></div>
            <div class="sig-pc-header-actions">${navButtons()}<button type="button" class="sig-pc-ghost sig-pc-refresh"><i class="fa fa-refresh" aria-hidden="true"></i> ${__('Refresh')}</button></div>
        </header>
        <section class="sig-pc-stats"></section>
        <section class="sig-pc-review"><div class="sig-pc-empty">${__('Loading…')}</div></section>
        <section class="sig-pc-section">
            <div class="sig-pc-section-heading"><h2>${__('Finance handoff and records')}</h2><p>${__('Confirmed receipts become draft invoices and payments for finance. Open them from here.')}</p></div>
            <div class="sig-pc-grid">${LINKS.filter(canOpen).map(linkCard).join('')}</div>
        </section>
        <p class="sig-pc-footnote">${__('Confirm creates a draft Purchase Invoice and a draft Payment Entry only. Finance reviews and submits them; ERPNext permissions remain enforced.')}</p>`);

    root.on('click', '[data-nav]', function () { go(NAV.filter(canOpen)[Number($(this).data('nav'))]); });
    root.on('click', '[data-link]', function () { go(LINKS[Number($(this).data('link'))]); });
    root.on('click', '.sig-pc-refresh', () => load());
    root.on('click', '[data-route]', function (e) { e.preventDefault(); frappe.set_route(...JSON.parse($(this).attr('data-route'))); });
    loadMetrics();

    // ---- render -------------------------------------------------------------------------------
    function render() {
        const nocat = S.rows.filter((x) => !catOf(x)).length;
        const unmatched = S.rows.filter(unmatchedSender).length;
        const dups = S.rows.filter((x) => x._dup).length;
        const total = S.rows.reduce((a, r) => a + (Number(r.amount) || 0), 0);
        setCount(__('{0} pending · {1} SAR', [S.rows.length, money(total)]));
        const chip = (key, text, count, variant) => `<button type="button" class="sig-pc-stat ${variant} ${S.filter === key ? 'active' : ''}" data-filter="${key}"><strong>${esc(count)}</strong><span>${esc(text)}</span></button>`;
        q('.sig-pc-stats').innerHTML = chip('all', __('Pending review'), S.rows.length, '') + chip('nocat', __('Need a category'), nocat, 'is-warning') +
            chip('dup', __('Possible duplicates'), dups, 'is-bad') + chip('unmatched', __('Unmatched senders'), unmatched, 'is-neutral');
        q('.sig-pc-stats').querySelectorAll('[data-filter]').forEach((b) => b.addEventListener('click', () => { S.filter = S.filter === b.dataset.filter && b.dataset.filter !== 'all' ? 'all' : b.dataset.filter; S.index = 0; render(); }));

        fixPerson();
        const review = q('.sig-pc-review');
        const rows = personRows();
        if (!rows.length) {
            review.innerHTML = `<div class="sig-pc-empty">${S.rows.length ? __('Nothing matches this filter.') : __('No invoices currently need review.')}${S.search || S.filter !== 'all' ? ` <a href="#" class="sig-pc-clear">${__('Clear filters')}</a>` : ''}</div>`;
            const c = review.querySelector('.sig-pc-clear'); if (c) c.addEventListener('click', (e) => { e.preventDefault(); S.filter = 'all'; S.search = ''; render(); });
            return;
        }
        S.index = Math.max(0, Math.min(S.index, rows.length - 1));
        const x = rows[S.index];
        view = {s: 1, x: 0, y: 0, r: 0, mode: null};

        const prevScroll = q('.sig-pc-queue-list') ? q('.sig-pc-queue-list').scrollTop : 0;
        review.innerHTML = `<div class="sig-pc-bar">
                <div class="sig-pc-progress"><strong>${esc(label(x.employee_name))}</strong> · ${__('Invoice {0} of {1}', [S.index + 1, rows.length])} · ${esc(fmtDate(x.transaction_date))}</div>
                <div class="sig-pc-nav"><button type="button" class="btn btn-default btn-sm" data-prev ${S.index === 0 ? 'disabled' : ''}>← ${__('Previous')}</button><button type="button" class="btn btn-default btn-sm" data-next ${S.index === rows.length - 1 ? 'disabled' : ''}>${__('Next')} →</button></div></div>
            ${unmatchedSender(x) ? `<p class="sig-pc-stagenote">${__('Unmatched sender: this receipt cannot be confirmed until the phone is recorded on the Employee or an Employee-linked Contact.')}</p>` : ''}
            <div class="sig-pc-workarea">${queue(rows)}${card(x)}</div>`;
        review.querySelector('[data-prev]').addEventListener('click', () => step(-1));
        review.querySelector('[data-next]').addEventListener('click', () => step(1));
        wireQueue(rows, prevScroll);
        wireCard(x);
    }
    function step(d) { const n = personRows().length; S.index = Math.max(0, Math.min(n - 1, S.index + d)); render(); }

    // ---- pending list, grouped by date --------------------------------------------------------
    function queue(rows) {
        const counts = {};
        visibleRows().forEach((x) => { const l = label(x.employee_name); counts[l] = (counts[l] || 0) + 1; });
        const people = peopleList();
        const groups = [];
        rows.forEach((x, i) => {
            const d = x.transaction_date || '';
            let g = groups[groups.length - 1];
            if (!g || g.date !== d) { g = {date: d, items: [], total: 0}; groups.push(g); }
            g.items.push({x, i}); g.total += Number(x.amount) || 0;
        });
        const showWho = S.person === ALL;
        const items = groups.map((g) => `<div class="sig-pc-day"><span>${esc(fmtDate(g.date))}</span><small>${countText(g.items.length)} · ${money(g.total)} SAR</small></div>` +
            g.items.map(({x, i}) => {
                const state = x._dup ? 'warn' : (x.transaction_category ? 'ok' : isSuggested(x) ? 'sugg' : 'bad');
                return `<button type="button" class="sig-pc-qi ${i === S.index ? 'active' : ''}" data-i="${i}" role="option" aria-selected="${i === S.index}">
                    <i class="sig-pc-dot sig-pc-dot--${state}" aria-hidden="true"></i>
                    <span class="sig-pc-qi-main"><b>${money(x.amount)}</b><span class="sig-pc-qi-cat ${catOf(x) ? (isSuggested(x) ? 'is-suggested' : '') : 'is-missing'}">${esc(catOf(x) || __('No category'))}${isSuggested(x) ? ` · ${__('suggested')}` : ''}</span>
                    ${showWho ? `<small>${esc(label(x.employee_name))}</small>` : ''}</span>
                    ${x._dup ? `<em class="sig-pc-badge">${__('Duplicate?')}</em>` : ''}</button>`;
            }).join('')).join('');
        return `<aside class="sig-pc-queue" aria-label="${__('Pending receipts')}">
            <div class="sig-pc-queue-head">
                <select class="sig-pc-person-select form-control input-sm" aria-label="${__('Review person')}"><option value="${ALL}"${S.person === ALL ? ' selected' : ''}>${__('All senders')} (${visibleRows().length})</option>${people.map((p) => `<option value="${esc(p)}"${p === S.person ? ' selected' : ''}>${esc(p)} (${counts[p]})</option>`).join('')}</select>
                <input type="search" class="sig-pc-search form-control input-sm" placeholder="${__('Search receipts…')}" value="${esc(S.search)}">
            </div>
            <div class="sig-pc-queue-meta"><span>${__('Pending dates')}</span><span>${countText(rows.length)} · ${money(rows.reduce((a, r) => a + (Number(r.amount) || 0), 0))} SAR</span></div>
            <div class="sig-pc-queue-list" role="listbox">${items}</div>
            <div class="sig-pc-legend"><span><i class="sig-pc-dot sig-pc-dot--bad"></i>${__('No category')}</span><span><i class="sig-pc-dot sig-pc-dot--ok"></i>${__('Category set')}</span><span><i class="sig-pc-dot sig-pc-dot--sugg"></i>${__('Suggested')}</span><span><i class="sig-pc-dot sig-pc-dot--warn"></i>${__('Duplicate?')}</span></div>
        </aside>`;
    }
    function wireQueue(rows, prevScroll) {
        const list = q('.sig-pc-queue-list');
        list.querySelectorAll('.sig-pc-qi').forEach((b) => b.addEventListener('click', () => { S.index = Number(b.dataset.i); render(); }));
        q('.sig-pc-person-select').addEventListener('change', (e) => { S.person = e.target.value; S.index = 0; render(); });
        const search = q('.sig-pc-search');
        let timer;
        search.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => { S.search = search.value.trim(); S.index = 0; render(); const s = q('.sig-pc-search'); if (s) { s.focus(); s.setSelectionRange(s.value.length, s.value.length); } }, 250);
        });
        // keep the list where it was, then make sure the active receipt is visible
        list.scrollTop = prevScroll;
        const a = list.querySelector('.sig-pc-qi.active');
        if (a) { const top = a.offsetTop, bottom = top + a.offsetHeight; if (top < list.scrollTop + 28) list.scrollTop = Math.max(0, top - 40); else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight + 8; }
    }

    // ---- receipt viewer + form ----------------------------------------------------------------
    function viewer(url) {
        if (!url) return `<div class="sig-pc-no-photo">${__('No receipt file URL')}</div>`;
        if (isPdf(url)) return `<iframe class="sig-pc-pdf" src="${esc(url)}" title="${__('Invoice PDF')}"></iframe>`;
        return `<div class="sig-pc-viewer"><div class="sig-pc-vtools">
            <button type="button" data-z="out" title="${__('Zoom out')} (-)">−</button><span class="sig-pc-zoomlabel">${__('Fit')}</span><button type="button" data-z="in" title="${__('Zoom in')} (+)">+</button>
            <button type="button" data-z="mode" class="sig-pc-mode" title="F"></button><button type="button" data-z="actual" title="${__('Actual size')} (1)">100%</button>
            <button type="button" data-z="rot" title="${__('Rotate')} (R)"><i class="fa fa-rotate-right" aria-hidden="true"></i> ${__('Rotate')}</button>
            <span class="sig-pc-vhint">${__('Wheel scrolls · Ctrl+wheel or double-click zooms · drag to move')}</span></div>
            <div class="sig-pc-vstage"><img src="${esc(url)}" alt="${__('Invoice receipt')}" draggable="false"></div></div>`;
    }
    const field = (f, lbl, v, type, extra) => `<div class="sig-pc-field"><label>${lbl}</label><input data-f="${f}" class="form-control input-sm" type="${type || 'text'}" value="${esc(v)}"${extra || ''}></div>`;

    function card(x) {
        const selected = catOf(x);
        const options = CATEGORIES.map((c) => `<option value="${esc(c)}"${selected === c ? ' selected' : ''}>${esc(c)}</option>`).join('');
        const dup = x._dup ? `<p class="sig-pc-dupwarn"><i class="fa fa-exclamation-triangle" aria-hidden="true"></i> ${x._dup.kind === 'image' ? __('Possible duplicate: same receipt image as {0}.', [x._dup.others.join(', ')]) : __('Possible duplicate: same sender, date and amount as {0}.', [x._dup.others.join(', ')])}</p>` : '';
        return `<article class="sig-pc-card-review" data-name="${esc(x.name)}"><div class="sig-pc-photo">${viewer(x.source_media_url)}</div><div class="sig-pc-side">
            <div class="sig-pc-title">${__('Receipt details')}</div>
            ${dup}
            ${field('amount', __('Amount (incl. VAT)'), x.amount, 'number', ' step="0.01" min="0"')}
            <label class="sig-pc-vat"><input data-f="has_vat" type="checkbox"${Number(x.has_vat) ? ' checked' : ''}> ${__('VAT invoice')} <span class="sig-pc-vat-amount"></span></label><p class="sig-pc-vatwarn"></p>
            <div class="sig-pc-field"><label>${__('Transaction category')}</label><select data-f="transaction_category" class="form-control input-sm"><option value="">${__('Choose category…')}</option>${options}</select>${isSuggested(x) ? `<p class="sig-pc-suggest">${__('Suggested from the receipt source. Check it, then confirm.')}</p>` : ''}</div>
            <div class="sig-pc-field"><label>${__('Notes')}</label><textarea data-f="details" class="form-control input-sm" rows="2">${esc(x.details || x.invoice_number || '')}</textarea></div>
            <details class="sig-pc-more"${x.supplier_vat_number || x.merchant ? ' open' : ''}><summary>${__('Supplier')}</summary>
                ${field('merchant', __('Merchant'), x.merchant)}${field('supplier_vat_number', __('Supplier VAT number (15 digits)'), x.supplier_vat_number, 'text', ' inputmode="numeric" maxlength="15"')}</details>
            <div class="sig-pc-actions"><button type="button" class="btn btn-primary sig-pc-confirm">${__('Confirm')}</button><button type="button" class="btn btn-danger sig-pc-reject">${__('Reject')}</button></div>
            <div class="sig-pc-msg"></div>
            <div class="sig-pc-links">${x.source_media_url ? `<a href="${esc(x.source_media_url)}" target="_blank" rel="noopener">${__('Open receipt')}</a> · ` : ''}${x.source_row_url ? `<a href="${esc(x.source_row_url)}" target="_blank" rel="noopener">${__('Source row')}</a> · ` : ''}<a href="#" data-route="${esc(JSON.stringify(['Form', 'SIG PC Transaction', x.name]))}">${__('Open record')}</a></div>
            <p class="sig-pc-hint">${__('Previous/Next never change a receipt. Only Confirm or Reject does. Keys: ← → navigate, Ctrl+Enter confirm, + − 0 zoom, R rotate, F fit.')}</p></div></article>`;
    }

    // ---- card behaviour -----------------------------------------------------------------------
    function values(root_) {
        const v = {};
        root_.querySelectorAll('[data-f]').forEach((i) => { v[i.dataset.f] = i.type === 'checkbox' ? (i.checked ? '1' : '0') : i.value; });
        return v;
    }
    function refreshVat(c) {
        const v = values(c), amount = Number(v.amount) || 0, on = v.has_vat === '1';
        const vat = on ? Math.round(amount * VAT_RATE / (1 + VAT_RATE) * 100) / 100 : 0;
        c.querySelector('.sig-pc-vat-amount').textContent = on ? __('VAT {0} · net {1} SAR', [money(vat), money(amount - vat)]) : '';
        const no = String(v.supplier_vat_number || '').replace(/\s/g, '');
        c.querySelector('.sig-pc-vatwarn').textContent = on && !(no.length === 15 && /^\d+$/.test(no)) ? __('VAT will not be claimed on the invoice until a valid 15-digit supplier VAT number is entered; finance will review it.') : '';
    }
    const showMsg = (c, html) => { c.querySelector('.sig-pc-msg').innerHTML = html; };
    const setBusy = (c, b) => { S.busy = b; c.querySelectorAll('button').forEach((x) => { x.disabled = b; }); };

    function wireCard(x) {
        const c = q('.sig-pc-card-review');
        c.addEventListener('input', () => refreshVat(c));
        c.addEventListener('change', () => refreshVat(c));
        c.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); confirmTx(x, c); } });
        refreshVat(c);
        c.querySelector('.sig-pc-confirm').addEventListener('click', () => confirmTx(x, c));
        c.querySelector('.sig-pc-reject').addEventListener('click', () => rejectBox(x, c));
        wireViewer(c);
    }
    function afterRemoval(x) {
        S.rows = S.rows.filter((r) => r.name !== x.name);
        prepare();
        render();
        loadMetrics();
    }

    async function confirmTx(x, c) {
        if (S.busy) return;
        const v = values(c);
        if (!v.transaction_category) { showMsg(c, `<div class="sig-pc-error">${__('Choose a transaction category before confirming.')}</div>`); return; }
        if (!(Number(v.amount) > 0)) { showMsg(c, `<div class="sig-pc-error">${__('Enter an amount greater than zero.')}</div>`); return; }
        v.transaction_id = x.name;
        showMsg(c, '');
        setBusy(c, true);
        c.querySelector('.sig-pc-confirm').textContent = __('Confirming…');
        try {
            await call('sig_pc_close_transaction', v);
            setBusy(c, false);
            afterRemoval(x);
        } catch (e) {
            setBusy(c, false);
            c.querySelector('.sig-pc-confirm').textContent = __('Confirm');
            showMsg(c, `<div class="sig-pc-error"><strong>${__('Not confirmed. Nothing was saved.')}</strong>\n${esc(e.message)}</div>`);
        }
    }

    function rejectBox(x, c) {
        if (S.busy || c.querySelector('.sig-pc-rejectbox')) return;
        const box = document.createElement('div');
        box.className = 'sig-pc-rejectbox';
        box.innerHTML = `<label>${__('Reason for rejection')}</label><textarea class="form-control"></textarea><div class="sig-pc-actions"><button type="button" class="btn btn-danger btn-sm" data-go>${__('Reject receipt')}</button><button type="button" class="btn btn-default btn-sm" data-cancel>${__('Cancel')}</button></div>`;
        c.querySelector('.sig-pc-msg').before(box);
        box.querySelector('textarea').focus();
        box.querySelector('[data-cancel]').addEventListener('click', () => box.remove());
        box.querySelector('[data-go]').addEventListener('click', async () => {
            const reason = box.querySelector('textarea').value.trim();
            if (!reason) { showMsg(c, `<div class="sig-pc-error">${__('Give a reason for rejecting this receipt.')}</div>`); return; }
            setBusy(c, true); showMsg(c, '');
            try {
                await call('sig_pc_reject_transaction', {transaction_id: x.name, notes: reason});
                setBusy(c, false);
                afterRemoval(x);
            } catch (e) { setBusy(c, false); showMsg(c, `<div class="sig-pc-error">${esc(e.message)}</div>`); }
        });
    }

    // ---- receipt viewer behaviour -------------------------------------------------------------
    // Every receipt opens "fit page" (the whole receipt visible); "Fit width" is one click (or F) away for
    // long receipts. Wheel scrolls, Ctrl+wheel / pinch / buttons / double-click zoom, drag pans, buttons rotate.
    const vstage = () => q('.sig-pc-vstage');
    const vimg = () => q('.sig-pc-vstage img');
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
        const zl = q('.sig-pc-zoomlabel'); if (zl) zl.textContent = view.s === 1 ? (view.mode === 'width' ? __('Fit width') : __('Fit page')) : Math.round(b * view.s * 100) + '%';
        const mb = q('.sig-pc-mode'); if (mb) mb.textContent = view.mode === 'width' ? __('Fit page') : __('Fit width');
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
        c.querySelector('.sig-pc-vtools').addEventListener('click', (e) => {
            const b = e.target.closest('[data-z]'); if (!b) return;
            const a = b.dataset.z;
            if (a === 'in') zoomCenter(1.3); else if (a === 'out') zoomCenter(1 / 1.3);
            else if (a === 'mode') toggleMode(); else if (a === 'actual') actualSize(); else if (a === 'rot') rotate();
        });
        img.addEventListener('error', () => { const v = q('.sig-pc-viewer'); if (v) v.outerHTML = `<div class="sig-pc-no-photo">${__('Receipt preview unavailable — use Open receipt')}</div>`; });
    }

    let resizeTimer;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (vstage()) layout(true); }, 120); });

    // Keys only act while this Page is the current route (Desk keeps pages mounted).
    document.addEventListener('keydown', (e) => {
        if ((frappe.get_route() || [])[0] !== 'pc-invoice-review') return;
        const tag = (document.activeElement && document.activeElement.tagName) || '';
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(tag) || e.ctrlKey || e.metaKey || e.altKey || S.busy || $('.modal.show').length) return;
        const k = String(e.key || '').toLowerCase();
        if (k === 'arrowright' || k === 'd') { e.preventDefault(); step(1); }
        else if (k === 'arrowleft' || k === 'a') { e.preventDefault(); step(-1); }
        else if (!vstage()) return;
        else if (k === '+' || k === '=') zoomCenter(1.3);
        else if (k === '-') zoomCenter(1 / 1.3);
        else if (k === '0') layout(true);
        else if (k === '1') actualSize();
        else if (k === 'f') toggleMode();
        else if (k === 'r') rotate();
    });

    // Reload when the page is shown again (e.g. after finance submitted drafts), at most every 30 s.
    frappe.pages['pc-invoice-review'].on_page_show = function () {
        if (!frappe.model.can_read('SIG PC Transaction')) return;
        if (Date.now() - S.loadedAt > 30000) { load(); loadMetrics(); }
    };

    if (!REVIEWERS.some((r) => frappe.user.has_role(r)) || !frappe.model.can_read('SIG PC Transaction')) {
        setCount(__('Not available'));
        q('.sig-pc-review').innerHTML = `<div class="sig-pc-empty">${__('Your ERP role cannot review petty cash receipts.')}</div>`;
    } else {
        load();
    }
};
