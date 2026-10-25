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
    const ZONE_COLORS = {Riyadh: '#fbe3c4', Qassim: '#dcefc9', Hail: '#e4dcf2', Madinah: '#f9d7d7', Makkah: '#d3e7f7',
        Asir: '#fbf0b8', Jizan: '#cdeeea', Najran: '#f3d9e6', East: '#d9e1f2', North: '#e6e8d2'};
    const BOX0 = [20, 35, 830, 700];
    const view = {mode: 'trip', base: 'drawing', zones: true, towns: true, box: null, leaflet: null, townList: null, zoneCells: null};

    function project(lon, lat) { return [(lon - 33) * 0.91 * 40, (34 - lat) * 40]; }

    function km(a, b) {
        const r = Math.PI / 180, h = Math.sin((b[0] - a[0]) * r / 2) ** 2 +
            Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin((b[1] - a[1]) * r / 2) ** 2;
        return 12742 * Math.asin(Math.sqrt(h));
    }

    // Overnight base for a trip: the reference town nearest to the centre of its stops.
    function baseTown(trip) {
        if (!view.townList || !trip.stops.length || trip.stops.some((s) => s.lat == null)) return null;
        const c = [trip.stops.reduce((s, x) => s + x.lat, 0) / trip.stops.length, trip.stops.reduce((s, x) => s + x.lon, 0) / trip.stops.length];
        let best = null;
        view.townList.forEach((t) => { const d = km(c, [t.lat, t.lon]); if (!best || d < best.d) best = {t, d}; });
        return best;
    }

    // Zone shading: every grid cell takes the zone of its nearest reference town (clipped to the outline).
    function zoneCells() {
        if (view.zoneCells || !view.townList) return view.zoneCells || '';
        const pts = view.townList.map((t) => [...project(t.lon, t.lat), t.zone]);
        let out = '';
        for (let x = BOX0[0]; x < BOX0[0] + BOX0[2]; x += 14) {
            for (let y = BOX0[1]; y < BOX0[1] + BOX0[3]; y += 14) {
                let best = null, bd = 1e12;
                pts.forEach((p) => { const d = (p[0] - x - 7) ** 2 + (p[1] - y - 7) ** 2; if (d < bd) { bd = d; best = p; } });
                out += `<rect x="${x}" y="${y}" width="14.5" height="14.5" fill="${ZONE_COLORS[best[2]] || '#eee'}"/>`;
            }
        }
        view.zoneCells = out;
        return out;
    }

    function clampBox(box) {
        const w = Math.min(BOX0[2], Math.max(BOX0[2] / 12, box[2])), h = w * BOX0[3] / BOX0[2];
        const x = Math.min(BOX0[0] + BOX0[2] - w, Math.max(BOX0[0], box[0]));
        const y = Math.min(BOX0[1] + BOX0[3] - h, Math.max(BOX0[1], box[1]));
        return [x, y, w, h];
    }

    // Keep markers and text a readable size whatever the zoom.
    function applyZoom(svg) {
        const scale = BOX0[2] / view.box[2], k = 1 / Math.sqrt(scale);
        svg.setAttribute('viewBox', view.box.join(' '));
        svg.classList.toggle('sig-planner-zoomed', scale >= 2.2);
        svg.querySelectorAll('[data-r]').forEach((e) => e.setAttribute('r', e.dataset.r * k));
        svg.querySelectorAll('[data-s]').forEach((e) => {
            const s = e.dataset.s * k, cx = e.dataset.cx, cy = e.dataset.cy;
            e.setAttribute('x', cx - s / 2); e.setAttribute('y', cy - s / 2); e.setAttribute('width', s); e.setAttribute('height', s);
        });
        svg.querySelectorAll('[data-f]').forEach((e) => { e.setAttribute('font-size', e.dataset.f * k); });
        svg.querySelectorAll('[data-w]').forEach((e) => e.setAttribute('stroke-width', e.dataset.w * k));
    }

    function zoomBy(svg, factor, cx, cy) {
        const [x, y, w, h] = view.box;
        const px = cx == null ? x + w / 2 : cx, py = cy == null ? y + h / 2 : cy;
        view.box = clampBox([px - (px - x) * factor, py - (py - y) * factor, w * factor, h * factor]);
        applyZoom(svg);
    }

    function drawStreetMap(data, mount) {
        const box = mount.find('.sig-planner-leaflet')[0];
        const map = L.map(box, {minZoom: 5, maxZoom: 11, scrollWheelZoom: false});
        view.leaflet = map;
        L.tileLayer(frappe.utils.map_defaults.tiles, frappe.utils.map_defaults.options).addTo(map);
        const bounds = [];
        data.trips.forEach((trip, index) => {
            const color = TRIP_COLORS[index % TRIP_COLORS.length], pts = trip.stops.map((s) => [s.lat, s.lon]);
            if (pts.length > 1) L.polyline(pts, {color, weight: 3, opacity: trip.loaded ? 0.9 : 0.4, dashArray: trip.loaded ? null : '6 6'}).addTo(map);
            trip.stops.forEach((s) => {
                const fill = view.mode === 'trip' ? color : TIER_COLORS[s.tier];
                L.marker([s.lat, s.lon], {icon: L.divIcon({className: 'sig-planner-pin-wrap', iconSize: [18, 18],
                    html: `<div class="sig-planner-pin" style="background:${fill};opacity:${trip.loaded ? 1 : 0.55}">${s.order}</div>`})})
                    .bindTooltip(`${s.site} · ${data.tiers[s.tier]} · ${trip.id} #${s.order}`).on('click', () => showCard(s.site)).addTo(map);
                bounds.push([s.lat, s.lon]);
            });
        });
        if (view.towns && view.townList) view.townList.forEach((t) =>
            L.circleMarker([t.lat, t.lon], {radius: 3, color: '#6b7785', weight: 1, fillOpacity: 0.7}).bindTooltip(`${t.name} · ${t.zone}`).addTo(map));
        if (bounds.length) map.fitBounds(bounds, {padding: [20, 20]}); else map.setView([24.5, 45], 6);
        setTimeout(() => map.invalidateSize(), 50);
    }

    function drawMap(data, mount) {
        if (view.leaflet) { view.leaflet.remove(); view.leaflet = null; }
        view.box = view.box || BOX0.slice();
        const street = view.base === 'street' && typeof L !== 'undefined';
        const tripNode = (trip, index) => {
            const color = TRIP_COLORS[index % TRIP_COLORS.length];
            const pts = trip.stops.map((stop) => project(stop.lon, stop.lat));
            let line = '', dots = '', labels = '';
            if (pts.length > 1) {
                line = `<polyline points="${pts.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${color}" data-w="2"
                    stroke-width="2" stroke-opacity="${trip.loaded ? 0.9 : 0.35}" ${trip.loaded ? '' : 'stroke-dasharray="5 4"'}/>`;
            }
            trip.stops.forEach((stop, i) => {
                const [x, y] = pts[i], fill = view.mode === 'trip' ? color : TIER_COLORS[stop.tier], op = trip.loaded ? 1 : 0.5;
                const tip = `<title>${esc(stop.site)} · ${esc(data.tiers[stop.tier])} · ${esc(trip.id)} #${stop.order}\n${esc(stop.reason)}</title>`;
                dots += stop.kind === 'Committed'
                    ? `<rect data-site="${esc(stop.site)}" data-s="12" data-cx="${x}" data-cy="${y}" x="${x - 6}" y="${y - 6}" width="12" height="12" fill="${fill}" fill-opacity="${op}" stroke="#fff" stroke-width="1.5">${tip}</rect>`
                    : `<circle data-site="${esc(stop.site)}" data-r="6.5" cx="${x}" cy="${y}" r="6.5" fill="${fill}" fill-opacity="${op}" stroke="#fff" stroke-width="1.5">${tip}</circle>`;
                labels += `<text data-f="8" x="${x}" y="${y + 3}" text-anchor="middle" font-size="8" fill="#fff" pointer-events="none">${stop.order}</text>`;
            });
            return {line, dots, labels};
        };
        let lines = '', dots = '', labels = '';
        if (!street) data.trips.forEach((trip, index) => { const n = tripNode(trip, index); lines += n.line; dots += n.dots; labels += n.labels; });
        const outline = KSA.map(([lon, lat]) => project(lon, lat).join(',')).join(' ');
        const townDots = (view.towns && view.townList) ? view.townList.map((t) => {
            const [x, y] = project(t.lon, t.lat);
            return `<circle data-r="2.2" cx="${x}" cy="${y}" r="2.2" fill="#6b7785" fill-opacity="0.75"><title>${esc(t.name)} · ${esc(t.zone)}</title></circle>` +
                `<text class="sig-planner-town" data-f="6.5" x="${x + 3}" y="${y - 3}" font-size="6.5" fill="#53657d" pointer-events="none">${esc(t.name)}</text>`;
        }).join('') : '';
        const zones = view.zones && view.townList ? `<g clip-path="url(#sigksa)">${zoneCells()}</g>` : '';
        const legend = view.mode === 'trip'
            ? data.trips.slice(0, 8).map((trip, i) => `<span><i style="background:${TRIP_COLORS[i % 8]}"></i>${esc(trip.id)}</span>`).join('')
            : Object.keys(TIER_COLORS).map((tier) => `<span><i style="background:${TIER_COLORS[tier]}"></i>${esc(data.tiers[tier])}</span>`).join('');
        const zoneLegend = (!street && view.zones && view.townList)
            ? Object.keys(ZONE_COLORS).map((z) => `<span><i class="sq" style="background:${ZONE_COLORS[z]}"></i>${esc(z)}</span>`).join('') : '';
        const btn = (attr, label, on) => `<button class="btn btn-xs ${on ? 'btn-primary' : 'btn-default'}" ${attr}>${label}</button>`;
        mount.html(`<div class="sig-planner-maptools">
            ${btn('data-base="drawing"', __('Drawing'), !street)}${btn('data-base="street"', __('Street map'), street)}
            ${btn('data-mode="trip"', __('Colour by trip'), view.mode === 'trip')}${btn('data-mode="tier"', __('Colour by priority'), view.mode === 'tier')}
            ${btn('data-toggle="towns"', __('Towns'), view.towns)}${street ? '' : btn('data-toggle="zones"', __('Zones'), view.zones)}
            ${street ? '' : `<span class="sig-planner-zoom"><button class="btn btn-xs btn-default" data-zoom="in">+</button>
                <button class="btn btn-xs btn-default" data-zoom="out">&minus;</button>
                <button class="btn btn-xs btn-default" data-zoom="reset">${__('Reset')}</button></span>`}
            <span class="sig-planner-legend">${legend}</span></div>
            ${zoneLegend ? `<div class="sig-planner-legend sig-planner-zones">${zoneLegend}</div>` : ''}
            ${street ? '<div class="sig-planner-leaflet"></div>'
                : `<svg viewBox="${view.box.join(' ')}" class="sig-planner-svg" preserveAspectRatio="xMidYMid meet">
                <defs><clipPath id="sigksa"><polygon points="${outline}"/></clipPath></defs>
                <polygon points="${outline}" fill="#f7fafc"/>${zones}
                <polygon points="${outline}" fill="none" stroke="#9db4c9" stroke-width="1.5" data-w="1.5"/>${townDots}${lines}${dots}${labels}</svg>`}
            <div class="sig-planner-foot">${street
                ? __('Street map tiles come from OpenStreetMap and need internet. Pins show visiting order.')
                : __('Squares are committed TCN sites, circles are the rest; dashed, faded trips are backlog. Zones follow the nearest reference town; outline is schematic. Ctrl + scroll or pinch to zoom, drag to pan, double-click to zoom in.')}</div>`);
        mount.find('[data-base]').on('click', (e) => { view.base = $(e.currentTarget).data('base'); drawMap(data, mount); });
        mount.find('[data-mode]').on('click', (e) => { view.mode = $(e.currentTarget).data('mode'); drawMap(data, mount); });
        mount.find('[data-toggle]').on('click', (e) => { const k = $(e.currentTarget).data('toggle'); view[k] = !view[k]; drawMap(data, mount); });
        mount.find('[data-site]').on('click', (e) => showCard($(e.currentTarget).attr('data-site')));
        if (street) { drawStreetMap(data, mount); return; }
        const svg = mount.find('svg')[0];
        applyZoom(svg);
        mount.find('[data-zoom]').on('click', (e) => {
            const z = $(e.currentTarget).data('zoom');
            if (z === 'reset') { view.box = BOX0.slice(); applyZoom(svg); } else zoomBy(svg, z === 'in' ? 0.6 : 1 / 0.6);
        });
        const point = (e) => { const r = svg.getBoundingClientRect(), [x, y, w, h] = view.box; return [x + (e.clientX - r.left) / r.width * w, y + (e.clientY - r.top) / r.height * h]; };
        svg.addEventListener('wheel', (e) => {
            if (!(e.ctrlKey || e.metaKey)) return;                // plain scrolling keeps moving the page
            e.preventDefault();
            const d = Math.max(-50, Math.min(50, e.deltaY));      // a touchpad can fire huge deltas
            const [px, py] = point(e);
            zoomBy(svg, Math.exp(d * 0.008), px, py);
        }, {passive: false});
        svg.addEventListener('dblclick', (e) => { const [px, py] = point(e); zoomBy(svg, 0.5, px, py); });
        let drag = null;
        svg.addEventListener('mousedown', (e) => { drag = {x: e.clientX, y: e.clientY, box: view.box.slice()}; });
        window.addEventListener('mouseup', () => { drag = null; });
        svg.addEventListener('mousemove', (e) => {
            if (!drag) return;
            if (!e.buttons) { drag = null; return; }              // button was released outside the map
            const r = svg.getBoundingClientRect();
            view.box = clampBox([drag.box[0] - (e.clientX - drag.x) / r.width * drag.box[2],
                drag.box[1] - (e.clientY - drag.y) / r.height * drag.box[3], drag.box[2], drag.box[3]]);
            applyZoom(svg);
        });
    }

    function card(label, value, tone) {
        return `<div class="sig-planner-card sig-planner-${tone}"><div class="num">${esc(value)}</div><div class="lbl">${esc(label)}</div></div>`;
    }

    function indexSites(data) {
        const idx = {};
        data.trips.forEach((trip) => trip.stops.forEach((stop) => { idx[stop.site] = {stop, trip, data}; }));
        data.other.forEach((o) => { if (!idx[o.site]) idx[o.site] = {other: o, data}; });
        return idx;
    }

    function cardHtml(site, project, rows, must) {
        return `<div class="sig-planner-sitecard">
            <div class="sig-planner-sitecard-head"><b>${esc(site)}</b>${must ? ' <span class="sig-planner-pill sig-planner-must">Must</span>' : ''}
            <button type="button" class="btn btn-xs btn-default sig-planner-close" aria-label="${esc(__('Close'))}">&times;</button></div>
            <div class="sig-planner-sitecard-sub">${esc(project || '')}</div>
            <dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join('')}</dl>
            <div class="sig-planner-sitecard-links"><a href="/app/sig-site/${encodeURIComponent(site)}">${__('Open site record')}</a></div></div>`;
    }

    // Small card for one site. Shown only after a search, a map pin or a table row is clicked.
    function siteCard(site) {
        const hit = view.index[site];
        if (!hit) return '';
        const d = hit.data;
        const cycleLink = (c) => `<a href="/app/sig-site-cycle/${encodeURIComponent(c)}">${esc(c)}</a>`;
        if (hit.other) {
            const o = hit.other;
            return cardHtml(site, o.project, [
                [__('Priority'), esc(d.tiers[o.tier])],
                [__('Plan'), esc(__('Not in this week\'s plan'))],
                [__('Why'), esc(o.reason)],
                [__('TCN window'), esc(o.window || '—')],
                [__('Cycle'), cycleLink(o.cycle)],
            ]);
        }
        const {stop, trip} = hit;
        const when = trip.first_day === trip.last_day ? trip.first_day : `${trip.first_day} → ${trip.last_day}`;
        const plan = trip.status === 'Scheduled' ? `${__('Team')} ${trip.team} · ${when}`
            : trip.status === 'Lapsed' ? __('Lapsed: no team-day left') : __('Waiting for nearby sites');
        const value = stop.value ? `${Math.round(stop.value).toLocaleString()} SAR · ${stop.value_source || ''}` : '—';
        const stopText = `${stop.order} / ${trip.stops.length}` +
            (stop.leg_km == null ? '' : ` · ${stop.leg_km} km ${__('from previous')}`);
        return cardHtml(site, stop.project, [
            [__('Priority'), esc(`${stop.class || ''} · ${d.tiers[stop.tier]}`)],
            [__('Plan'), esc(`${trip.id} · ${plan}`)],
            [__('Stop'), esc(stopText)],
            [__('TCN window'), esc(stop.window || __('none this week'))],
            [__('Value'), esc(value)],
            [__('Why'), esc(stop.reason)],
            [__('Cycle'), cycleLink(stop.cycle)],
        ], stop.must || stop.class === 'Must');
    }

    function showCard(site) {
        const key = site ? String(site).toUpperCase() : null;
        view.selected = key && view.index[key] ? key : null;
        const box = root.find('.sig-planner-sitebox');
        box.html(view.selected ? siteCard(view.selected) : '');
        box.find('.sig-planner-close').on('click', () => showCard(null));
        if (view.selected) box[0].scrollIntoView({block: 'nearest', behavior: 'smooth'});
    }

    function render(data) {
        view.index = indexSites(data);
        const sites = Object.keys(view.index).sort();
        const s = data.summary;
        const cards = [
            card(__('Committed this week'), s.committed_sites, 'blue'),
            card(__('Overdue TCN'), s.overdue, 'red'),
            card(__('Close to handover'), s.close_to_handover, 'amber'),
            card(__('Ready to batch'), s.ready_to_batch, 'green'),
            card(__('Team-days planned / capacity'), `${s.loaded_team_days} / ${s.capacity_team_days}`, s.over_capacity ? 'red' : 'green'),
            card(__('Lapsed or waiting trips'), s.backlog_trips, 'gray'),
            card(__('No coordinates'), data.has_coordinates ? s.no_coordinates : s.candidates, s.no_coordinates || !data.has_coordinates ? 'red' : 'gray'),
        ].join('');
        const note = data.has_coordinates ? '' :
            `<div class="sig-planner-note">${__('Site coordinates are not loaded yet, so trips cannot be formed.')}</div>`;
        const trips = data.trips.map((trip) => {
            const rows = trip.stops.map((stop) => `<tr class="sig-planner-row" data-site="${esc(stop.site)}">
                <td>${stop.order}</td>
                <td><a href="/app/sig-site-cycle/${encodeURIComponent(stop.cycle)}">${esc(stop.site)}</a></td>
                <td>${esc(stop.project)}</td>
                <td><span class="sig-planner-pill sig-planner-${esc(stop.tier)}">${esc(data.tiers[stop.tier])}</span></td>
                <td>${esc(stop.class || '')}</td><td>${esc(stop.window)}</td><td>${esc(stop.reason)}</td>
                <td class="num">${stop.leg_km == null ? '' : esc(stop.leg_km)}</td></tr>`).join('');
            const title = `${esc(trip.id)} · ${esc(trip.kind)}${trip.anchor ? ' · ' + esc(trip.anchor) : ''}`;
            const base = baseTown(trip);
            const baseText = base ? ` · ${__('Base')}: ${esc(base.t.name)} (${Math.round(base.d)} km)` : '';
            const status = trip.status === 'Scheduled' ? `${__('Team')} ${trip.team} · ${esc(trip.first_day)}`
                : trip.status === 'Lapsed' ? __('Lapsed') : __('Waiting');
            return `<section class="sig-planner-trip ${trip.loaded ? '' : 'sig-planner-backlog'}">
                <header><b>${title}</b><span>${trip.stops.length} ${__('sites')} · ${esc(trip.diameter_km)} km ${__('spread')} ·
                ${esc(trip.hours)} h · ${esc(trip.team_days)} ${__('team-day(s)')} · ${status}${baseText}</span></header>
                <table><thead><tr><th>#</th><th>${__('Site')}</th><th>${__('Project')}</th><th>${__('Priority')}</th>
                <th>${__('Class')}</th><th>${__('TCN window')}</th><th>${__('Why')}</th><th>${__('km')}</th></tr></thead>
                <tbody>${rows}</tbody></table></section>`;
        }).join('');
        const other = data.other.length ? `<section class="sig-planner-trip"><header><b>${__('Not placed')}</b>
            <span>${__('Committed for a later week, or no site coordinates')}</span></header><table><tbody>${
            data.other.map((o) => `<tr class="sig-planner-row" data-site="${esc(o.site)}"><td><a href="/app/sig-site-cycle/${encodeURIComponent(o.cycle)}">${esc(o.site)}</a></td>
                <td>${esc(o.project)}</td><td>${esc(data.tiers[o.tier])}</td><td>${esc(o.kind)}</td>
                <td>${esc(o.window)}</td><td>${esc(o.reason)}</td></tr>`).join('')}</tbody></table></section>` : '';
        root.html(`<div class="sig-planner-cards">${cards}</div>${note}
            <div class="sig-planner-searchbar">
                <input type="search" class="sig-planner-search" list="sig-planner-sites" autocomplete="off"
                    placeholder="${esc(__('Search a site code, e.g. ZDA970'))}">
                <datalist id="sig-planner-sites">${sites.map((x) => `<option value="${esc(x)}">`).join('')}</datalist>
            </div>
            <div class="sig-planner-sitebox"></div>
            <div class="sig-planner-map"></div>${trips}${other}
            <p class="sig-planner-foot">${__('Read-only proposal. Mark a cycle Hold or Visited on its form to keep it out of the plan.')}</p>`);
        root.find('.sig-planner-search').on('input', (e) => {
            const q = String($(e.currentTarget).val() || '').trim().toUpperCase();
            if (view.index[q]) showCard(q);
        }).on('change', (e) => {
            const q = String($(e.currentTarget).val() || '').trim().toUpperCase();
            if (!q) return showCard(null);
            const hit = Object.keys(view.index).find((k) => k.startsWith(q));
            if (hit) showCard(hit);
        });
        root.find('.sig-planner-row').on('click', (e) => {
            if (!$(e.target).is('a')) showCard($(e.currentTarget).attr('data-site'));
        });
        if (data.has_coordinates && data.trips.length) drawMap(data, root.find('.sig-planner-map'));
        showCard(view.selected);
    }

    function load() {
        root.html(`<p class="sig-planner-foot">${__('Loading…')}</p>`);
        const towns = view.townList ? Promise.resolve() : frappe.call({method: 'sig_warehouse.sig_warehouse.field_planner_api.get_reference_towns'})
            .then((r) => { view.townList = r.message || []; }).catch(() => { view.townList = []; });
        towns.then(() => frappe.call({
            method: 'sig_warehouse.sig_warehouse.field_planner_api.get_field_plan', args: filters,
            callback: (r) => render(r.message), error: () => root.html(`<p class="sig-planner-foot">${__('Could not load the field plan.')}</p>`),
        }));
    }
    load();
};
