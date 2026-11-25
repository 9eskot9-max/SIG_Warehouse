// Site Visits (V0, read-only). See docs/site_visits_page_design.md.
// Same client pattern as project-progress: one shell, server does the filtering,
// Row click opens a concise detail panel with the linked cycle and actions.
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
    const state = {stream: '', site: '', person: '', status: '', view: 'current', search: '', selected: null, period: 'week', anchor: frappe.datetime.get_today(), dateFrom: '', dateTo: '', historyFrom: '', historyTo: ''};
    let movement = null, movementRequest = 0, highlightedVisit = null, focusRequest = 0;
    const mapView = {box: [20, 35, 830, 760], towns: true, zones: true, zoneCells: null, base: 'drawing', leaflet: null, roadView: null};
    const esc = (v) => frappe.utils.escape_html(String(v || ''));
    const dt = (v) => {
        if (!v) return '—';
        const parts = String(v).slice(0, 19).split(/[- :]/);
        if (parts.length < 5) return String(v).slice(0, 16);
        return `${parts[2]}-${parts[1]}-${parts[0].slice(-2)} ${parts[3]}:${parts[4]}`;
    };
    const timeOnly = (v) => v ? String(v).slice(11, 16) : '';
    const WEEKDAYS = [__('Mon'), __('Tue'), __('Wed'), __('Thu'), __('Fri'), __('Sat'), __('Sun')];
    const MONTHS = [__('Jan'), __('Feb'), __('Mar'), __('Apr'), __('May'), __('Jun'), __('Jul'), __('Aug'), __('Sep'), __('Oct'), __('Nov'), __('Dec')];
    function visitDateTime(start, end) {
        const date = String(start || '').slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (!date) return `<span class="sig-sv-visit-time">${esc(dt(start))}${end ? ' – ' + esc(timeOnly(end)) : ''}</span>`;
        const weekday = (new Date(Date.UTC(Number(date[1]), Number(date[2]) - 1, Number(date[3]))).getUTCDay() + 6) % 7;
        const dateLabel = `${date[3]} ${MONTHS[Number(date[2]) - 1]} ${date[1]}`;
        const timeLabel = `${timeOnly(start)}${end ? ' – ' + timeOnly(end) : ''}`;
        return `<span class="sig-sv-day sig-sv-day-${weekday}" data-weekday="${weekday}">${WEEKDAYS[weekday]} · ${esc(dateLabel)}</span><span class="sig-sv-visit-time">${esc(timeLabel)}</span>`;
    }
    function familyLabel(value) {
        const raw = String(value || '').toLowerCase();
        if (raw.includes('capex')) return __('Capex');
        if (raw.includes('incident')) return __('Incident');
        if (raw.includes('colo') || raw.includes('5g')) return __('Colocation');
        return '';
    }

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
            <label class="sig-sv-field sig-sv-history-date" hidden>${__('From')}<input type="date" class="sig-sv-history-from form-control"></label>
            <label class="sig-sv-field sig-sv-history-date" hidden>${__('To')}<input type="date" class="sig-sv-history-to form-control"></label>
            <button type="button" class="btn btn-default btn-sm sig-sv-log-missing" style="align-self:flex-end">${__('Log missing visit')}</button>
        </div>
        <div class="sig-sv-summary"></div>
        <section class="sig-movement"><div class="sig-movement-head"><div><h3>${__('Team movement')}</h3></div><div class="sig-movement-controls"><select class="form-control sig-movement-period" aria-label="${__('Period')}"><option value="week">${__('Week')}</option><option value="month">${__('Month')}</option></select><input type="date" class="form-control sig-movement-anchor" aria-label="${__('Date in period')}"><button type="button" class="btn btn-default sig-movement-all">${__('All people')}</button></div></div><div class="sig-movement-leaders"></div><div class="sig-movement-tools"><button type="button" class="btn btn-default btn-xs" data-movement="drawing" aria-pressed="true">${__('Drawing')}</button><button type="button" class="btn btn-default btn-xs" data-movement="road" aria-pressed="false">${__('Road map')}</button><button type="button" class="btn btn-default btn-xs" data-movement="towns" aria-pressed="true">${__('Town references')}</button><button type="button" class="btn btn-default btn-xs" data-movement="zones" aria-pressed="true">${__('Planning zones')}</button><button type="button" class="btn btn-default btn-xs" data-movement="in" aria-label="${__('Zoom in')}">+</button><button type="button" class="btn btn-default btn-xs" data-movement="out" aria-label="${__('Zoom out')}">−</button><button type="button" class="btn btn-default btn-xs" data-movement="reset">${__('Reset map')}</button><button type="button" class="btn btn-default btn-xs" data-movement="fit">${__('Focus selection')}</button><input class="form-control sig-movement-search" placeholder="${__('Find site')}" aria-label="${__('Find site on map')}"><button type="button" class="btn btn-default btn-xs" data-movement="find">${__('Find')}</button><button type="button" class="btn btn-default btn-xs" data-movement="expand">${__('Expand map')}</button></div><div class="sig-movement-map-wrap"><div class="sig-movement-map"></div><div class="sig-movement-sitebox"></div></div><div class="sig-movement-note"></div></section>
        <div class="sig-sv-active-filter"></div><div class="sig-sv-list-limit text-muted small" hidden></div><div class="sig-sv-main"><div class="sig-sv-table-wrap"></div><aside class="sig-sv-detail"><div class="text-muted text-center" style="padding:40px 10px">${__('Select a visit to see its details.')}</div></aside></div>`);
        root.find('.sig-sv-view').on('change', function () { state.view = this.value; load(); });
        root.find('.sig-sv-history-from, .sig-sv-history-to').on('change', function () { state.historyFrom = root.find('.sig-sv-history-from').val(); state.historyTo = root.find('.sig-sv-history-to').val(); load(); });
        root.find('.sig-sv-stream').on('change', function () { state.stream = this.value; load(); });
        root.find('.sig-sv-search').on('input', frappe.utils.debounce(function () { state.search = this.value; load(); }, 250));
        root.find('.sig-sv-log-missing').on('click', openLogMissingDialog);
        root.find('.sig-movement-anchor').val(state.anchor).on('change', function () { if (this.value) { state.anchor = this.value; loadMovement(); } });
        root.find('.sig-movement-period').on('change', function () { state.period = this.value; loadMovement(); });
        root.find('.sig-movement-all').on('click', () => { state.person = ''; mapView.box = [20,35,830,760]; drawMovement(); load(); });
        root.find('.sig-movement-tools').on('click', '[data-movement]', function () { movementControl($(this).attr('data-movement')); });
        root.find('.sig-movement-search').on('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); movementControl('find'); } });
        root.find('.sig-movement').on('keydown', function (e) { if (e.key === 'Escape' && $(this).hasClass('is-expanded')) movementControl('expand'); });
        root.find('.sig-movement-leaders').on('click', 'button[data-person]', function () { state.person = $(this).attr('data-person'); mapView.box = [20,35,830,760]; drawMovement(); load(); });
        // Delegated: the tiles are re-rendered on every load(), so bind once on the
        // static parent rather than re-binding (and leaking listeners) after each render.
        root.find('.sig-sv-summary').on('click', '.sig-sv-tile', function () {
            state.view = $(this).data('view');
            load();
        });
    }

    const ACTIVITIES = ['UNSPECIFIED', 'SURVEY', 'INSTALL', 'HANDOVER', 'WARRANTY', 'DISMANTLE', 'SNAG', 'PAT'];

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
            + tile('Needs review', s.needs_review, 'review') + tile('Sites in period', s.sites_in_period, 'current');
    }

    function statusBadge(row) {
        if (row.is_review) return `<span class="indicator-pill red">${__('Review')}</span>`;
        if (row.status === 'OPEN') return `<span class="indicator-pill blue">${__('Open')}</span>`;
        if (row.status === 'AUTO_CLOSED') return `<span class="indicator-pill orange">${__('Auto-closed')}</span>`;
        if (row.posted) return `<span class="indicator-pill green">${__('Posted')}</span>`;
        return `<span class="indicator-pill grey">${__('Pending')}</span>`;
    }

    function rowHtml(row) {
        const when = visitDateTime(row.start_at, row.end_at);
        const siteLabel = row.site_linked ? row.site : (row.site || __('Unresolved site'));
        const description = [familyLabel(row.project_family), row.activity_code && row.activity_code !== 'UNSPECIFIED' ? row.activity_code : ''].filter(Boolean).join(' · ') || '—';
        const minutes = row.hours != null ? Math.round(Number(row.hours) * 60) + ' ' + __('min') : '—';
        return `<tr class="sig-sv-row" tabindex="0" data-name="${esc(row.name)}">
            <td><b class="sig-sv-site">${esc(siteLabel)}</b><br><span class="text-muted small">${esc(description)}</span></td>
            <td>${esc(row.reporter_name)}<br><div class="sig-sv-when">${when}</div></td>
            <td>${minutes}<br><span class="text-muted small">${row.photo_count} ${__('Pics')}</span></td>
            <td>${statusBadge(row)}</td>
        </tr>`;
    }

    function renderTable(payload) {
        lastPayload = payload;
        const activePerson = movement && (movement.visits || []).find(v => v.employee === state.person);
        const activeTeam = movement && (movement.teams || []).find(t => t.leader === state.person);
        const personLabel = state.person ? ((activePerson && activePerson.person) || (activeTeam && activeTeam.label) || state.person) : __('All people');
        const viewLabel = root.find('.sig-sv-view option').filter(function () { return this.value === state.view; }).text() || __('Current');
        const listFrom = state.view === 'history' ? state.historyFrom : state.dateFrom;
        const listTo = state.view === 'history' ? state.historyTo : state.dateTo;
        const dateLabel = state.view === 'history' && !listFrom && !listTo ? __('All dates') : `${listFrom || '…'} – ${listTo || '…'}`;
        root.find('.sig-sv-active-filter').text(`${__('Visits')} · ${dateLabel} · ${personLabel} · ${viewLabel}`);
        root.find('.sig-sv-history-date').prop('hidden', state.view !== 'history');
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
        wrap.find('.sig-sv-row').on('click keydown', function (e) { if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return; e.preventDefault(); state.selected = $(this).data('name'); wrap.find('.sig-sv-row').removeClass('selected'); $(this).addClass('selected'); root.find('.sig-sv-detail').removeClass('is-closed').addClass('is-open'); showDetail(state.selected); focusVisitOnMap(state.selected); });
    }

    function showDetail(name) {
        const panel = root.find('.sig-sv-detail');
        panel.html(`<div class="text-muted text-center" style="padding:30px">${__('Loading...')}</div>`);
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visit', args: {session_key: name}, callback: (r) => {
            if (state.selected !== name) return;
            const d = r.message || {};
            if (d.result !== 'ok') { panel.html(`<div class="text-muted">${__('Not found.')}</div>`); return; }
            const row = (lastPayload.rows || []).find((r) => r.name === name) || {};
            const cyc = d.cycle;
            const cycleHtml = cyc ? `<button type="button" class="sig-sv-cycle-link">${esc(cyc.project || cyc.name)}</button>${cyc.stage ? ' · ' + esc(cyc.stage === '2 - Plan' ? __('2 - Execute') : cyc.stage) : ''}` : `<span class="text-muted">—</span>`;
            const project = familyLabel(d.project_family || row.project_family) || '—';
            const commentsHtml = (d.comments || []).map((c) => `<div class="small" style="margin-bottom:4px"><b>${esc(c.by)}</b> <span class="text-muted">${dt(c.at)}</span><br>${esc(c.content)}</div>`).join('') || `<div class="text-muted small">${__('No notes yet.')}</div>`;
            const endText = row.status === 'AUTO_CLOSED' ? __('Auto-closed; End not received') : (row.end_at ? dt(row.end_at) : '—');
            panel.html(`<div class="sig-sv-detail-head"><div><small>${__('Visit details')}</small><h3>${esc(row.site || __('Unresolved site'))}</h3>${statusBadge(row)}</div><button type="button" class="sig-sv-detail-close" aria-label="${__('Close details')}">×</button></div>
                <div class="sig-sv-detail-summary"><div><small>${__('Project')}</small><b>${esc(project)}</b></div><div><small>${__('Person')}</small><b>${esc(row.reporter_name)}</b></div><div><small>${__('Pics')}</small><b>${row.photo_count || 0}</b></div><div><small>${__('Start')}</small><b>${dt(row.start_at)}</b></div><div><small>${__('End')}</small><b>${esc(endText)}</b></div></div>
                <h5>${__('Description')}</h5><div class="sig-sv-block">${esc(row.activity_code && row.activity_code !== 'UNSPECIFIED' ? row.activity_code : '—')}</div>
                <h5>${__('Cycle')}</h5><div class="sig-sv-block">${cycleHtml}</div>
                ${(row.is_review && (row.diagnostics || []).length) ? `<details><summary>${__('Review details')}</summary><div class="sig-sv-block">${esc(row.diagnostics.join(', '))}</div></details>` : ''}
                <div class="sig-sv-actions"></div>
                <details><summary>${__('Notes')}</summary><div class="sig-sv-block">${commentsHtml}</div><textarea class="form-control sig-sv-note-text" rows="2" placeholder="${__('Add a note...')}"></textarea><button type="button" class="btn btn-default btn-sm sig-sv-add-note" style="margin-top:6px">${__('Add note')}</button></details>`);
            if (cyc) panel.find('.sig-sv-cycle-link').on('click', () => frappe.set_route('Form', 'SIG Site Cycle', cyc.name));
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
        if (row.posted && !unallocated) { box.empty(); return; }
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
        const asset = window.sigMovementMapAssets;
        const colors = ['#1261b1','#d34b00','#198442','#9b2e9f','#c51b51','#00818a','#ac7000','#4e4c9a','#0071ad','#b14378','#637b13','#bb4129','#4e726d','#925116','#6657bd','#a32c28','#00836b','#815795','#9a641e','#3c7194','#a83d68','#6e7c30','#875b48','#4f627e'];
        if (mapView.leaflet) { const c = mapView.leaflet.getCenter(); mapView.roadView = {center: [c.lat,c.lng], zoom: mapView.leaflet.getZoom()}; mapView.leaflet.remove(); mapView.leaflet = null; }
        const teams = movement.teams || [], visits = movement.visits || [];
        const shortName = name => { const parts = String(name || '').trim().split(/\s+/).filter(Boolean); return parts.length > 1 ? parts[0] + ' ' + parts[parts.length - 1] : (parts[0] || ''); };
        const people = new Map();
        const fixedPeople = ['HR-EMP-00067','HR-EMP-00045','HR-EMP-00014','HR-EMP-00005','HR-EMP-00008','HR-EMP-00019','HR-EMP-00021','HR-EMP-00025','HR-EMP-00026','HR-EMP-00031','HR-EMP-00010'];
        const colorFor = id => { const i = fixedPeople.indexOf(id); return i < 0 ? null : colors[i]; };
        const addPerson = (id, name) => { if (!id || people.has(id)) return; const used = new Set([...people.values()].map(p => p.color)); const color = colorFor(id) || colors.find((c, i) => i >= fixedPeople.length && !used.has(c)) || colors[people.size % colors.length]; people.set(id, {name, color}); };
        teams.forEach(t => addPerson(t.leader, t.label));
        visits.filter(v => v.employee && !people.has(v.employee)).sort((a,b) => a.employee.localeCompare(b.employee)).forEach(v => addPerson(v.employee, v.person || v.employee));
        const personColor = v => (people.get(v.employee) || {}).color || '#748594';
        root.find('.sig-movement-leaders').html([...people].map(([id, p]) => `<button type="button" data-person="${esc(id)}" class="sig-movement-person ${state.person === id ? 'active' : ''}"><span style="background:${p.color}"></span>${esc(shortName(p.name))}</button>`).join(''));
        const shown = visits.filter(v => !state.person || v.employee === state.person);
        const outline = asset.outline.map(([lon, lat]) => asset.project(lon, lat).join(',')).join(' ');
        const runs = new Map();
        shown.forEach(v => { const key = (v.employee || v.name) + '|' + v.at.slice(0, 10); if (!runs.has(key)) runs.set(key, []); runs.get(key).push(v); });
        let lines = '', dots = '';
        const towns = asset.towns || [], zoneColors = asset.zoneColors || {};
        if (!mapView.zoneCells && towns.length) { const points = towns.map(t => [...asset.project(t.lon, t.lat), t.zone]); let cells = ''; for (let x = 20; x < 850; x += 14) for (let y = 35; y < 795; y += 14) { let nearest = null, best = Infinity; points.forEach(p => { const d = (p[0]-x-7)**2 + (p[1]-y-7)**2; if (d < best) { best = d; nearest = p; } }); cells += `<rect x="${x}" y="${y}" width="14.5" height="14.5" fill="${zoneColors[nearest[2]] || '#eee'}"/>`; } mapView.zoneCells = cells; }
        const mainTowns = new Set(['Riyadh','Jeddah','Makkah','Madinah','Dammam','Taif','Tabuk','Buraydah','Abha','Hail','Najran','Jizan']);
        const townDots = mapView.towns ? towns.filter(t => mainTowns.has(t.name)).map(t => { const [x,y] = asset.project(t.lon,t.lat); return `<circle cx="${x}" cy="${y}" r="2.6" fill="#b7791f"/><text x="${x+4}" y="${y-3}" font-size="7" fill="#7a4e12">${esc(t.name)}</text>`; }).join('') : '';
        runs.forEach(group => {
            for (let i = 1; i < group.length; i++) {
                const a = group[i - 1], b = group[i];
                if (a.lat == null || b.lat == null || a.lon == null || b.lon == null) continue;
                const color = personColor(b);
                const [x1,y1] = asset.project(a.lon,a.lat), [x2,y2] = asset.project(b.lon,b.lat);
                lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="2" opacity=".8"/>`;
            }
            group.forEach((v, index) => {
                if (v.lat == null || v.lon == null) return;
                const [x,y] = asset.project(v.lon,v.lat), color = personColor(v);
                dots += `<g class="sig-movement-point ${highlightedVisit === v.name ? 'is-highlighted' : ''}" data-session="${esc(v.name)}" tabindex="0" role="button"><circle cx="${x}" cy="${y}" r="6" fill="${color}" stroke="white" stroke-width="1.5"/>${highlightedVisit === v.name ? `<circle class="sig-movement-highlight-ring" cx="${x}" cy="${y}" r="11" fill="none" stroke="#102f4c" stroke-width="3"/>` : ''}<text x="${x}" y="${y+2}" font-size="6" text-anchor="middle" fill="white">${index+1}</text><title>${esc(v.site)} · ${esc(v.person)} · ${esc(v.at.slice(0,16))}</title></g>`;
            });
        });
        if (mapView.base === 'road') { drawMovementRoad(shown, runs, personColor); root.find('.sig-movement-note').text(`${movement.start} – ${movement.end} · ${shown.length} ${__('visits')} · ${shown.filter(v => v.lat == null || v.lon == null).length} ${__('unmapped')}`); return; }
        root.find('.sig-movement-map').html(`<svg viewBox="${mapView.box.join(' ')}" role="img" aria-label="${__('Recorded visit movement')}"><defs><clipPath id="sig-movement-ksa"><polygon points="${outline}"/></clipPath></defs><rect x="20" y="35" width="830" height="760" fill="#e9f1f7"/><polygon points="${outline}" fill="#f8faf9"/><g clip-path="url(#sig-movement-ksa)">${mapView.zones ? mapView.zoneCells || '' : ''}</g><polygon points="${outline}" fill="none" stroke="#9db4c9" stroke-width="1.5"/>${townDots}${lines}${dots}</svg>`);
        bindMovementMap();
        setMovementBox(mapView.box);
        root.find('[data-movement=drawing]').attr('aria-pressed', 'true'); root.find('[data-movement=road]').attr('aria-pressed', 'false');
        root.find('[data-movement=towns]').attr('aria-pressed', String(mapView.towns));
        root.find('[data-movement=zones]').attr('aria-pressed', String(mapView.zones));
        const missing = shown.filter(v => v.lat == null || v.lon == null).length;
        root.find('.sig-movement-note').text(`${movement.start} – ${movement.end} · ${shown.length} ${__('visits')} · ${missing} ${__('unmapped')}${movement.truncated ? ' · ' + __('Results limited to 10,000 visits') : ''}`);
    }

    async function focusVisitOnMap(name) {
        const request = ++focusRequest;
        const row = (lastPayload.rows || []).find(r => r.name === name);
        if (!row || !row.start_at) return;
        const day = String(row.start_at).slice(0, 10);
        if (!movement || day < movement.start || day > movement.end) {
            state.anchor = day;
            root.find('.sig-movement-anchor').val(day);
            await loadMovement();
            if (request !== focusRequest) return;
        }
        const visit = movement && (movement.visits || []).find(v => v.name === name);
        if (!visit || visit.lat == null || visit.lon == null) {
            highlightedVisit = null; drawMovement();
            frappe.show_alert({message: __('This visit has no map point in the selected period.'), indicator: 'orange'});
            return;
        }
        highlightedVisit = name;
        drawMovement();
        if (mapView.leaflet) mapView.leaflet.setView([visit.lat, visit.lon], 8);
        else { const [x, y] = window.sigMovementMapAssets.project(visit.lon, visit.lat); const w = 180, h = w * 760 / 830; setMovementBox([x-w/2, y-h/2, w, h]); }
        const point = root.find('.sig-movement-point').filter(function () { return $(this).attr('data-session') === name; });
        const color = point.find('circle').first().attr('fill') || root.find('.sig-movement-person').filter(function () { return $(this).attr('data-person') === visit.employee; }).find('span').css('background-color') || '#3784db';
        showMovementSite(visit, color);
    }

    function showMovementSite(visit, color) {
        const box = root.find('.sig-movement-sitebox');
        const visitRow = (lastPayload.rows || []).find(row => row.name === visit.name) || {};
        const initialProject = familyLabel(visitRow.project_family) || '—';
        box.html(`<div class="sig-movement-sitecard" style="--site-color:${esc(color)}"><button type="button" class="sig-movement-site-close" aria-label="${__('Close')}">×</button><b>${esc(visit.site || '—')}</b><div>${esc(visit.person || '—')}</div><small>${esc(dt(visit.at))}</small><div class="sig-movement-project"><span>${__('Project')}</span><b class="sig-movement-project-value">${esc(initialProject)}</b></div><div class="sig-movement-cycle-slot"></div>${(lastPayload.rows || []).some(row => row.name === visit.name) ? `<button type="button" class="btn btn-default btn-xs sig-movement-visit-detail">${__('Visit details')}</button>` : ''}</div>`);
        box.find('.sig-movement-site-close').on('click', () => box.empty());
        box.find('.sig-movement-visit-detail').on('click', () => {
            if (!(lastPayload.rows || []).some(row => row.name === visit.name)) { frappe.show_alert({message: __('Select this visit in the list to see full details.'), indicator: 'orange'}); return; }
            state.selected = visit.name; root.find('.sig-sv-detail').removeClass('is-closed').addClass('is-open'); showDetail(visit.name);
        });
        box.data('session', visit.name);
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visit', args: {session_key: visit.name}, callback: r => {
            if (!box.find('.sig-movement-project-value').length || box.data('session') !== visit.name) return;
            const d = r.message || {}, cycle = d.cycle || {};
            const category = familyLabel(d.project_family) || initialProject;
            box.find('.sig-movement-project-value').text(category);
            box.find('.sig-movement-cycle-slot').html(cycle.name ? `<button type="button" class="sig-movement-cycle btn btn-link btn-xs">${__('Open cycle')}</button>` : '');
            box.find('.sig-movement-cycle').on('click', () => frappe.set_route('Form', 'SIG Site Cycle', cycle.name));
        }});
    }

    function drawMovementRoad(shown, runs, personColor) {
        root.find('.sig-movement-map').html('<div class="sig-movement-leaflet"></div>');
        const map = L.map(root.find('.sig-movement-leaflet')[0], {minZoom:5,maxZoom:11,scrollWheelZoom:false});
        mapView.leaflet = map;
        const tiles = frappe.utils.map_defaults.tiles, config = tiles.default_tile || {url: tiles, options: frappe.utils.map_defaults.options};
        L.tileLayer(config.url, config.options).addTo(map);
        runs.forEach(group => {
            for (let i = 1; i < group.length; i++) { const a = group[i-1], b = group[i]; if (a.lat == null || a.lon == null || b.lat == null || b.lon == null) continue; L.polyline([[a.lat,a.lon],[b.lat,b.lon]], {color:personColor(b),weight:3}).addTo(map); }
            group.forEach((v,i) => { if (v.lat == null || v.lon == null) return; const color = personColor(v); const active = highlightedVisit === v.name; const icon = L.divIcon({className:'sig-movement-road-icon',html:`<span class="sig-movement-road-point ${active ? 'is-highlighted' : ''}" style="--point-color:${color}">${i+1}</span>`,iconSize:active?[32,32]:[26,26],iconAnchor:active?[16,16]:[13,13]}); const marker = L.marker([v.lat,v.lon], {icon,zIndexOffset:active ? 1000 : i}).bindTooltip(`${esc(v.site)} · ${esc(v.person)} · ${esc(v.at.slice(0,16))} · ${i+1}`); marker.on('click', () => showMovementSite(v, personColor(v))); marker.addTo(map); });
        });
        if (mapView.roadView) map.setView(mapView.roadView.center,mapView.roadView.zoom); else map.setView([24.5,45],6);
        root.find('[data-movement=drawing]').attr('aria-pressed','false'); root.find('[data-movement=road]').attr('aria-pressed','true');
        setTimeout(() => map.invalidateSize(), 50);
    }

    function clampMovementBox(box) {
        const w = Math.min(830, Math.max(830 / 12, box[2])), h = w * 760 / 830;
        const px = Math.min(830 * .35, w * .55), py = Math.min(760 * .35, h * .55);
        return [Math.min(850 - w + px, Math.max(20 - px, box[0])), Math.min(795 - h + py, Math.max(35 - py, box[1])), w, h];
    }
    function setMovementBox(box) {
        mapView.box = clampMovementBox(box);
        const svg = root.find('.sig-movement-map svg')[0];
        if (svg) {
            svg.setAttribute('viewBox', mapView.box.join(' '));
            const k = Math.max(.35, Math.pow(830 / mapView.box[2], -.8));
            svg.querySelectorAll('.sig-movement-point').forEach(point => { const circle = point.querySelector('circle'), text = point.querySelector('text'); if (circle) { circle.setAttribute('r', 6*k); circle.setAttribute('stroke-width', 1.5*k); } if (text && circle) { text.setAttribute('font-size', 6*k); text.setAttribute('y', Number(circle.getAttribute('cy')) + 2*k); } });
        }
    }
    function zoomMovement(factor, cx, cy) {
        const [x,y,w,h] = mapView.box, px = cx == null ? x+w/2 : cx, py = cy == null ? y+h/2 : cy;
        setMovementBox([px-(px-x)*factor, py-(py-y)*factor, w*factor, h*factor]);
    }
    function movementPoint(svg, event) {
        const rect = svg.getBoundingClientRect(), [x,y,w,h] = mapView.box, scale = Math.min(rect.width/w, rect.height/h);
        const left = rect.left + (rect.width-w*scale)/2, top = rect.top + (rect.height-h*scale)/2;
        return [x+(event.clientX-left)/scale, y+(event.clientY-top)/scale];
    }
    function movementControl(action) {
        if (action === 'drawing' || action === 'road') {
            if (action === 'road') { Promise.all([frappe.require('leaflet.bundle.js'), frappe.require('leaflet.bundle.css')]).then(() => { if (typeof L === 'undefined' || !frappe.utils.map_defaults?.tiles) throw new Error('Map tiles unavailable'); mapView.base = 'road'; drawMovement(); }).catch(() => frappe.msgprint(__('Road map is unavailable.'))); }
            else { mapView.base = 'drawing'; drawMovement(); }
        }
        else if (action === 'in' && mapView.leaflet) mapView.leaflet.zoomIn();
        else if (action === 'out' && mapView.leaflet) mapView.leaflet.zoomOut();
        else if (action === 'in') zoomMovement(.7);
        else if (action === 'out') zoomMovement(1.4);
        else if (action === 'reset') { if (mapView.leaflet) mapView.leaflet.setView([24.5,45], 6); else setMovementBox([20,35,830,760]); }
        else if (action === 'towns' || action === 'zones') { mapView[action] = !mapView[action]; drawMovement(); }
        else if (action === 'expand') { const card = root.find('.sig-movement'); card.toggleClass('is-expanded'); root.find('[data-movement=expand]').text(card.hasClass('is-expanded') ? __('Close expanded map') : __('Expand map')); if (mapView.leaflet) setTimeout(() => mapView.leaflet && mapView.leaflet.invalidateSize(), 80); }
        else if (action === 'fit' || action === 'find') {
            const query = String(root.find('.sig-movement-search').val() || '').trim().toLowerCase();
            const matches = (movement.visits || []).filter(v => (!state.person || v.employee === state.person) && v.lat != null && v.lon != null && (action !== 'find' || (query && String(v.site || '').toLowerCase().includes(query))));
            if (!matches.length) { frappe.show_alert({message: __('No matching mapped visits.'), indicator: 'orange'}); return; }
            if (mapView.leaflet) { mapView.leaflet.fitBounds(matches.map(v => [v.lat,v.lon]), {padding:[44,44], maxZoom:8}); return; }
            const points = matches.map(v => window.sigMovementMapAssets.project(v.lon,v.lat));
            const xs = points.map(p => p[0]), ys = points.map(p => p[1]), minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
            const width = Math.max(100, (maxx-minx)*1.5, (maxy-miny)*1.5*830/760);
            setMovementBox([(minx+maxx-width)/2, (miny+maxy-width*760/830)/2, width, width*760/830]);
        }
    }
    function bindMovementMap() {
        const svg = root.find('.sig-movement-map svg')[0]; if (!svg) return;
        svg.addEventListener('wheel', e => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); const delta = Math.max(-50, Math.min(50, e.deltaY)), [x,y] = movementPoint(svg,e); zoomMovement(Math.exp(delta * .008),x,y); }, {passive: false});
        svg.addEventListener('dblclick', e => { e.preventDefault(); const [x,y] = movementPoint(svg,e); zoomMovement(.5,x,y); });
        const pointers = new Map(); let gesture = null;
        const resetGesture = () => {
            const values = [...pointers.values()];
            if (values.length === 1) gesture = {kind: 'pan', start: values[0], box: [...mapView.box]};
            else if (values.length === 2) gesture = {kind: 'pinch', distance: Math.hypot(values[0].x-values[1].x, values[0].y-values[1].y), box: [...mapView.box]};
            else gesture = null;
        };
        svg.addEventListener('pointerdown', e => { if (e.target.closest('.sig-movement-point')) return; e.preventDefault(); pointers.set(e.pointerId,{x:e.clientX,y:e.clientY}); svg.setPointerCapture(e.pointerId); resetGesture(); });
        svg.addEventListener('pointermove', e => {
            if (!pointers.has(e.pointerId) || !gesture) return;
            pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
            const rect = svg.getBoundingClientRect(); if (!rect.width || !rect.height) return;
            if (gesture.kind === 'pan') { const p = pointers.get(e.pointerId), b = gesture.box, scale = Math.min(rect.width/b[2],rect.height/b[3]); setMovementBox([b[0]-(p.x-gesture.start.x)/scale,b[1]-(p.y-gesture.start.y)/scale,b[2],b[3]]); }
            else if (gesture.kind === 'pinch' && pointers.size === 2) { const v = [...pointers.values()], distance = Math.hypot(v[0].x-v[1].x,v[0].y-v[1].y); if (distance > 0 && gesture.distance > 0) { const b = gesture.box, factor = gesture.distance / distance, w = b[2]*factor, h = b[3]*factor; setMovementBox([b[0]+(b[2]-w)/2,b[1]+(b[3]-h)/2,w,h]); } }
        });
        const endPointer = e => { pointers.delete(e.pointerId); resetGesture(); };
        svg.addEventListener('pointerup', endPointer); svg.addEventListener('pointercancel', endPointer);
        svg.querySelectorAll('.sig-movement-point').forEach(point => { const open = () => { const visit = (movement.visits || []).find(v => v.name === point.dataset.session); if (visit) showMovementSite(visit, point.querySelector('circle').getAttribute('fill')); }; point.addEventListener('click', open); point.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } }); });
    }

    let latestLoad = 0;
    function load() {
        const requestId = ++latestLoad;
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visits',
            args: {stream: state.stream, site: state.site, person: state.person, status: state.status,
                   view: state.view, search: state.search,
                   date_from: state.view === 'history' ? state.historyFrom : state.dateFrom,
                   date_to: state.view === 'history' ? state.historyTo : state.dateTo},
            callback: (r) => { if (requestId === latestLoad && r.message) renderTable(r.message); }});
    }

    shell();
    loadMovement();
};
