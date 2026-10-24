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

    // Schematic Saudi Arabia outline (lon, lat); for orientation only, not a survey boundary.
    const KSA = [[34.9,29.4],[35.2,28.0],[36.6,25.9],[37.2,24.8],[38.1,24.0],[38.9,22.6],[39.2,21.4],[39.1,20.2],
        [40.1,18.9],[41.0,17.4],[42.6,16.8],[43.2,17.3],[44.2,17.4],[46.4,17.2],[47.6,17.4],[48.8,18.2],[50.0,18.0],
        [52.0,19.0],[55.0,20.0],[55.7,22.0],[52.6,22.9],[51.6,24.2],[50.8,24.8],[50.2,26.5],[49.6,27.2],[48.6,28.0],
        [47.7,28.5],[47.4,29.0],[46.6,29.1],[44.7,29.2],[42.0,31.0],[39.2,32.1],[38.0,31.6],[37.0,29.9],[35.7,29.3]];
    const TRIP_COLORS = ['#1e7fff', '#e8590c', '#2b9348', '#9c36b5', '#d6336c', '#0b7285', '#a67c00', '#495057'];
    const TIER_COLORS = {T0: '#1e7fff', T1: '#a4211f', T2: '#c27c00', T3: '#1a7a3d', T4: '#868e96'};
    const view = {mode: 'trip', box: null};

    function project(lon, lat) { return [(lon - 33) * 0.91 * 40, (34 - lat) * 40]; }

    function drawMap(data, mount) {
        const BOX0 = [20, 35, 830, 700];
        view.box = view.box || BOX0.slice();
        const outline = KSA.map(([lon, lat]) => project(lon, lat).join(',')).join(' ');
        let lines = '', dots = '', labels = '';
        data.trips.forEach((trip, index) => {
            const color = TRIP_COLORS[index % TRIP_COLORS.length];
            const pts = trip.stops.map((stop) => project(stop.lon, stop.lat));
            if (pts.length > 1) {
                lines += `<polyline points="${pts.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${color}"
                    stroke-width="2" stroke-opacity="${trip.loaded ? 0.9 : 0.35}" ${trip.loaded ? '' : 'stroke-dasharray="5 4"'}/>`;
            }
            trip.stops.forEach((stop, i) => {
                const [x, y] = pts[i];
                const fill = view.mode === 'trip' ? color : TIER_COLORS[stop.tier];
                const shape = stop.kind === 'Committed' ? `<rect x="${x - 6}" y="${y - 6}" width="12" height="12"` :
                    `<circle cx="${x}" cy="${y}" r="6.5"`;
                dots += `${shape} fill="${fill}" fill-opacity="${trip.loaded ? 1 : 0.5}" stroke="#fff" stroke-width="1.5">
                    <title>${esc(stop.site)} · ${esc(data.tiers[stop.tier])} · ${esc(trip.id)} #${stop.order}\n${esc(stop.reason)}</title>
                    ${stop.kind === 'Committed' ? '</rect>' : '</circle>'}`;
                labels += `<text x="${x}" y="${y + 3}" text-anchor="middle" font-size="8" fill="#fff" pointer-events="none">${stop.order}</text>`;
            });
        });
        const legend = view.mode === 'trip'
            ? data.trips.slice(0, 8).map((trip, i) => `<span><i style="background:${TRIP_COLORS[i % 8]}"></i>${esc(trip.id)}</span>`).join('')
            : Object.keys(TIER_COLORS).map((tier) => `<span><i style="background:${TIER_COLORS[tier]}"></i>${esc(data.tiers[tier])}</span>`).join('');
        mount.html(`<div class="sig-planner-maptools">
            <button class="btn btn-xs ${view.mode === 'trip' ? 'btn-primary' : 'btn-default'}" data-mode="trip">${__('Colour by trip')}</button>
            <button class="btn btn-xs ${view.mode === 'tier' ? 'btn-primary' : 'btn-default'}" data-mode="tier">${__('Colour by priority')}</button>
            <button class="btn btn-xs btn-default" data-mode="reset">${__('Reset view')}</button>
            <span class="sig-planner-legend">${legend}</span></div>
            <svg viewBox="${view.box.join(' ')}" class="sig-planner-svg" preserveAspectRatio="xMidYMid meet">
            <polygon points="${outline}" fill="#eef7fc" stroke="#9db4c9" stroke-width="1.5"/>${lines}${dots}${labels}</svg>
            <div class="sig-planner-foot">${__('Squares are committed TCN sites, circles are the rest; dashed, faded trips are backlog. Outline is schematic.')}</div>`);
        const svg = mount.find('svg')[0];
        mount.find('button').on('click', (e) => {
            const mode = $(e.currentTarget).data('mode');
            if (mode === 'reset') view.box = BOX0.slice(); else view.mode = mode;
            drawMap(data, mount);
        });
        svg.addEventListener('wheel', (e) => {
            e.preventDefault();
            const f = e.deltaY < 0 ? 0.8 : 1.25;
            const r = svg.getBoundingClientRect();
            const [x, y, w, h] = view.box;
            const px = x + ((e.clientX - r.left) / r.width) * w, py = y + ((e.clientY - r.top) / r.height) * h;
            view.box = [px - (px - x) * f, py - (py - y) * f, w * f, h * f];
            svg.setAttribute('viewBox', view.box.join(' '));
        }, {passive: false});
        let drag = null;
        svg.addEventListener('mousedown', (e) => { drag = {x: e.clientX, y: e.clientY, box: view.box.slice()}; });
        window.addEventListener('mouseup', () => { drag = null; });
        svg.addEventListener('mousemove', (e) => {
            if (!drag) return;
            const r = svg.getBoundingClientRect();
            view.box = [drag.box[0] - ((e.clientX - drag.x) / r.width) * drag.box[2],
                drag.box[1] - ((e.clientY - drag.y) / r.height) * drag.box[3], drag.box[2], drag.box[3]];
            svg.setAttribute('viewBox', view.box.join(' '));
        });
    }

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
        root.html(`<div class="sig-planner-cards">${cards}</div>${note}<div class="sig-planner-map"></div>${trips}${other}
            <p class="sig-planner-foot">${__('Read-only proposal. Mark a cycle Hold or Visited on its form to keep it out of the plan.')}</p>`);
        if (data.has_coordinates && data.trips.length) drawMap(data, root.find('.sig-planner-map'));
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
