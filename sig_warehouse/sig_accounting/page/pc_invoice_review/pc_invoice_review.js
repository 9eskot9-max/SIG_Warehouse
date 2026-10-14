// Petty cash invoice review - app-owned Desk Page (replaces the website Web Page /pc-invoice-review).
// Runs inside the Desk shell, so the SIG logo/navbar, session, CSRF and permissions are native.
// Data: SIG PC Transaction (one list call) + SIG PC Sender Staging. Actions are the sig_pc_* Server Scripts.
// Navigation only links to ERPNext records; ERPNext permissions stay authoritative.
frappe.pages['pc-invoice-review'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Petty Cash Review'), single_column: true});
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-pc-home"></main>').attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr').attr('lang', language).appendTo(page.main);
    const el = root[0];
    const q = (sel) => el.querySelector(sel);

    const CATEGORIES = ['Fuel/Disel', 'Hotel Rent', 'Food expenses', 'Equipment Rental', 'Car Maintanence', 'Construction/Operational Material', 'Vehicle OIL change', 'Vehicle Other Misc.', 'Drinking water', 'Medical expenses', 'Phone bill', 'Trailer Rent', 'Dyna Rent', 'Work Labor', 'Car Spare Parts', 'Others', 'Air-Ticket', 'Bus Ticket', 'Fax', 'Iqama fees', 'Office rental', 'Stationaries', 'Taxi', 'Train ticket', 'VISA fees', 'Xerox Copy', 'Fork Lift Rent', 'Pickup Rent', 'Office - Housekeeping', 'Warehouse misc.'];
    const FIELDS = ['name', 'employee_name', 'transaction_date', 'amount', 'purpose', 'transaction_category', 'has_vat', 'vat_amount', 'supplier_vat_number', 'merchant', 'invoice_number', 'details', 'vehicle', 'odo', 'site', 'source_id', 'source_media_url', 'source_row_url'];
    const VAT_RATE = 0.15;
    const REVIEWERS = ['System Manager', 'Accounts User', 'Accounts Manager', 'Operations User', 'Operations Manager'];
    const FINANCE = ['System Manager', 'Accounts User', 'Accounts Manager', 'SIG Finance Viewer'];

    const S = {rows: [], senders: {}, filter: 'all', person: null, index: 0, busy: false, loadedAt: 0, banner: ''};
    let view = {s: 1, x: 0, y: 0, r: 0, mode: null};

    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const isPhone = (v) => /^\+?\d{9,15}$/.test(String(v || '').replace(/\s/g, ''));
    const phoneKey = (v) => String(v || '').replace(/\s/g, '').replace(/^\+/, '');
    const isPdf = (v) => /\.pdf(?:[?#]|$)/i.test(String(v || '')) || /[?&]\w*=pdf(?:&|$)/i.test(String(v || ''));
    const money = (n) => (Math.round((Number(n) || 0) * 100) / 100).toFixed(2);
    const number = (n) => new Intl.NumberFormat(language.replace('_', '-'), {maximumFractionDigits: 0}).format(n);
    const unmatchedSender = (x) => isPhone(x.employee_name) && !S.senders[phoneKey(x.employee_name)];

    function label(v) {
        if (isPhone(v)) return S.senders[phoneKey(v)] || (__('Unmatched sender') + ' · ' + v);
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
            const [tx, st] = await Promise.all([
                call('frappe.client.get_list', {doctype: 'SIG PC Transaction', fields: JSON.stringify(FIELDS), filters: JSON.stringify([['closure_status', 'in', ['Draft', 'Needs Review']]]), order_by: 'employee_name asc, transaction_date asc', limit_page_length: 0}),
                call('frappe.client.get_list', {doctype: 'SIG PC Sender Staging', fields: JSON.stringify(['sender_phone', 'candidate_name', 'employee']), limit_page_length: 0}).catch(() => [])
            ]);
            S.rows = tx || [];
            S.senders = {};
            (st || []).forEach((r) => { if (r.candidate_name) S.senders[phoneKey(r.sender_phone)] = r.candidate_name + (r.employee ? '' : ' · ' + __('staged')); });
            S.loadedAt = Date.now();
            render();
        } catch (e) {
            setCount(__('Review board unavailable'));
            q('.sig-pc-review').innerHTML = `<div class="sig-pc-empty">${esc(e.message || __('Could not load invoices.'))}</div>`;
        }
    }

    const visibleRows = () => S.rows.filter((x) => S.filter === 'nocat' ? !x.transaction_category : S.filter === 'unmatched' ? unmatchedSender(x) : true);
    function peopleList() {
        const seen = {}, out = [];
        visibleRows().forEach((x) => { const l = label(x.employee_name); if (!seen[l]) { seen[l] = 1; out.push(l); } });
        return out;
    }
    const personRows = () => visibleRows().filter((x) => label(x.employee_name) === S.person).sort((a, b) =>
        String(a.transaction_date || '').localeCompare(String(b.transaction_date || '')) || String(a.source_id || a.name).localeCompare(String(b.source_id || b.name)));
    function fixPerson() { const p = peopleList(); if (!p.includes(S.person)) { S.person = p[0] || null; S.index = 0; } }
    function setCount(text) { const c = q('.sig-pc-count'); if (c) c.textContent = text; }

    // ---- navigation (role-aware, like the Finance workbench) -----------------------------------
    function canOpen(item) {
        if (item.roleAny && !item.roleAny.some((r) => frappe.user.has_role(r))) return false;
        return !item.doctype || frappe.model.can_read(item.doctype);
    }
    const NAV = [
        {title: __('Finance workbench'), icon: 'line-chart', roleAny: FINANCE, route: ['finance-workbench']},
        {title: __('SIG Petty Cash'), icon: 'folder-open-o', roleAny: FINANCE.concat(['SIG PC Clearance']), route: ['Workspaces', 'SIG Petty Cash']}
    ];
    const LINKS = [
        {variant: 'warn', title: __('Draft purchase invoices'), description: __('Invoices created by confirmed receipts, awaiting finance review and submit.'), doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List'], routeOptions: {naming_series: ['like', 'ACC-PC-PINV%'], docstatus: 0},
            metric: {key: 'pc-draft-pi', filters: [['Purchase Invoice', 'naming_series', 'like', 'ACC-PC-PINV%'], ['Purchase Invoice', 'docstatus', '=', 0]]}},
        {variant: 'warn', title: __('Draft payments from custody'), description: __('Payment entries from employee custody, awaiting finance review and submit.'), doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List'], routeOptions: {custom_pc_clearance: 1, docstatus: 0},
            metric: {key: 'pc-draft-pe', filters: [['Payment Entry', 'custom_pc_clearance', '=', 1], ['Payment Entry', 'docstatus', '=', 0]]}},
        {variant: 'cyan', title: __('Confirmed receipts'), description: __('Receipts already confirmed and handed to finance.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List'], routeOptions: {closure_status: 'Closed'},
            metric: {key: 'pc-closed', filters: [['SIG PC Transaction', 'closure_status', '=', 'Closed']]}},
        {variant: 'navy', title: __('PC clearances'), description: __('Cycle clearance register per employee.'), doctype: 'SIG PC Clearance', route: ['List', 'SIG PC Clearance', 'List']},
        {variant: 'slate', title: __('All PC transactions'), description: __('Every receipt, including rejected and archived ones.'), doctype: 'SIG PC Transaction', route: ['List', 'SIG PC Transaction', 'List']},
        {variant: 'slate', title: __('Sender mapping'), description: __('Match phone senders to employees so their receipts can be confirmed.'), doctype: 'SIG PC Sender Staging', route: ['List', 'SIG PC Sender Staging', 'List']}
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
            call('frappe.desk.doctype.number_card.number_card.get_result', {doc: JSON.stringify({function: 'Count', document_type: item.doctype}), filters: JSON.stringify(item.metric.filters)})
                .then((v) => { const n = Number(v); const t = q(`[data-metric="${item.metric.key}"]`); if (t) t.textContent = Number.isFinite(n) ? number(n) : '—'; })
                .catch(() => { const t = q(`[data-metric="${item.metric.key}"]`); if (t) t.textContent = '—'; });
        });
    }

    // ---- shell --------------------------------------------------------------------------------
    root.html(`<header class="sig-pc-header">
            <div><div class="sig-pc-eyebrow">${__('Accounts')} · ${__('Petty cash')}</div>
                <h1>${__('Petty cash invoice review')}</h1>
                <p class="sig-pc-count">${__('Loading invoices…')}</p></div>
            <div class="sig-pc-header-actions">${navButtons()}<button type="button" class="sig-pc-ghost sig-pc-refresh"><i class="fa fa-refresh" aria-hidden="true"></i> ${__('Refresh')}</button></div>
        </header>
        <div class="sig-pc-banner" role="status" aria-live="polite" hidden></div>
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
    root.on('click', '[data-route]', function (e) { e.preventDefault(); const r = JSON.parse($(this).attr('data-route')); frappe.set_route(...r); });
    root.on('click', '.sig-pc-banner-close', () => { S.banner = ''; showBanner(''); });
    loadMetrics();

    function showBanner(html) { const b = q('.sig-pc-banner'); b.hidden = !html; b.innerHTML = html ? `<span>${html}</span><button type="button" class="sig-pc-banner-close" aria-label="${__('Dismiss')}">×</button>` : ''; }
    const docLink = (doctype, name) => `<a href="#" data-route="${esc(JSON.stringify(['Form', doctype, name]))}">${esc(name)}</a>`;

    // ---- render -------------------------------------------------------------------------------
    function render() {
        const nocat = S.rows.filter((x) => !x.transaction_category).length;
        const unmatched = S.rows.filter(unmatchedSender).length;
        setCount(__('{0} pending · {1} need a category · {2} from unmatched senders', [S.rows.length, nocat, unmatched]));
        const chip = (key, text, count, variant) => `<button type="button" class="sig-pc-stat ${variant} ${S.filter === key ? 'active' : ''}" data-filter="${key}"><strong>${esc(count)}</strong><span>${esc(text)}</span></button>`;
        q('.sig-pc-stats').innerHTML = chip('all', __('Pending review'), S.rows.length, '') + chip('nocat', __('Need a category'), nocat, 'is-warning') + chip('unmatched', __('Unmatched senders'), unmatched, 'is-neutral');
        q('.sig-pc-stats').querySelectorAll('[data-filter]').forEach((b) => b.addEventListener('click', () => { S.filter = b.dataset.filter; S.person = null; S.index = 0; render(); }));

        fixPerson();
        const people = peopleList(), counts = {};
        visibleRows().forEach((x) => { const l = label(x.employee_name); counts[l] = (counts[l] || 0) + 1; });
        const rows = personRows(), review = q('.sig-pc-review');
        if (!rows.length) { review.innerHTML = `<div class="sig-pc-empty">${S.rows.length ? __('Nothing in this filter.') : __('No invoices currently need review.')}</div>`; return; }
        S.index = Math.max(0, Math.min(S.index, rows.length - 1));
        const x = rows[S.index];
        view = {s: 1, x: 0, y: 0, r: 0, mode: null};

        review.innerHTML = `<div class="sig-pc-panel">
            <div class="sig-pc-panel-head"><label class="sig-pc-person">${__('Review person')} <select class="sig-pc-person-select">${people.map((p) => `<option value="${esc(p)}"${p === S.person ? ' selected' : ''}>${esc(p)} (${counts[p]})</option>`).join('')}</select></label>
                <div class="sig-pc-progress">${__('Invoice {0} of {1}', [S.index + 1, rows.length])} · ${esc(x.transaction_date || '')}</div>
                <div class="sig-pc-nav"><button type="button" class="btn btn-default btn-sm" data-prev ${S.index === 0 ? 'disabled' : ''}>← ${__('Previous')}</button><button type="button" class="btn btn-default btn-sm" data-next ${S.index === rows.length - 1 ? 'disabled' : ''}>${__('Next')} →</button></div></div>
            ${unmatchedSender(x) ? `<p class="sig-pc-stagenote">${__('Unmatched sender: this receipt cannot be confirmed until the sender is matched to an Employee in Sender mapping.')}</p>` : ''}
            ${card(x)}</div>`;
        review.querySelector('.sig-pc-person-select').addEventListener('change', (e) => { S.person = e.target.value; S.index = 0; render(); });
        review.querySelector('[data-prev]').addEventListener('click', () => step(-1));
        review.querySelector('[data-next]').addEventListener('click', () => step(1));
        wireCard(x);
    }
    function step(d) { const n = personRows().length; S.index = Math.max(0, Math.min(n - 1, S.index + d)); render(); }

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
        const selected = x.transaction_category || x.purpose || '';
        const options = CATEGORIES.map((c) => `<option value="${esc(c)}"${selected === c ? ' selected' : ''}>${esc(c)}</option>`).join('');
        return `<article class="sig-pc-card-review" data-name="${esc(x.name)}"><div class="sig-pc-photo">${viewer(x.source_media_url)}</div><div class="sig-pc-side">
            <div class="sig-pc-title">${esc(x.source_id || x.name)}</div>
            ${field('amount', __('Amount (incl. VAT)'), x.amount, 'number', ' step="0.01" min="0"')}
            <label class="sig-pc-vat"><input data-f="has_vat" type="checkbox"${Number(x.has_vat) ? ' checked' : ''}> ${__('VAT invoice')} <span class="sig-pc-vat-amount"></span></label><p class="sig-pc-vatwarn"></p>
            <div class="sig-pc-field"><label>${__('Transaction category')}</label><select data-f="transaction_category" class="form-control input-sm"><option value="">${__('Choose category…')}</option>${options}</select></div>
            ${field('details', __('Invoice / Notes'), x.details || x.invoice_number || '')}
            <details class="sig-pc-more"${x.supplier_vat_number || x.merchant ? ' open' : ''}><summary>${__('Supplier, vehicle & site')}</summary>
                ${field('merchant', __('Merchant'), x.merchant)}${field('supplier_vat_number', __('Supplier VAT number (15 digits)'), x.supplier_vat_number, 'text', ' inputmode="numeric" maxlength="15"')}${field('invoice_number', __('Invoice number'), x.invoice_number)}
                <div class="sig-pc-row2">${field('vehicle', __('Vehicle'), x.vehicle)}${field('odo', __('ODO'), x.odo)}</div>${field('site', __('Site / Project'), x.site)}</details>
            <div class="sig-pc-actions"><button type="button" class="btn btn-primary sig-pc-confirm">${__('Confirm')}</button><button type="button" class="btn btn-danger sig-pc-reject">${__('Reject')}</button></div>
            <div class="sig-pc-msg"></div>
            <div class="sig-pc-links">${x.source_media_url ? `<a href="${esc(x.source_media_url)}" target="_blank" rel="noopener">${__('Open receipt')}</a>` : ''}${x.source_row_url ? ` · <a href="${esc(x.source_row_url)}" target="_blank" rel="noopener">${__('Source row')}</a>` : ''}${` · `}<a href="#" data-route="${esc(JSON.stringify(['Form', 'SIG PC Transaction', x.name]))}">${__('Open record')}</a></div>
            <p class="sig-pc-hint">${__('Previous/Next never change a receipt. Only Confirm or Reject does. Keys: ← → navigate, + − 0 zoom, R rotate, F fit.')}</p></div></article>`;
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
        refreshVat(c);
        c.querySelector('.sig-pc-confirm').addEventListener('click', () => confirmTx(x, c));
        c.querySelector('.sig-pc-reject').addEventListener('click', () => rejectBox(x, c));
        wireViewer(c);
    }
    function afterRemoval(x) {
        S.rows = S.rows.filter((r) => r.name !== x.name);
        fixPerson();
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
            const m = (await call('sig_pc_close_transaction', v)) || {};
            S.banner = `${__('Cleared')} ${esc(x.source_id || x.name)} · ${esc(v.transaction_category)}` +
                (m.purchase_invoice ? ` · ${__('Draft Purchase Invoice')} ${docLink('Purchase Invoice', m.purchase_invoice)}` : '') +
                (m.payment_entry ? ` · ${__('Draft Payment Entry')} ${docLink('Payment Entry', m.payment_entry)}` : '');
            setBusy(c, false);
            afterRemoval(x);
            showBanner(S.banner);
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
                showBanner(`${__('Rejected')} ${esc(x.source_id || x.name)}`);
            } catch (e) { setBusy(c, false); showMsg(c, `<div class="sig-pc-error">${esc(e.message)}</div>`); }
        });
    }

    // ---- receipt viewer -----------------------------------------------------------------------
    // Base size is computed from the image's natural size: tall photos / long receipts open "fit width"
    // (readable; scroll down), everything else opens "fit page". Wheel scrolls, Ctrl+wheel / pinch /
    // buttons / double-click zoom, drag pans, buttons rotate.
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
        if (!view.mode) view.mode = d.contain < d.wide * 0.7 ? 'width' : 'page';
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
