// Site Visits (V0, read-only). See docs/site_visits_page_design.md.
// Same client pattern as project-progress: one shell, server does the filtering,
// row click opens a side panel with the original WhatsApp timeline + cycle context.
frappe.pages['site-visits'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Site Visits'), single_column: true});
    $(wrapper).find('.page-head').hide();
    const root = $('<div class="sig-sv-page"></div>').appendTo(page.main);
    const nav = $('<header class="sig-ops-header"><div class="sig-ops-brand"><span>SIG OPERATIONS</span><h1>Site Visits</h1></div><nav class="sig-ops-nav" aria-label="Operations"><button type="button" data-route="projects">Projects</button><button type="button" data-route="cycles">Site Cycles</button><button type="button" class="active" aria-current="page">Site Visits</button><button type="button" data-route="planner">Field Planner</button></nav><button type="button" class="sig-ops-refresh">' + __('Refresh') + '</button></header>');
    page.main.prepend(nav);
    nav.find('[data-route="projects"]').on('click', () => frappe.set_route('List', 'Project'));
    nav.find('[data-route="cycles"]').on('click', () => frappe.set_route('site-cycles'));
    nav.find('[data-route="planner"]').on('click', () => frappe.set_route('field-planner'));
    nav.find('.sig-ops-refresh').on('click', () => load());
    const state = {stream: '', site: '', person: '', status: '', view: 'current', search: '', selected: null, period: 'week', anchor: frappe.datetime.get_today(), dateFrom: '', dateTo: ''};
    let movement = null, movementRequest = 0;
    const esc = (v) => frappe.utils.escape_html(String(v || ''));
    const dt = (v) => {
        if (!v) return '—';
        const parts = String(v).slice(0, 19).split(/[- :]/);
        if (parts.length < 5) return String(v).slice(0, 16);
        return `${parts[2]}-${parts[1]}-${parts[0].slice(-2)} ${parts[3]}:${parts[4]}`;
    };
    const timeOnly = (v) => v ? String(v).slice(11, 16) : '';

    function shell() {
        root.html(`<div class="sig-sv-toolbar">
            <label class="sig-sv-field">${__('View')}<select class="sig-sv-view form-control">
                <option value="current">${__('Current')}</option><option value="today">${__('Today')}</option>
                <option value="open">${__('Open now')}</option><option value="review">${__('Needs review')}</option>
                <option value="unclassified">${__('Unclassified')}</option><option value="thisweek">${__('Sites this week')}</option>
                <option value="history">${__('History')}</option>
            </select></label>
            <label class="sig-sv-field">${__('Stream')}<select class="sig-sv-stream form-control"><option value="">${__('All')}</option></select></label>
            <label class="sig-sv-field" style="min-width:200px">${__('Site or employee')}<input class="sig-sv-search form-control" placeholder="${__('Search site or ERP employee name')}"></label>
            <button type="button" class="btn btn-default btn-sm sig-sv-log-missing" style="align-self:flex-end">${__('Log missing visit')}</button>
        </div>
        <div class="sig-sv-summary"></div>
        <section class="sig-movement"><div class="sig-movement-head"><div><h3>${__('Team movement')}</h3><span class="text-muted small">${__('Recorded visits in order; lines do not show actual roads.')}</span></div><div class="sig-movement-controls"><select class="form-control sig-movement-period" aria-label="${__('Period')}"><option value="week">${__('Week')}</option><option value="month">${__('Month')}</option></select><input type="date" class="form-control sig-movement-anchor" aria-label="${__('Date in period')}"><button type="button" class="btn btn-default sig-movement-all">${__('All people')}</button></div></div><div class="sig-movement-leaders"></div><div class="sig-movement-map"></div><div class="sig-movement-note"></div></section>
        <div class="sig-sv-list-limit text-muted small" hidden></div><div class="sig-sv-main"><div class="sig-sv-table-wrap"></div><aside class="sig-sv-detail"><div class="text-muted text-center" style="padding:40px 10px">${__('Select a visit to see its WhatsApp timeline and site context.')}</div></aside></div>`);
        root.find('.sig-sv-view').on('change', function () { state.view = this.value; load(); });
        root.find('.sig-sv-stream').on('change', function () { state.stream = this.value; load(); });
        root.find('.sig-sv-search').on('input', frappe.utils.debounce(function () { state.search = this.value; load(); }, 250));
        root.find('.sig-sv-log-missing').on('click', openLogMissingDialog);
        root.find('.sig-movement-anchor').val(state.anchor).on('change', function () { if (this.value) { state.anchor = this.value; loadMovement(); } });
        root.find('.sig-movement-period').on('change', function () { state.period = this.value; loadMovement(); });
        root.find('.sig-movement-all').on('click', () => { state.person = ''; drawMovement(); load(); });
        root.find('.sig-movement-leaders').on('click', 'button[data-person]', function () { state.person = $(this).attr('data-person'); drawMovement(); load(); });
        // Delegated: the tiles are re-rendered on every load(), so bind once on the
        // static parent rather than re-binding (and leaking listeners) after each render.
        root.find('.sig-sv-summary').on('click', '.sig-sv-tile', function () {
            state.view = $(this).data('view');
            load();
        });
    }

    const ACTIVITIES = ['UNSPECIFIED', 'SURVEY', 'INSTALL', 'HANDOVER', 'WARRANTY', 'DISMANTLE', 'SNAG'];

    function call(method, args, freeze_message) {
        return new Promise((resolve) => {
            frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.' + method, args, freeze: true,
                freeze_message: freeze_message || __('Working...'),
                callback: (r) => resolve(r.message || {}),
                error: () => resolve({result: 'exception', reason: 'request failed'})});
        });
    }

    function reportResult(res, okMessage) {
        if (res.result === 'ok' || res.result === 'created' || res.result === 'duplicate') {
            frappe.show_alert({message: okMessage || __('Done'), indicator: 'green'});
            return true;
        }
        frappe.msgprint({title: __('Failed'), indicator: 'red', message: esc(res.reason || JSON.stringify(res))});
        return false;
    }

    function openLogMissingDialog() {
        const d = new frappe.ui.Dialog({
            title: __('Log a Visit the Team Never Messaged'),
            fields: [
                {fieldtype: 'Link', fieldname: 'site', label: __('Site'), options: 'SIG Site', reqd: 1},
                {fieldtype: 'Link', fieldname: 'employee', label: __('Employee'), options: 'Employee', reqd: 1},
                {fieldtype: 'Column Break'},
                {fieldtype: 'Datetime', fieldname: 'start_at', label: __('Start'), reqd: 1},
                {fieldtype: 'Datetime', fieldname: 'end_at', label: __('End'), reqd: 1},
                {fieldtype: 'Section Break'},
                {fieldtype: 'Select', fieldname: 'activity_code', label: __('Type'), options: ACTIVITIES.join('\n'), default: 'UNSPECIFIED'},
                {fieldtype: 'Data', fieldname: 'scope', label: __('Scope (free text)')},
                {fieldtype: 'Small Text', fieldname: 'reason', label: __('Why was this not messaged?'), reqd: 1},
            ],
            primary_action_label: __('Log Visit'),
            primary_action: async (values) => {
                const res = await call('log_visit', values, __('Logging visit...'));
                if (reportResult(res, __('Visit logged and posted.'))) { d.hide(); load(); }
            },
        });
        d.show();
    }

    function summaryHtml(s) {
        const tile = (label, n, view) => `<div class="sig-sv-tile" data-view="${view}"><div class="sig-sv-tile-n">${n}</div><div class="sig-sv-tile-l">${__(label)}</div></div>`;
        return tile('Open now', s.open_now, 'open') + tile('Visits today', s.visits_today, 'today')
            + tile('Needs review', s.needs_review, 'review') + tile('Sites this week', s.sites_this_week, 'thisweek');
    }

    function statusBadge(row) {
        if (row.is_review) return `<span class="indicator-pill red">${__('Review')}</span>`;
        if (row.status === 'OPEN') return `<span class="indicator-pill blue">${__('Open')}</span>`;
        if (row.status === 'AUTO_CLOSED') return `<span class="indicator-pill orange">${__('Auto-closed')}</span>`;
        if (row.posted) return `<span class="indicator-pill green">${__('Posted')}</span>`;
        return `<span class="indicator-pill grey">${__('Pending')}</span>`;
    }

    function rowHtml(row) {
        const when = `${dt(row.start_at)}${row.end_at ? '–' + timeOnly(row.end_at) : ''}`;
        const siteLabel = row.site_linked ? row.site : (row.site || __('Unresolved site'));
        const description = row.activity_code && row.activity_code !== 'UNSPECIFIED' ? row.activity_code : '—';
        const minutes = row.hours != null ? Math.round(Number(row.hours) * 60) + ' ' + __('min') : '—';
        return `<tr class="sig-sv-row" tabindex="0" data-name="${esc(row.name)}">
            <td><b class="sig-sv-site">${esc(siteLabel)}</b><br><span class="text-muted small">${esc(description)}</span></td>
            <td>${esc(row.reporter_name)}<br><span class="text-muted small">${when}</span></td>
            <td>${minutes}<br><span class="text-muted small">${row.photo_count} ${__('Pics')}</span></td>
            <td>${statusBadge(row)}</td>
        </tr>`;
    }

    function renderTable(payload) {
        lastPayload = payload;
        root.find('.sig-sv-list-limit').prop('hidden', !payload.truncated).text(payload.truncated ? __('Visit list is limited to the 500 most recent matches; narrow the filters to see earlier visits.') : '');
        const sel = root.find('.sig-sv-stream').empty().append(`<option value="">${__('All')}</option>`);
        (payload.streams || []).forEach((s) => sel.append($('<option></option>').val(s.value).text(s.label)));
        sel.val(state.stream);
        root.find('.sig-sv-view').val(state.view);
        root.find('.sig-sv-search').val(state.search);
        root.find('.sig-sv-summary').html(summaryHtml(payload.summary || {}));
        const wrap = root.find('.sig-sv-table-wrap');
        if (!payload.rows || !payload.rows.length) {
            wrap.html(`<div class="text-muted text-center" style="padding:30px">${__('No visits in this view.')}</div>`);
            return;
        }
        wrap.html(`<table class="table table-bordered sig-sv-table">
            <thead><tr><th>${__('Site / Description')}</th><th>${__('Person · When')}</th><th>${__('Duration · Pics')}</th><th>${__('Status')}</th></tr></thead>
            <tbody>${payload.rows.map(rowHtml).join('')}</tbody></table>`);
        wrap.find('.sig-sv-row').on('click keydown', function (e) { if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return; e.preventDefault(); state.selected = $(this).data('name'); wrap.find('.sig-sv-row').removeClass('selected'); $(this).addClass('selected'); root.find('.sig-sv-detail').removeClass('is-closed').addClass('is-open'); showDetail(state.selected); });
    }

    function showDetail(name) {
        const panel = root.find('.sig-sv-detail');
        panel.html(`<div class="text-muted text-center" style="padding:30px">${__('Loading...')}</div>`);
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visit', args: {session_key: name}, callback: (r) => {
            if (state.selected !== name) return;
            const d = r.message || {};
            if (d.result !== 'ok') { panel.html(`<div class="text-muted">${__('Not found.')}</div>`); return; }
            const cyc = d.cycle;
            const cycleHtml = cyc ? `<b>${esc(cyc.project || '')}</b> · ${esc(cyc.stage || '')}${cyc.wo ? ' · ' + esc(cyc.wo) : ''}<br>
                <span class="text-muted small">${__('Visits so far')}: ${cyc.sessions_completed || 0}, ${__('first')} ${dt(cyc.first_visit_at)}, ${__('last')} ${dt(cyc.last_visit_at)}</span>` : `<span class="text-muted">${__('No posted cycle link for this session.')}</span>`;
            const timelineHtml = (d.timeline || []).map((m) => `<div class="sig-sv-msg"><span class="text-muted small">${timeOnly(m.at)}</span> <b>${esc(m.who)}</b> <span class="indicator-pill ${m.kind === 'START' ? 'blue' : m.kind === 'END' ? 'green' : 'grey'}" style="font-size:10px">${m.kind}</span>${m.text ? ' — ' + esc(m.text) : ''}</div>`).join('') || `<div class="text-muted small">${__('No stored messages.')}</div>`;
            const priorHtml = (d.prior_visits || []).map((p) => `<div class="small">${dt(p.start_at)} · ${esc(p.reporter_name)} · ${esc(p.status)}</div>`).join('') || `<div class="text-muted small">${__('None.')}</div>`;
            const commentsHtml = (d.comments || []).map((c) => `<div class="small" style="margin-bottom:4px"><b>${esc(c.by)}</b> <span class="text-muted">${dt(c.at)}</span><br>${esc(c.content)}</div>`).join('') || `<div class="text-muted small">${__('No notes yet.')}</div>`;
            const row = (lastPayload.rows || []).find((r) => r.name === name) || {};
            panel.html(`<div class="sig-sv-detail-head"><div><small>${__('Visit details')}</small><h3>${esc(row.site || __('Unresolved site'))}</h3>${statusBadge(row)}</div><button type="button" class="sig-sv-detail-close" aria-label="${__('Close details')}">×</button></div><div class="sig-sv-detail-summary"><div><small>${__('Person')}</small><b>${esc(row.reporter_name)}</b></div><div><small>${__('When')}</small><b>${dt(row.start_at)}${row.end_at ? '–' + timeOnly(row.end_at) : ''}</b></div><div><small>${__('Pics')}</small><b>${row.photo_count || 0}</b></div></div><h5>${__('Description')}</h5><div class="sig-sv-block">${esc(row.activity_code && row.activity_code !== 'UNSPECIFIED' ? row.activity_code : '—')}</div><h5>${__('Cycle and status')}</h5><div class="sig-sv-block">${cycleHtml}${(row.diagnostics || []).length ? '<br>' + esc(row.diagnostics.join(', ')) : ''}</div>
                <h5>${__('WhatsApp timeline')}</h5><div class="sig-sv-block sig-sv-timeline">${timelineHtml}</div>
                <details><summary>${__('Other visits at this site')}</summary><div class="sig-sv-block">${priorHtml}</div></details>
                <h5>${__('Actions')}</h5><div class="sig-sv-actions"></div>
                <h5>${__('Notes')}</h5><div class="sig-sv-block">${commentsHtml}</div>
                <textarea class="form-control sig-sv-note-text" rows="2" placeholder="${__('Add a note...')}"></textarea>
                <button type="button" class="btn btn-default btn-sm sig-sv-add-note" style="margin-top:6px">${__('Add note')}</button>`);
            panel.find('.sig-sv-detail-close').on('click', () => panel.removeClass('is-open').addClass('is-closed'));
            renderActions(row, name, d.cycle_candidates || []);
            panel.find('.sig-sv-add-note').on('click', async () => {
                const content = panel.find('.sig-sv-note-text').val().trim();
                if (!content) return;
                const res = await call('add_note', {session_key: name, content});
                if (reportResult(res, __('Note added.'))) showDetail(name);
            });
        }});
    }

    let lastPayload = {rows: []};

    function renderActions(row, name, cycleCandidates) {
        const box = root.find('.sig-sv-detail .sig-sv-actions');
        const btn = (label, cls) => `<button type="button" class="btn btn-default btn-xs ${cls}" style="margin:2px">${label}</button>`;
        const unallocated = row.posted && (row.diagnostics || []).includes('UNALLOCATED');
        if (row.posted && !unallocated) { box.html(`<span class="text-muted small">${__('Already posted - corrections go through an amendment on the Field Visit itself.')}</span>`); return; }
        const pairBtn = row.status !== 'COMPLETED' ? btn(__('Pair a lonely End'), 'sig-sv-act-pair') : '';
        const attributionReview = (row.diagnostics || []).includes('CYCLE_ATTRIBUTION_EXCEPTION');
        const confirmBtn = row.is_review && !attributionReview ? btn(__('Confirm as-is'), 'sig-sv-act-confirm') : '';
        const cycleBtn = unallocated ? btn(__('Attach to a cycle'), 'sig-sv-act-cycle')
            : (attributionReview && row.status === 'COMPLETED' ? btn(__('Select cycle and post'), 'sig-sv-act-cycle') : '');
        box.html(unallocated
            ? `<span class="text-muted small">${__('Visit recorded without a cycle.')}</span><br>` + cycleBtn
            : cycleBtn + btn(__('Set type / scope'), 'sig-sv-act-type') + btn(__('Fix site'), 'sig-sv-act-site')
              + btn(__('Assign person'), 'sig-sv-act-assign') + pairBtn + confirmBtn + btn(__('Void'), 'sig-sv-act-void'));
        if (cycleBtn) box.find('.sig-sv-act-cycle').on('click', () => {
            if (!cycleCandidates.length) {
                frappe.msgprint({title: __('No open cycle'), message: __('This site has no open cycle to attach the visit to.')});
                return;
            }
            const opts = cycleCandidates.map((c) => ({
                label: `${c.project || c.erp_project || __('Project unavailable')} · ${c.po || __('No PO')} · ${c.wo || __('No WO')} · ${c.stage || ''}`,
                value: c.name,
            }));
            const d2 = new frappe.ui.Dialog({title: __('Select the Correct Open Cycle'), fields: [
                {fieldtype: 'Select', fieldname: 'cycle_name', label: __('Site / PO / WO cycle'),
                 options: opts.map((o) => o.value).join('\n'), reqd: 1}],
                primary_action_label: __('Post to Cycle'), primary_action: async (v) => {
                    const res = await call('post_to_cycle', {session_key: name, cycle_name: v.cycle_name}, __('Posting visit...'));
                    if (reportResult(res, __('Visit posted to the selected cycle.'))) {
                        d2.hide(); load(); showDetail(name);
                    }
                }});
            d2.show();
            const $sel = d2.fields_dict.cycle_name.$input;
            opts.forEach((o, i) => $sel.find('option').eq(i).text(o.label));
        });
        if (confirmBtn) box.find('.sig-sv-act-confirm').on('click', () => {
            frappe.prompt({fieldtype: 'Small Text', fieldname: 'note', label: __('Note (optional)')}, async (v) => {
                const res = await call('confirm', {session_key: name, note: v.note});
                if (reportResult(res, __('Confirmed.'))) { load(); showDetail(name); }
            }, __('Confirm This Session As-Is'), __('Confirm'));
        });
        box.find('.sig-sv-act-type').on('click', () => {
            const d2 = new frappe.ui.Dialog({title: __('Set Type / Scope'), fields: [
                {fieldtype: 'Select', fieldname: 'activity_code', label: __('Type'), options: ACTIVITIES.join('\n'), default: row.activity_code || 'UNSPECIFIED'},
                {fieldtype: 'Data', fieldname: 'scope', label: __('Scope (free text)')}],
                primary_action_label: __('Save'), primary_action: async (v) => {
                    const res = await call('set_type', {session_key: name, activity_code: v.activity_code, scope: v.scope});
                    if (reportResult(res, __('Updated.'))) { d2.hide(); load(); showDetail(name); }
                }});
            d2.show();
        });
        box.find('.sig-sv-act-site').on('click', () => {
            const d2 = new frappe.ui.Dialog({title: __('Fix Site'), fields: [
                {fieldtype: 'Data', fieldname: 'site', label: __('Correct Site Code'), reqd: 1, default: row.site},
                {fieldtype: 'Check', fieldname: 'create', label: __('Create this site if it does not exist')}],
                primary_action_label: __('Save'), primary_action: async (v) => {
                    const res = await call('fix_site', {session_key: name, site: v.site, create: v.create ? 1 : 0});
                    if (reportResult(res, __('Site fixed.'))) { d2.hide(); load(); showDetail(name); }
                }});
            d2.show();
        });
        box.find('.sig-sv-act-void').on('click', () => {
            frappe.prompt({fieldtype: 'Small Text', fieldname: 'reason', label: __('Reason'), reqd: 1}, async (v) => {
                const res = await call('void', {session_key: name, reason: v.reason});
                if (reportResult(res, __('Voided.'))) { load(); root.find('.sig-sv-detail').html(''); }
            }, __('Void This Session'), __('Void'));
        });
        box.find('.sig-sv-act-assign').on('click', () => {
            const d2 = new frappe.ui.Dialog({title: __('Assign Person'), fields: [
                {fieldtype: 'Data', fieldname: 'reporter_phone', label: __('Reporter Phone'), default: row.reporter, read_only: 1},
                {fieldtype: 'Data', fieldname: 'reporter_name_seen', label: __('Name Seen on WhatsApp'), default: row.whatsapp_name || row.reporter_name, read_only: 1},
                {fieldtype: 'Link', fieldname: 'employee', label: __('Employee'), options: 'Employee', reqd: 1, default: row.employee}],
                primary_action_label: __('Save'), primary_action: async (v) => {
                    const res = await call('assign_person', {reporter_phone: v.reporter_phone, employee: v.employee,
                        reporter_name_seen: v.reporter_name_seen}, __('Assigning...'));
                    if (reportResult(res, __('Assigned ({0} session(s) updated).', [res.sessions_updated]))) {
                        d2.hide(); load(); showDetail(name);
                    }
                }});
            d2.show();
        });
        if (pairBtn) box.find('.sig-sv-act-pair').on('click', async () => {
            const ends = await call('list_unpaired_ends', {site_key: row.site});
            if (!Array.isArray(ends) || !ends.length) {
                frappe.msgprint({title: __('No candidates'), message: __('No unpaired End messages found for this site.')});
                return;
            }
            const opts = ends.map((e) => ({label: `${e.at.slice(0, 16)} - ${e.who} (${e.diagnostic})`, value: e.msg_key}));
            const d2 = new frappe.ui.Dialog({title: __('Pair a Lonely End'), fields: [
                {fieldtype: 'Select', fieldname: 'end_msg', label: __('End Message'),
                 options: opts.map((o) => o.value).join('\n'), reqd: 1}],
                primary_action_label: __('Pair'), primary_action: async (v) => {
                    const res = await call('pair_end', {end_msg: v.end_msg, session_key: name});
                    if (reportResult(res, __('Paired ({0}h).', [res.hours]))) { d2.hide(); load(); showDetail(name); }
                }});
            // Select field shows raw values; swap in readable labels post-render.
            d2.show();
            const $sel = d2.fields_dict.end_msg.$input;
            opts.forEach((o, i) => $sel.find('option').eq(i).text(o.label));
        });
    }

    async function loadMovement() {
        const id = ++movementRequest;
        root.find('.sig-movement-map').text(__('Loading movement…'));
        try {
            await frappe.require('/assets/sig_warehouse/js/sig_movement_map_assets.js');
            const response = await frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_movement_map', args: {period: state.period, anchor: state.anchor}});
            if (id !== movementRequest) return;
            movement = response.message;
            if (!movement) throw new Error('No movement data');
            state.dateFrom = movement.start; state.dateTo = movement.end;
            drawMovement(); load();
        } catch (error) {
            if (id === movementRequest) root.find('.sig-movement-map').text(__('Movement map could not be loaded.'));
        }
    }

    function drawMovement() {
        if (!movement) return;
        const asset = window.sigMovementMapAssets, colors = asset.colors;
        const teams = movement.teams || [], visits = movement.visits || [];
        const labels = new Map(teams.map((t, i) => [t.id, {label: t.label, color: colors[i % colors.length], leader: t.leader}]));
        const people = new Map();
        teams.forEach((t, i) => people.set(t.leader, {name: t.label, color: colors[i % colors.length]}));
        visits.forEach(v => { if (v.employee && !people.has(v.employee)) people.set(v.employee, {name: v.person || v.employee, color: '#748594'}); });
        root.find('.sig-movement-leaders').html([...people].map(([id, p]) => `<button type="button" data-person="${esc(id)}" class="sig-movement-person ${state.person === id ? 'active' : ''}"><span style="background:${p.color}"></span>${esc(p.name)}</button>`).join(''));
        const shown = visits.filter(v => !state.person || v.employee === state.person);
        const outline = asset.outline.map(([lon, lat]) => asset.project(lon, lat).join(',')).join(' ');
        const runs = new Map();
        shown.forEach(v => { const key = (v.employee || v.name) + '|' + v.at.slice(0, 10); if (!runs.has(key)) runs.set(key, []); runs.get(key).push(v); });
        let lines = '', dots = '';
        runs.forEach(group => {
            for (let i = 1; i < group.length; i++) {
                const a = group[i - 1], b = group[i];
                if (a.lat == null || b.lat == null || a.lon == null || b.lon == null) continue;
                const color = (labels.get(b.team) || {}).color || '#748594';
                const [x1,y1] = asset.project(a.lon,a.lat), [x2,y2] = asset.project(b.lon,b.lat);
                lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="2" opacity=".8"/>`;
            }
            group.forEach((v, index) => {
                if (v.lat == null || v.lon == null) return;
                const [x,y] = asset.project(v.lon,v.lat), color = (labels.get(v.team) || {}).color || '#748594';
                dots += `<g><circle cx="${x}" cy="${y}" r="6" fill="${color}" stroke="white" stroke-width="1.5"/><text x="${x}" y="${y+2}" font-size="6" text-anchor="middle" fill="white">${index+1}</text><title>${esc(v.site)} · ${esc(v.person)} · ${esc(v.at.slice(0,16))}</title></g>`;
            });
        });
        root.find('.sig-movement-map').html(`<svg viewBox="20 35 830 760" role="img" aria-label="${__('Recorded visit movement')}"><rect x="20" y="35" width="830" height="760" fill="#e9f1f7"/><polygon points="${outline}" fill="#f8faf9" stroke="#9db4c9" stroke-width="1.5"/>${lines}${dots}</svg>`);
        const missing = shown.filter(v => v.lat == null || v.lon == null).length;
        root.find('.sig-movement-note').text(`${movement.start} – ${movement.end} · ${shown.length} ${__('visits')} · ${missing} ${__('without map coordinates')}${movement.truncated ? ' · ' + __('Results limited to 10,000 visits') : ''}`);
    }

    let latestLoad = 0;
    function load() {
        const requestId = ++latestLoad;
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visits',
            args: {stream: state.stream, site: state.site, person: state.person, status: state.status,
                   view: state.view, search: state.search, date_from: state.dateFrom, date_to: state.dateTo},
            callback: (r) => { if (requestId === latestLoad && r.message) renderTable(r.message); }});
    }

    shell();
    loadMovement();
};
