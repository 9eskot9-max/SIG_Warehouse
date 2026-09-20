frappe.pages['project-progress'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Project Progress'), single_column: true});
    const root = $('<div class="sig-pp-page"></div>').appendTo(page.main);
    const state = {project: '', view: 'current', search: '', selected: null, payload: null, events: []};
    const esc = (value) => frappe.utils.escape_html(String(value || ''));
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 19)) : '—';

    function shell() {
        root.html(`<div class="sig-pp-toolbar">
            <label class="sig-pp-field">${__('Project')}<select class="sig-pp-project form-control"><option value="">${__('All projects')}</option></select></label>
            <label class="sig-pp-field">${__('View')}<select class="sig-pp-view form-control">
                <option value="current">${__('Current work')}</option><option value="followup">${__('Follow-up due')}</option>
                <option value="blockers">${__('Reported blockers')}</option><option value="review">${__('Needs review')}</option><option value="history">${__('History')}</option>
            </select></label>
            <label class="sig-pp-field" style="min-width:220px">${__('Site or reference')}<input class="sig-pp-search form-control" placeholder="${__('Search site, PO or WO')}"></label>
            <button type="button" class="btn btn-default btn-sm sig-pp-insights">${__('Open Ops KPIs')}</button>
        </div><div class="sig-pp-summary"></div><div class="sig-pp-main"><div class="sig-pp-table-wrap"></div><aside class="sig-pp-detail"></aside></div>`);
        root.find('.sig-pp-project').on('change', function () { state.project = this.value; load(); });
        root.find('.sig-pp-view').on('change', function () { state.view = this.value; load(); });
        root.find('.sig-pp-search').on('input', frappe.utils.debounce(function () { state.search = this.value; load(); }, 250));
        root.find('.sig-pp-insights').on('click', function () { window.open('/insights/dashboard/dh657cqj78', '_blank', 'noopener'); });
    }

    function renderFilters() {
        const sel = root.find('.sig-pp-project').empty().append(`<option value="">${__('All projects')}</option>`);
        (state.payload.projects || []).forEach((p) => sel.append($('<option></option>').val(p).text(p)));
        sel.val(state.project); root.find('.sig-pp-view').val(state.view); root.find('.sig-pp-search').val(state.search);
    }

    function activityHtml(row) {
        return (row.activities || []).map((a) => `<span class="sig-pp-chip ${a.state === 'Recorded' ? '' : 'missing'}">${esc(a.label)}: ${a.state === 'Recorded' ? esc(date(a.at)) : __('not recorded')}</span>`).join('');
    }

    function renderSummary() {
        const s = state.payload.summary || {};
        root.find('.sig-pp-summary').html([
            ['scopes', __('Monitored scopes')], ['sites', __('Unique sites')], ['due', __('Follow-ups due')], ['blockers', __('Reported blockers')], ['reviews', __('Needs review')]
        ].map(([key, label]) => `<div class="sig-pp-stat"><div class="value">${esc(s[key])}</div><div class="label">${label}</div></div>`).join(''));
    }

    function renderTable() {
        const rows = state.payload.rows || [];
        const table = `<div class="sig-pp-table-title"><span>${__('Evidence-driven worklist')}</span><span>${rows.length} ${__('rows')}</span></div><table class="sig-pp-table"><thead><tr>
            <th style="width:15%">${__('Site / project')}</th><th style="width:16%">${__('Work position')}</th><th style="width:24%">${__('Recorded activities')}</th><th style="width:17%">${__('Next follow-up')}</th><th style="width:19%">${__('Latest update')}</th><th style="width:9%">${__('Timing')}</th>
        </tr></thead><tbody>${rows.length ? rows.map((r) => {
            const due = r.todo ? `<div>${esc(r.todo.description)}</div><div class="sig-pp-meta">${__('Due')} ${esc(r.todo.date || '—')}</div>` : `<span class="sig-pp-muted">${__('No open ToDo')}</span>`;
            const update = r.latest_comment ? `<div>${esc(r.latest_comment.content)}</div><div class="sig-pp-meta">${esc(r.latest_comment.owner)} · ${esc(date(r.latest_comment.creation))} · ${r.comment_count} ${__('updates')}</div>` : `<span class="sig-pp-muted">${__('No human update yet')}</span>`;
            const timing = r.todo && r.todo.date && r.todo.date < frappe.datetime.get_today() ? `<span class="sig-pp-danger">${__('Overdue')}</span>` : (r.delay_reason ? `<span class="sig-pp-warning">${esc(r.delay_reason)}</span>` : `<span class="sig-pp-good">${__('Current')}</span>`);
            return `<tr data-cycle="${esc(r.name)}" class="${state.selected === r.name ? 'sig-selected' : ''}"><td><span class="sig-pp-site">${esc(r.site)}</span><span class="sig-pp-project">${esc(r.project)}${r.wo && r.po ? '' : ''}</span></td><td><strong>${esc(r.position)}</strong><div class="sig-pp-muted">${esc(r.basis)}</div></td><td>${activityHtml(r)}</td><td>${due}</td><td>${update}</td><td>${timing}</td></tr>`;
        }).join('') : `<tr><td colspan="6" class="text-muted text-center">${__('No cycles match these filters.')}</td></tr>`}</tbody></table>`;
        root.find('.sig-pp-table-wrap').html(table).find('tbody tr[data-cycle]').on('click', function () { state.selected = $(this).data('cycle'); state.events = []; renderTable(); renderDetail(); loadEvents(); });
    }

    function renderDetail() {
        const row = (state.payload.rows || []).find((r) => r.name === state.selected);
        if (!row) { root.find('.sig-pp-detail').html(`<div class="sig-pp-detail-body text-muted">${__('Select a row to see updates and evidence.')}</div>`); return; }
        const comments = (row.comments || []).length ? row.comments.map((comment) => `<div class="sig-pp-comment"><div>${esc(comment.content)}</div><div class="sig-pp-comment-meta">${esc(comment.owner)} · ${esc(date(comment.creation))}</div></div>`).join('') : `<div class="sig-pp-muted">${__('No human updates yet. Add the first update below.')}</div>`;
        const events = (state.events || []).map((e) => `<div class="sig-pp-event"><span class="sig-pp-event-dot"></span><div><strong>${esc(e.code)}</strong><div class="sig-pp-meta">${esc(date(e.occurred_at))} · ${esc(e.source || 'ERP')}</div></div></div>`).join('');
        root.find('.sig-pp-detail').html(`<div class="sig-pp-detail-head"><h3>${esc(row.site)}</h3><div class="sig-pp-muted">${esc(row.project)} · ${esc(row.position)}</div></div><div class="sig-pp-detail-body"><div class="sig-pp-note"><div class="sig-pp-note-label">${__('Updates')}</div><div class="sig-pp-comment-list">${comments}</div></div><textarea class="sig-pp-update form-control" placeholder="${__('Add an update for this site…')}"></textarea><button class="btn btn-primary btn-sm sig-pp-add-update">${__('Update')}</button><div class="sig-pp-evidence"><h4>${__('EVIDENCE HISTORY')}</h4>${events || `<div class="sig-pp-muted">${__('No evidence events returned.')}</div>`}</div><div class="sig-pp-muted" style="margin-top:10px">${row.wo && row.po ? __('WO / PO reference available in record') : __('WO is hidden: this scope is unambiguous')}</div></div>`);
        root.find('.sig-pp-add-update').on('click', function () { const btn = $(this); const content = root.find('.sig-pp-update').val().trim(); if (!content) { frappe.msgprint(__('Write an update first.')); return; } btn.prop('disabled', true); frappe.call({method: 'sig_warehouse.sig_warehouse.project_progress.add_comment', args: {cycle: row.name, content: content}}).then(() => { frappe.show_alert({message: __('Update added'), indicator: 'green'}); state.selected = row.name; load(); }).always(() => btn.prop('disabled', false)); });
    }

    function loadEvents() { if (!state.selected) return; frappe.call({method: 'sig_warehouse.sig_warehouse.project_progress.get_events', args: {cycle: state.selected}}).then((r) => { if (r.message) { state.events = r.message; renderDetail(); } }); }
    function load() { frappe.call({method: 'sig_warehouse.sig_warehouse.project_progress.get_progress', args: {project: state.project, view: state.view, search: state.search}}).then((r) => { state.payload = r.message || {rows: [], projects: [], summary: {}}; if (!state.selected || !(state.payload.rows || []).some((x) => x.name === state.selected)) state.selected = (state.payload.rows || [])[0]?.name || null; renderFilters(); renderSummary(); renderTable(); renderDetail(); if (state.selected) loadEvents(); }); }
    shell(); load();
};

