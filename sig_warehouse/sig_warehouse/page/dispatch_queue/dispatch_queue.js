// Pure ordering/search helpers: the single implementation (the server only returns newest first).
// Exposed on window.sig_dq_pure so tests/test_dispatch_queue_pure.cjs can exercise them.
(function () {
    function sortRows(rows, mode) {
        const created = (r) => String(r.created || '');
        if (mode === 'waiting') {
            const open = (r) => r.stage === 'PENDING' || r.stage === 'PARTIAL';
            const w = rows.filter(open).sort((a, b) =>
                String(a.required_by || '9999').localeCompare(String(b.required_by || '9999')) || created(a).localeCompare(created(b)));
            const rest = rows.filter((r) => !open(r)).sort((a, b) => created(b).localeCompare(created(a)));
            return w.concat(rest);
        }
        if (mode === 'attention') {
            const key = (r) => [r.availability === 'red' ? 0 : 1, (r.flags || []).includes('return_blocks_close') ? 0 : 1, -(r.age_days || 0)];
            return rows.slice().sort((a, b) => {
                const x = key(a), y = key(b);
                for (let i = 0; i < 3; i++) { if (x[i] !== y[i]) return x[i] - y[i]; }
                return String(a.name).localeCompare(String(b.name));
            });
        }
        return rows.slice().sort((a, b) => created(b).localeCompare(created(a)) || String(b.name).localeCompare(String(a.name)));
    }
    function matches(row, query) {
        const q = String(query || '').trim().toLowerCase();
        return !q || [row.name, row.mir, row.site, row.project, row.po, row.work_type].join(' ').toLowerCase().includes(q);
    }
    (typeof window !== 'undefined' ? window : globalThis).sig_dq_pure = {sortRows, matches};
})();

frappe.pages['dispatch-queue'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Dispatch Queue'), single_column: true});
    const root = $('<main class="sig-dq-page"></main>').appendTo(page.main);
    const API = 'sig_warehouse.sig_warehouse.dispatch_queue.';
    const PAGE_SIZE = 50;
    const STAGES = [
        ['PENDING', __('Pending'), __('Nothing issued yet')],
        ['PARTIAL', __('Partial'), __('Some issued or cancelled')],
        ['DISPATCHED', __('Dispatched'), __('Returns not yet declared')],
        ['CLOSED', __('Closed'), __('Recently closed')],
    ];
    const FLAG_TEXT = {
        cancelled_partial: __('Remainder cancelled; stays partial'),
        return_blocks_close: __('Waiting for return declaration'),
        no_open_lines_but_open_stage: __('No open lines but stage not resolved - review'),
    };
    const state = {data: null, stage: '', query: '', project: '', availability: '', sort: 'newest',
        includeClosed: false, page: 1, selected: '', detail: null, loadId: 0, status: 'loading', error: ''};
    try { state.sort = localStorage.getItem('sig_dq_sort') || 'newest'; } catch (e) { /* storage unavailable */ }

    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const num = (v) => { const n = Number(v) || 0; return Number.isInteger(n) ? String(n) : n.toFixed(2); };
    const date = (v) => v ? frappe.datetime.str_to_user(String(v).slice(0, 10)) : '—';

    function visibleRows() {
        const rows = ((state.data && state.data.rows) || []).filter((r) => {
            if (state.stage ? r.stage !== state.stage : r.stage === 'CLOSED') return false;
            if (state.project && r.project !== state.project) return false;
            if (state.availability && r.availability !== state.availability) return false;
            return window.sig_dq_pure.matches(r, state.query);
        });
        return window.sig_dq_pure.sortRows(rows, state.sort);
    }

    function shell() {
        root.html(`<header class="sig-dq-header"><div><div class="sig-dq-eyebrow">${__('SIG Warehouse')}</div>
            <h1>${__('Dispatch Queue')}</h1><p>${__('Material Issue requests by dispatch stage.')}</p></div>
            <nav><button type="button" class="btn btn-default sig-dq-kanban">${__('Kanban view')}</button>
            <button type="button" class="btn btn-default sig-dq-custody" style="display:none">${__('Tool / asset custody')}</button>
            <button type="button" class="btn btn-default sig-dq-refresh">${__('Refresh')}</button></nav></header>
            <section class="sig-dq-tiles"></section>
            <div class="sig-dq-notices"></div>
            <div class="sig-dq-toolbar">
              <label class="sig-dq-search">${__('Find a request')}<input class="form-control" placeholder="${__('MIR #, MR ID, site, PO or project')}"></label>
              <label>${__('Project')}<select class="form-control sig-dq-project"></select></label>
              <label>${__('Availability')}<select class="form-control sig-dq-avail">
                <option value="">${__('Any')}</option><option value="green">${__('Covered here')}</option>
                <option value="yellow">${__('Covered elsewhere')}</option><option value="red">${__('Short')}</option></select></label>
              <label>${__('Sort')}<select class="form-control sig-dq-sort">
                <option value="newest">${__('Newest first')}</option><option value="waiting">${__('Oldest waiting first')}</option>
                <option value="attention">${__('Needs attention')}</option></select></label>
              <label class="sig-dq-check"><input type="checkbox"> ${__('Include recently closed')}</label>
              <span class="sig-dq-count"></span></div>
            <div class="sig-dq-layout"><section class="sig-dq-table-wrap"></section><aside class="sig-dq-detail"></aside></div>
            <div class="sig-dq-footnote">${__('The stage is calculated from issues, cancellations and return declarations. A cancelled remainder keeps a request partial. A request is closed only when every issue has its return declared.')}</div>`);
        root.find('.sig-dq-kanban').on('click', () => frappe.set_route('List', 'Material Request', 'Kanban', 'SIG Dispatch Queue'));
        root.find('.sig-dq-custody').on('click', () => {
            if (window.sig_wh && window.sig_wh.open_custody_dialog) window.sig_wh.open_custody_dialog();
            else frappe.msgprint(__('Dispatch module still loading - try again in a moment.'));
        });
        root.find('.sig-dq-refresh').on('click', load);
        root.find('.sig-dq-search input').on('input', frappe.utils.debounce(function () { state.query = this.value.trim(); state.page = 1; renderTable(); }, 250));
        root.find('.sig-dq-project').on('change', function () { state.project = this.value; state.page = 1; renderTable(); });
        root.find('.sig-dq-avail').on('change', function () { state.availability = this.value; state.page = 1; renderTable(); });
        root.find('.sig-dq-sort').val(state.sort).on('change', function () {
            state.sort = this.value; state.page = 1;
            try { localStorage.setItem('sig_dq_sort', state.sort); } catch (e) { /* ignore */ }
            renderTable();
        });
        root.find('.sig-dq-check input').on('change', function () { state.includeClosed = this.checked; if (!this.checked && state.stage === 'CLOSED') state.stage = ''; state.page = 1; load(); });
    }

    function renderTiles() {
        const s = (state.data && state.data.summary) || {};
        const counts = {PENDING: s.PENDING, PARTIAL: s.PARTIAL, DISPATCHED: s.DISPATCHED, CLOSED: s.CLOSED_RECENT};
        const sub = {DISPATCHED: s.return_pending ? __('{0} awaiting return', [s.return_pending]) : ''};
        root.find('.sig-dq-tiles').html(`<div class="sig-dq-tiles-head"><div><h2>${__('Stage')}</h2>
            <p>${__('Click a stage to filter. Counts cover every request, not only the visible page.')}</p></div>
            <button type="button" class="btn btn-default btn-xs sig-dq-clear" style="flex-direction:row">${__('All open')}</button></div>` +
            STAGES.filter(([k]) => k !== 'CLOSED' || state.includeClosed).map(([k, label, hint]) =>
                `<button type="button" data-stage="${k}" class="${state.stage === k ? 'active' : ''}"><strong>${esc(counts[k] == null ? '—' : counts[k])}</strong>
                 <span>${esc(label)}</span><small>${esc(sub[k] || hint)}</small></button>`).join(''));
        root.find('.sig-dq-tiles [data-stage]').on('click', function () {
            state.stage = state.stage === this.dataset.stage ? '' : this.dataset.stage; state.page = 1; renderTiles(); renderTable();
        });
        root.find('.sig-dq-clear').on('click', () => { state.stage = ''; state.page = 1; renderTiles(); renderTable(); });
    }

    function renderFilters() {
        const rows = (state.data && state.data.rows) || [];
        const projects = [...new Set(rows.map((r) => r.project).filter(Boolean))].sort();
        const sel = root.find('.sig-dq-project').empty().append($('<option></option>').val('').text(__('All projects')));
        projects.forEach((p) => sel.append($('<option></option>').val(p).text(p)));
        sel.val(projects.includes(state.project) ? state.project : '');
        if (!projects.includes(state.project)) state.project = '';
        root.find('.sig-dq-avail').val(state.availability);
        root.find('.sig-dq-check input').prop('checked', state.includeClosed);
        const access = (state.data && state.data.access) || {};
        // Custody dispatch is server-gated to the same roles as MIR dispatch; do not offer it to view-only users.
        root.find('.sig-dq-custody').toggle(!!access.can_dispatch);
        const notes = [];
        if (state.data && !state.data.complete) notes.push(__('The list reached its size limit; narrow the filters or ask for a larger limit.'));
        if (state.data && !access.dn) notes.push(__('Your role cannot read Stock Entries: return state is hidden.'));
        if (state.data && !access.availability) notes.push(__('Your role cannot read Bins: stock availability is hidden.'));
        root.find('.sig-dq-notices').html(notes.map((n) => `<div class="sig-dq-notice">${esc(n)}</div>`).join(''));
    }

    function dot(r) { return r.availability ? `<span class="sig-dq-dot ${esc(r.availability)}" title="${esc(r.availability)}"></span>` : '<span class="sig-dq-dot"></span>'; }
    function returnLabel(r) {
        if (r.return == null) return '—';
        return ({NONE: __('No issue yet'), PENDING: __('Pending'), PARTIAL: __('Partial'), DECLARED: __('Declared')})[r.return] || esc(r.return);
    }

    function renderTable() {
        const wrap = root.find('.sig-dq-table-wrap');
        if (state.status === 'loading') { wrap.html(`<div class="sig-dq-loading">${__('Loading requests...')}</div>`); return; }
        if (state.status === 'error') { wrap.html(`<div class="sig-dq-error">${esc(state.error)}</div>`); root.find('.sig-dq-count').text(''); return; }
        const all = visibleRows();
        const pages = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
        state.page = Math.min(state.page, pages);
        const rows = all.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
        root.find('.sig-dq-count').text(__('{0} requests', [all.length]));
        if (!rows.length) { wrap.html(`<div class="sig-dq-empty">${__('No requests match.')}</div>`); return; }
        wrap.html(`<table><thead><tr><th>${__('Request')}</th><th>${__('Site / project')}</th><th>${__('Stage')}</th><th>${__('Lines open')}</th>
            <th>${__('Remaining')}</th><th>${__('Stock')}</th><th>${__('Last issue')}</th><th>${__('Returns')}</th><th>${__('Age')}</th></tr></thead><tbody>` +
            rows.map((r) => `<tr data-mr="${esc(r.name)}" class="${state.selected === r.name ? 'selected' : ''}">
                <td><b>${r.mir ? esc(__('MIR {0}', [r.mir])) : esc(r.name)}</b><small>${esc(r.name)}</small></td>
                <td><b>${esc(r.site || '—')}</b><small>${esc(r.project || r.po || '')}</small></td>
                <td><span class="sig-dq-badge ${esc(r.stage)}">${esc(r.stage)}</span>${(r.flags || []).map((f) => `<span class="sig-dq-flag">${esc(FLAG_TEXT[f] || f)}</span>`).join('')}</td>
                <td>${esc(r.lines.open)} / ${esc(r.lines.total)}</td>
                <td>${num(r.qty.remaining)} <small>${__('of')} ${num(r.qty.requested)}</small></td>
                <td>${dot(r)}</td>
                <td>${r.dn.last ? `${esc(r.dn.last)}<small>${date(r.dn.last_date)}</small>` : '—'}</td>
                <td>${returnLabel(r)}</td><td>${esc(r.age_days)} ${__('d')}</td></tr>`).join('') +
            `</tbody></table>` + (pages > 1 ? `<div class="sig-dq-pager"><button type="button" class="btn btn-default btn-xs sig-dq-prev" ${state.page <= 1 ? 'disabled' : ''}>${__('Previous')}</button>
                <span>${__('Page {0} of {1}', [state.page, pages])}</span><button type="button" class="btn btn-default btn-xs sig-dq-next" ${state.page >= pages ? 'disabled' : ''}>${__('Next')}</button></div>` : ''));
        wrap.find('tbody tr').on('click', function () { select(this.dataset.mr); });
        wrap.find('.sig-dq-prev').on('click', () => { state.page = Math.max(1, state.page - 1); renderTable(); });
        wrap.find('.sig-dq-next').on('click', () => { state.page = Math.min(pages, state.page + 1); renderTable(); });
    }

    function actionsFor(stage) {
        if (stage === 'PENDING') return ['issue', 'cancel'];
        if (stage === 'PARTIAL') return ['issue', 'return', 'cancel'];
        return ['return'];
    }

    function renderDetail() {
        const box = root.find('.sig-dq-detail');
        if (!state.selected) { box.html(`<div class="sig-dq-empty">${__('Select a request to see its lines, issues and returns.')}</div>`); return; }
        const d = state.detail;
        if (!d || d.row.name !== state.selected) { box.html(`<div class="sig-dq-loading">${__('Loading...')}</div>`); return; }
        const r = d.row;
        const canAct = d.access && d.access.can_dispatch;
        box.html(`<div class="sig-dq-detail-head"><h2>${esc(r.mir ? __('MIR {0}', [r.mir]) : r.name)}</h2>
            <p>${esc(r.name)} · ${esc(r.site || '—')} · ${esc(r.project || r.po || '—')}</p></div>
            <div class="sig-dq-detail-body"><span class="sig-dq-badge ${esc(r.stage)}">${esc(r.stage)}</span> ${dot(r)}
            ${(r.flags || []).map((f) => `<div class="sig-dq-explain">${esc(FLAG_TEXT[f] || f)}</div>`).join('')}
            <h3>${__('Lines')}</h3><table><thead><tr><th>${__('Item')}</th><th>${__('Req.')}</th><th>${__('Issued')}</th><th>${__('Canc.')}</th><th>${__('Left')}</th></tr></thead><tbody>` +
            d.lines.map((l) => `<tr><td>${esc(l.item_code)}<br><small>${esc(l.custom_line_status || '')}</small></td><td>${num(l.qty)}</td><td>${num(l.custom_qty_issued)}</td><td>${num(l.custom_qty_cancelled)}</td><td>${num(l.custom_qty_remaining)}</td></tr>`).join('') +
            `</tbody></table><h3>${__('Issues (DN)')}</h3>` +
            (!d.access.dn ? `<div class="sig-dq-explain">${__('Not visible for your role.')}</div>` :
                (d.dns.length ? d.dns.map((s) => `<div class="sig-dq-explain"><b>${esc(s.name)}</b> · ${date(s.posting_date)} · ${esc(s.custom_return_state || 'PENDING')}</div>`).join('') : `<div class="sig-dq-explain">${__('No issue recorded.')}</div>`)) +
            (d.returns.length ? `<h3>${__('Returns')}</h3>` + d.returns.map((s) => `<div class="sig-dq-explain">${esc(s.name)} · ${date(s.posting_date)}</div>`).join('') : '') +
            (canAct ? `<div class="sig-dq-actions">` + actionsFor(r.stage).map((a) =>
                `<button type="button" class="btn btn-default btn-sm" data-act="${a}">${({issue: __('Issue'), return: __('Return'), cancel: __('Cancel remaining')})[a]}</button>`).join('') + `</div>` : '') +
            `<div class="sig-dq-actions"><button type="button" class="btn btn-default btn-xs sig-dq-open">${__('Open request')}</button></div></div>`);
        box.find('.sig-dq-open').on('click', () => frappe.set_route('Form', 'Material Request', r.name));
        box.find('[data-act]').on('click', function () { act(this.dataset.act, r.name); });
    }

    function select(name) {
        state.selected = name; state.detail = null;
        root.find('.sig-dq-table-wrap tbody tr').removeClass('selected').filter(function () { return this.dataset.mr === name; }).addClass('selected');
        renderDetail();
        frappe.call({method: API + 'get_mr_detail', args: {mr: name}, silent: true}).then((r) => {
            if (state.selected !== name) return;
            state.detail = r.message; renderDetail();
        }, (err) => { if (state.selected === name) root.find('.sig-dq-detail').html(`<div class="sig-dq-error">${esc(serverMessage(err))}</div>`); });
    }

    function refreshOne(name) {
        if (window.sig_wh && window.sig_wh.invalidate_availability) window.sig_wh.invalidate_availability(name);
        frappe.call({method: API + 'get_mr_detail', args: {mr: name}}).then((r) => {
            const d = r.message; if (!d || !state.data) return;
            const i = state.data.rows.findIndex((x) => x.name === name);
            if (i >= 0) state.data.rows[i] = d.row;
            if (state.selected === name) state.detail = d;
            recount(); renderTiles(); renderTable(); renderDetail();
        });
    }

    function recount() {
        const s = {PENDING: 0, PARTIAL: 0, DISPATCHED: 0, CLOSED_RECENT: 0, return_pending: 0, red: 0, yellow: 0};
        state.data.rows.forEach((r) => {
            if (r.stage === 'CLOSED') s.CLOSED_RECENT++; else if (s[r.stage] != null) s[r.stage]++;
            if ((r.flags || []).includes('return_blocks_close')) s.return_pending++;
        });
        state.data.summary = s;
    }

    // Actions reuse the single dialog implementations in material_request.js. The server endpoints stay the real gate.
    let busy = false;
    function act(kind, name) {
        if (busy) return;
        const sig = window.sig_wh || {};
        const fn = {issue: sig.open_mr_dispatch, return: sig.open_mr_return, cancel: sig.open_mr_cancel}[kind];
        if (!fn) { frappe.msgprint(__('Dispatch module still loading - try again in a moment.')); return; }
        const done = () => refreshOne(name);
        if (kind === 'return') { fn(name, done); return; }
        busy = true;
        frappe.call({method: 'frappe.client.get', args: {doctype: 'Material Request', name}}).then((r) => {
            busy = false;
            if (kind === 'issue') fn({doc: r.message, reload_doc: done}); else fn(r.message, done);
        }, () => { busy = false; });
    }

    function serverMessage(err) {
        try {
            const raw = err && err.responseJSON && err.responseJSON._server_messages;
            const msgs = raw ? JSON.parse(raw).map((m) => JSON.parse(m).message) : [];
            if (msgs.length) return frappe.utils.html2text(msgs.join(' '));
        } catch (e) { /* fall through */ }
        return __('Could not load the Dispatch Queue.');
    }

    function load() {
        const id = ++state.loadId;
        state.status = 'loading'; renderTable();
        frappe.call({method: API + 'get_queue', args: {include_closed: state.includeClosed ? 1 : 0}, silent: true}).then((r) => {
            if (id !== state.loadId) return;
            state.data = r.message; state.status = 'ready';
            renderFilters(); renderTiles(); renderTable(); renderDetail();
        }, (err) => {
            if (id !== state.loadId) return;
            state.status = 'error'; state.error = serverMessage(err);
            renderTable();
        });
    }

    shell(); renderTiles(); renderDetail(); load();
};
