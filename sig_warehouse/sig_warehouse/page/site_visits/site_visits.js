// Site Visits (V0, read-only). See docs/site_visits_page_design.md.
// Same client pattern as project-progress: one shell, server does the filtering,
// row click opens a side panel with the original WhatsApp timeline + cycle context.
frappe.pages['site-visits'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Site Visits'), single_column: true});
    const root = $('<div class="sig-sv-page"></div>').appendTo(page.main);
    const state = {stream: '', site: '', person: '', status: '', view: 'current', search: '', selected: null};
    const esc = (v) => frappe.utils.escape_html(String(v || ''));
    const dt = (v) => v ? frappe.datetime.str_to_user(String(v).slice(0, 19)) : '—';
    const timeOnly = (v) => v ? String(v).slice(11, 16) : '';

    function shell() {
        root.html(`<div class="sig-sv-toolbar">
            <label class="sig-sv-field">${__('View')}<select class="sig-sv-view form-control">
                <option value="current">${__('Current')}</option><option value="today">${__('Today')}</option>
                <option value="open">${__('Open now')}</option><option value="review">${__('Needs review')}</option>
                <option value="history">${__('History')}</option>
            </select></label>
            <label class="sig-sv-field">${__('Stream / PM')}<select class="sig-sv-stream form-control"><option value="">${__('All')}</option></select></label>
            <label class="sig-sv-field" style="min-width:200px">${__('Site or person')}<input class="sig-sv-search form-control" placeholder="${__('Search site or reporter')}"></label>
        </div>
        <div class="sig-sv-summary"></div>
        <div class="sig-sv-main"><div class="sig-sv-table-wrap"></div><aside class="sig-sv-detail"><div class="text-muted text-center" style="padding:40px 10px">${__('Select a visit to see its WhatsApp timeline and site context.')}</div></aside></div>`);
        root.find('.sig-sv-view').on('change', function () { state.view = this.value; load(); });
        root.find('.sig-sv-stream').on('change', function () { state.stream = this.value; load(); });
        root.find('.sig-sv-search').on('input', frappe.utils.debounce(function () { state.search = this.value; load(); }, 250));
    }

    function summaryHtml(s) {
        const tile = (label, n, view) => `<div class="sig-sv-tile" data-view="${view}"><div class="sig-sv-tile-n">${n}</div><div class="sig-sv-tile-l">${__(label)}</div></div>`;
        return tile('Open now', s.open_now, 'open') + tile('Visits today', s.visits_today, 'today')
            + tile('Needs review', s.needs_review, 'review') + tile('Unclassified', s.unclassified, 'current')
            + tile('Sites this week', s.sites_this_week, 'current');
    }

    function statusBadge(row) {
        if (row.is_review) return `<span class="indicator-pill red">${__('Review')}</span>`;
        if (row.status === 'OPEN') return `<span class="indicator-pill blue">${__('Open')}</span>`;
        if (row.status === 'AUTO_CLOSED') return `<span class="indicator-pill orange">${__('Auto-closed')}</span>`;
        if (row.posted) return `<span class="indicator-pill green">${__('Posted')}</span>`;
        return `<span class="indicator-pill grey">${__('Pending')}</span>`;
    }

    function rowHtml(row) {
        const cyc = row.cycle;
        const projectLine = cyc ? `${esc(cyc.project)}${cyc.wo ? ' · ' + esc(cyc.wo) : ''}${cyc.is_temporary ? ' <span class="text-muted">(' + __('temp scope') + ')</span>' : ''}` : `<span class="text-muted">${__('no cycle yet')}</span>`;
        const when = `${dt(row.start_at)}${row.end_at ? '–' + timeOnly(row.end_at) : ''}`;
        return `<tr class="sig-sv-row" data-name="${esc(row.name)}">
            <td><b>${esc(row.site)}</b><br><span class="text-muted small">${projectLine}</span></td>
            <td>${esc(row.reporter_name)}<br><span class="text-muted small">${when}</span></td>
            <td>${row.hours != null ? row.hours + 'h' : '—'}<br><span class="text-muted small">${row.photo_count} ${__('photos')}</span></td>
            <td>${esc(row.activity_code || 'UNSPECIFIED')}<br><span class="text-muted small">${esc(row.stream_label)} · ${esc(row.pm)}</span></td>
            <td>${statusBadge(row)}${row.diagnostics.length ? '<br><span class="text-muted small">' + esc(row.diagnostics.join(', ')) + '</span>' : ''}</td>
        </tr>`;
    }

    function renderTable(payload) {
        const sel = root.find('.sig-sv-stream').empty().append(`<option value="">${__('All')}</option>`);
        (payload.streams || []).forEach((s) => sel.append($('<option></option>').val(s.value).text(s.label + ' (' + s.pm + ')')));
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
            <thead><tr><th>${__('Site / Project')}</th><th>${__('Who · When')}</th><th>${__('Duration · Photos')}</th>
            <th>${__('Type / Stream')}</th><th>${__('Status')}</th></tr></thead>
            <tbody>${payload.rows.map(rowHtml).join('')}</tbody></table>`);
        wrap.find('.sig-sv-row').on('click', function () { state.selected = $(this).data('name'); showDetail(state.selected); });
    }

    function showDetail(name) {
        const panel = root.find('.sig-sv-detail');
        panel.html(`<div class="text-muted text-center" style="padding:30px">${__('Loading...')}</div>`);
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visit', args: {session_key: name}, callback: (r) => {
            const d = r.message || {};
            if (d.result !== 'ok') { panel.html(`<div class="text-muted">${__('Not found.')}</div>`); return; }
            const cyc = d.cycle;
            const cycleHtml = cyc ? `<b>${esc(cyc.project || '')}</b> · ${esc(cyc.stage || '')}${cyc.wo ? ' · ' + esc(cyc.wo) : ''}<br>
                <span class="text-muted small">${__('Visits so far')}: ${cyc.sessions_completed || 0}, ${__('first')} ${dt(cyc.first_visit_at)}, ${__('last')} ${dt(cyc.last_visit_at)}</span>` : `<span class="text-muted">${__('No cycle yet for this site.')}</span>`;
            const timelineHtml = (d.timeline || []).map((m) => `<div class="sig-sv-msg"><span class="text-muted small">${timeOnly(m.at)}</span> <b>${esc(m.who)}</b> <span class="indicator-pill ${m.kind === 'START' ? 'blue' : m.kind === 'END' ? 'green' : 'grey'}" style="font-size:10px">${m.kind}</span>${m.text ? ' — ' + esc(m.text) : ''}</div>`).join('') || `<div class="text-muted small">${__('No stored messages.')}</div>`;
            const priorHtml = (d.prior_visits || []).map((p) => `<div class="small">${dt(p.start_at)} · ${esc(p.reporter_name)} · ${esc(p.status)}</div>`).join('') || `<div class="text-muted small">${__('None.')}</div>`;
            panel.html(`<h5>${__('Site context')}</h5><div class="sig-sv-block">${cycleHtml}</div>
                <h5>${__('WhatsApp timeline')}</h5><div class="sig-sv-block sig-sv-timeline">${timelineHtml}</div>
                <h5>${__('Other visits at this site')}</h5><div class="sig-sv-block">${priorHtml}</div>`);
        }});
    }

    function load() {
        frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_visits',
            args: {stream: state.stream, site: state.site, person: state.person, status: state.status,
                   view: state.view, search: state.search},
            callback: (r) => { if (r.message) renderTable(r.message); }});
    }

    shell();
    load();
};
