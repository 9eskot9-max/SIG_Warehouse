frappe.pages['field-planner'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Field Planner'), single_column: true});
    const root = $('<main class="sig-planner-page"></main>').appendTo(page.main);
    const esc = (value) => frappe.utils.escape_html(value == null ? '' : String(value));
    const filters = {};

    const field = (fieldname, label, fieldtype, def) => page.add_field({
        fieldname, label, fieldtype, default: def, change() { filters[fieldname] = this.get_value(); },
    });
    field('week_start', __('Week starting (Sunday)'), 'Date');
    field('teams', __('Teams available'), 'Int', 4);
    field('scope_hours', __('Hours per site'), 'Float', 2);
    field('diameter_km', __('Trip diameter (km)'), 'Float', 150);
    field('project', __('Project'), 'Data');
    page.set_primary_action(__('Refresh'), load);
    filters.teams = 4; filters.scope_hours = 2; filters.diameter_km = 150;

    function card(label, value, tone) {
        return `<div class="sig-planner-card sig-planner-${tone}"><div class="num">${esc(value)}</div><div class="lbl">${esc(label)}</div></div>`;
    }

    function render(data) {
        const s = data.summary;
        const cards = [
            card(__('Committed this week'), s.committed_sites, 'blue'),
            card(__('Overdue TCN'), s.overdue, 'red'),
            card(__('Close to handover'), s.close_to_handover, 'amber'),
            card(__('Ready to batch'), s.ready_to_batch, 'green'),
            card(__('Team-days planned / capacity'), `${s.loaded_team_days} / ${s.capacity_team_days}`, s.over_capacity ? 'red' : 'green'),
            card(__('Backlog trips'), s.backlog_trips, 'gray'),
            card(__('No coordinates'), data.has_coordinates ? s.no_coordinates : s.candidates, s.no_coordinates || !data.has_coordinates ? 'red' : 'gray'),
        ].join('');
        const note = data.has_coordinates ? '' :
            `<div class="sig-planner-note">${__('Site coordinates are not loaded yet, so trips cannot be formed.')}</div>`;
        const trips = data.trips.map((trip) => {
            const rows = trip.stops.map((stop) => `<tr>
                <td>${stop.order}</td>
                <td><a href="/app/sig-site-cycle/${encodeURIComponent(stop.cycle)}">${esc(stop.site)}</a></td>
                <td>${esc(stop.project)}</td>
                <td><span class="sig-planner-pill sig-planner-${esc(stop.tier)}">${esc(data.tiers[stop.tier])}</span></td>
                <td>${esc(stop.kind)}</td><td>${esc(stop.window)}</td><td>${esc(stop.reason)}</td>
                <td class="num">${stop.leg_km == null ? '' : esc(stop.leg_km)}</td></tr>`).join('');
            const title = `${esc(trip.id)} · ${esc(trip.kind)}${trip.anchor ? ' · ' + esc(trip.anchor) : ''}`;
            return `<section class="sig-planner-trip ${trip.loaded ? '' : 'sig-planner-backlog'}">
                <header><b>${title}</b><span>${trip.stops.length} ${__('sites')} · ${esc(trip.diameter_km)} km ${__('spread')} ·
                ${esc(trip.hours)} h · ${esc(trip.team_days)} ${__('team-day(s)')} ·
                ${trip.loaded ? __('This week') : __('Backlog')}</span></header>
                <table><thead><tr><th>#</th><th>${__('Site')}</th><th>${__('Project')}</th><th>${__('Priority')}</th>
                <th>${__('Kind')}</th><th>${__('TCN window')}</th><th>${__('Why')}</th><th>${__('km')}</th></tr></thead>
                <tbody>${rows}</tbody></table></section>`;
        }).join('');
        const other = data.other.length ? `<section class="sig-planner-trip"><header><b>${__('Not placed')}</b>
            <span>${__('Committed for a later week, or no site coordinates')}</span></header><table><tbody>${
            data.other.map((o) => `<tr><td><a href="/app/sig-site-cycle/${encodeURIComponent(o.cycle)}">${esc(o.site)}</a></td>
                <td>${esc(o.project)}</td><td>${esc(data.tiers[o.tier])}</td><td>${esc(o.kind)}</td>
                <td>${esc(o.window)}</td><td>${esc(o.reason)}</td></tr>`).join('')}</tbody></table></section>` : '';
        root.html(`<div class="sig-planner-cards">${cards}</div>${note}${trips}${other}
            <p class="sig-planner-foot">${__('Read-only proposal. Mark a cycle Hold or Visited on its form to keep it out of the plan.')}</p>`);
    }

    function load() {
        root.html(`<p class="sig-planner-foot">${__('Loading…')}</p>`);
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.field_planner_api.get_field_plan', args: filters,
            callback: (r) => render(r.message), error: () => root.html(`<p class="sig-planner-foot">${__('Could not load the field plan.')}</p>`),
        });
    }
    load();
};
