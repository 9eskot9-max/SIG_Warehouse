frappe.pages['field-planner'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Field Planner'), single_column: true});
    const root = $('<main class="sig-planner-page"></main>').appendTo(page.main);
    const canSeeSetup = (frappe.user_roles || []).some(r => ['System Manager','Operations Manager','Operations User','Projects Manager','SIG Excel Setup Editor'].includes(r));
    const nav = $('<nav class="sig-planner-nav" aria-label="Operations"><a href="#" data-route="projects">Projects</a><a href="#" data-route="cycles">Site Cycles</a><a href="#" data-route="visits">Site Visits</a><a class="active" href="#">Field Planner</a>' + (canSeeSetup ? '<a href="#" data-route="setup">Excel Setup</a>' : '') + '</nav>');
    page.main.prepend(nav);
    nav.find('[data-route="projects"]').on('click', e => { e.preventDefault(); frappe.set_route('List', 'Project'); });
    nav.find('[data-route="cycles"]').on('click', e => { e.preventDefault(); frappe.set_route('site-cycles'); });
    nav.find('[data-route="visits"]').on('click', e => { e.preventDefault(); frappe.set_route('site-visits'); });
    nav.find('[data-route="setup"]').on('click', e => { e.preventDefault(); frappe.set_route('excel-setup'); });
    // Every PM decision list on the page reports here; the choice saves at once.
    root.on('change', '.sig-planner-decide', (e) => decide($(e.currentTarget).attr('data-cycle'), $(e.currentTarget).val()));
    const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const fmtDates = (text) => text.replace(/(\d{4})-(\d{2})-(\d{2})/g, (m, y, mo, d) => `${d}-${MON[Number(mo) - 1]}`);
    const esc = (value) => frappe.utils.escape_html(fmtDates(value == null ? '' : String(value)));
    const filters = {};
    let positionSiteField = null;
    let projectControl = null;
    filters.week_start = frappe.datetime.add_days(frappe.datetime.get_today(), 1);

    // Saudi Arabia outline (lon, lat): Natural Earth 1:110m countries (public domain, via world-atlas); simplified, not a survey boundary.
    const KSA = [[34.95,29.36],[36.07,29.2],[36.5,29.51],[36.74,29.87],[37.5,30.0],[37.67,30.34],[38.0,30.51],[37.0,31.51],[39.0,32.01],[39.2,32.16],[40.4,31.89],[41.89,31.19],[44.71,29.18],[46.57,29.1],[47.46,29.0],[47.71,28.53],[48.42,28.55],[48.81,27.69],[49.3,27.46],[49.47,27.11],[50.15,26.69],[50.21,26.28],[50.11,25.94],[50.24,25.61],[50.53,25.33],[50.66,25.0],[50.81,24.75],[51.11,24.56],[51.39,24.63],[51.58,24.24],[51.62,24.01],[52.0,23.0],[55.01,22.5],[55.21,22.71],[55.67,22.0],[55.0,20.0],[52.0,19.0],[49.12,18.62],[48.18,18.17],[47.47,17.12],[47.0,16.95],[46.75,17.28],[46.37,17.23],[45.4,17.33],[45.22,17.43],[44.06,17.41],[43.79,17.32],[43.38,17.58],[43.12,17.09],[43.22,16.67],[42.78,16.35],[42.65,16.77],[42.35,17.08],[42.27,17.47],[41.76,17.83],[41.22,18.67],[40.94,19.49],[40.25,20.17],[39.8,20.34],[39.14,21.29],[39.02,21.99],[39.07,22.58],[38.49,23.69],[38.03,24.08],[37.49,24.29],[37.15,24.86],[37.21,25.08],[36.93,25.6],[36.64,25.83],[36.25,26.57],[35.64,27.38],[35.13,28.06],[34.63,28.06],[34.79,28.61],[34.83,28.96],[34.95,29.36]];
    const TRIP_COLORS = ['#1e7fff', '#e8590c', '#2b9348', '#9c36b5', '#d6336c', '#0b7285', '#a67c00', '#495057'];
    const TEAM_COLORS = ['#1e7fff', '#e8590c', '#2b9348', '#9c36b5', '#d6336c'];
    const DARK = '#2f3640';
    const TIER_COLORS = {T0: '#1e7fff', T1: '#a4211f', T2: '#c27c00', T3: '#1a7a3d', T4: '#868e96'};
    const ZONE_COLORS = {Riyadh: '#fbe3c4', Qassim: '#dcefc9', Hail: '#e4dcf2', Madinah: '#f9d7d7', Makkah: '#d3e7f7',
        Asir: '#fbf0b8', Jizan: '#cdeeea', Najran: '#f3d9e6', East: '#d9e1f2', North: '#e6e8d2'};
    const BOX0 = [20, 35, 830, 760];
    const SEA = '#e9f1f7', LAND = '#f8faf9', CAPITAL = '#b7791f';
    // Main towns stay on the map at the normal zoom; every other town appears only once zoomed in.
    const MAIN_TOWNS = new Set(['Riyadh', 'Jeddah', 'Makkah', 'Madinah', 'Dammam', 'Al Khobar', 'Al Hofuf', 'Taif', 'Abha',
        'Tabuk', 'Buraydah', 'Hail', 'Najran', 'Jizan', 'Yanbu', 'Al Jubail', 'Arar', 'Sakaka', 'Al Bahah', 'Khamis Mushait',
        'Al Kharj', 'Al Qatif', 'Hafar Albatin', 'Bisha', 'Al Ula', 'Unayzah', 'Rabigh']);
    const NATIONAL_TOWNS = new Set(['Riyadh', 'Jeddah', 'Makkah', 'Madinah', 'Dammam', 'Taif', 'Tabuk', 'Buraydah', 'Abha', 'Hail', 'Najran', 'Al Hofuf']);
    const KM_PER_UNIT = 111.2 / 40;      // project() puts one degree of latitude at 40 units
    const teamName = (n) => (view.teamNames && view.teamNames[n]) || `${__('Team')} ${n}`;
    const view = {mode: 'team', base: 'drawing', extent: 'all', showUnplanned: false, selectedTeam: 1, selected: null, activeTab: 'team', reviewKind: 'all',
        zones: true, towns: true, box: null, leaflet: null, leafletView: null, townList: null, zoneCells: null, teamNames: {}, teamPositions: [], markers: {}};

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
        const px = Math.min(BOX0[2] * 0.35, w * 0.55), py = Math.min(BOX0[3] * 0.35, h * 0.55);
        const x = Math.min(BOX0[0] + BOX0[2] - w + px, Math.max(BOX0[0] - px, box[0]));
        const y = Math.min(BOX0[1] + BOX0[3] - h + py, Math.max(BOX0[1] - py, box[1]));
        return [x, y, w, h];
    }

    // Keep markers and text a readable size whatever the zoom.
    // Bottom-right scale bar: picks a round km length that fits about a fifth of the visible width, so it changes on every zoom.
    function updateScale(svg) {
        const g = svg.querySelector('.sig-planner-scale');
        if (!g) return;
        const [x, y, w, h] = view.box, s = w / BOX0[2], want = w * 0.2 * KM_PER_UNIT;
        const nice = [5, 10, 20, 25, 50, 100, 200, 500].filter((km) => km <= want);
        const km = nice.length ? nice[nice.length - 1] : 5, len = km / KM_PER_UNIT;
        const x1 = x + w - 16 * s - len, yb = y + h - 16 * s;
        g.querySelector('rect').setAttribute('x', x1 - 8 * s); g.querySelector('rect').setAttribute('y', yb - 26 * s);
        g.querySelector('rect').setAttribute('width', len + 16 * s); g.querySelector('rect').setAttribute('height', 32 * s);
        g.querySelector('path').setAttribute('d', `M${x1} ${yb - 9 * s}V${yb}H${x1 + len}V${yb - 9 * s}`);
        g.querySelector('path').setAttribute('stroke-width', 1.6 * s);
        const label = g.querySelector('text');
        label.setAttribute('x', x1 + len / 2); label.setAttribute('y', yb - 12 * s);
        label.setAttribute('font-size', 11 * s); label.textContent = `${km} km`;
    }

    function applyZoom(svg) {
        const scale = BOX0[2] / view.box[2], k = Math.max(0.35, Math.pow(scale, -0.8));
        svg.setAttribute('viewBox', view.box.join(' '));
        svg.classList.toggle('sig-planner-zoomed', scale >= 2.2);
        svg.classList.toggle('sig-planner-very-zoomed', scale >= 4.5);
        svg.querySelectorAll('[data-r]').forEach((e) => e.setAttribute('r', e.dataset.r * k));
        svg.querySelectorAll('[data-mk]').forEach((g) => {
            const emphasis = g.classList.contains('is-selected') ? 2.2 : 1;
            g.setAttribute('transform', `translate(${g.dataset.cx} ${g.dataset.cy}) scale(${k * emphasis})`);
        });
        svg.querySelectorAll('[data-f]').forEach((e) => { e.setAttribute('font-size', e.dataset.f * k); });
        svg.querySelectorAll('[data-w]').forEach((e) => e.setAttribute('stroke-width', e.dataset.w * k));
        updateScale(svg);
        layoutTownLabels(svg, scale);
    }

    function layoutTownLabels(svg, scale) {
        const all = [...svg.querySelectorAll('.sig-planner-cap[data-town]')];
        if (!all.length) return;
        const regional = all.filter((e) => !e.classList.contains('sig-planner-minor'));
        const local = all.filter((e) => e.classList.contains('sig-planner-minor'));
        const eligible = [...all.filter((e) => e.classList.contains('sig-planner-national-town'))];
        if (scale >= 2.2) regional.filter((e) => !eligible.includes(e)).slice(0, 24).forEach((e) => eligible.push(e));
        if (scale >= 4.5) local.slice(0, 40).forEach((e) => eligible.push(e));
        all.forEach((e) => { e.style.visibility = 'hidden'; });
        const accepted = [];
        eligible.forEach((label) => {
            const box = label.getBoundingClientRect();
            if (!box.width || !box.height) return;
            const overlaps = accepted.some((other) => {
                const r = other.getBoundingClientRect();
                return !(box.right + 5 < r.left || box.left - 5 > r.right || box.bottom + 3 < r.top || box.top - 3 > r.bottom);
            });
            if (!overlaps) { label.style.visibility = 'visible'; accepted.push(label); }
        });
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
        (data.team_positions || []).filter((p) => p.state !== 'Incident' && p.lat != null && p.lon != null &&
            (view.extent !== 'team' || p.team_no === view.selectedTeam)).forEach((p) => {
            const color = TEAM_COLORS[((p.team_no || 1) - 1) % TEAM_COLORS.length];
            L.circleMarker([p.lat, p.lon], {radius: 13, color, weight: 3, fillColor: '#fff', fillOpacity: 1,
                dashArray: p.state === 'Stale' ? '4 4' : null})
                .bindTooltip('<b>' + esc(p.team || p.leader) + '</b><br>' + esc(p.site || '') + '<br>' + esc(p.source || ''),
                    {className: 'sig-planner-start-tooltip'}).addTo(map);
            bounds.push([p.lat, p.lon]);
        });
        data.trips.forEach((trip, index) => {
            const hasSelected = trip.stops.some((s) => String(s.cycle) === String(view.selected));
            if ((trip.status !== 'Scheduled' && !view.showUnplanned && !hasSelected) || (view.extent === 'team' && trip.team !== view.selectedTeam)) return;
            const color = trip.status === 'Scheduled' ? TEAM_COLORS[((trip.team || 1) - 1) % TEAM_COLORS.length] : DARK, pts = trip.stops.map((s) => [s.lat, s.lon]);
            if (pts.length > 1) L.polyline(pts, {color, weight: 3, opacity: trip.loaded ? 0.9 : 0.4, dashArray: trip.loaded ? null : '6 6'}).addTo(map);
            trip.stops.forEach((s) => {
                const fill = view.mode === 'tier' ? TIER_COLORS[s.tier] : color;
                const isSelected = String(s.cycle) === String(view.selected);
                L.marker([s.lat, s.lon], {zIndexOffset: isSelected ? 1000 : 0, icon: L.divIcon({className: 'sig-planner-pin-wrap',
                    iconSize: [isSelected ? 34 : 22, isSelected ? 34 : 22], iconAnchor: [isSelected ? 17 : 11, isSelected ? 17 : 11],
                    html: `<div class="sig-planner-pin${isSelected ? ' is-selected' : ''}" style="background:${fill};opacity:${trip.loaded ? 1 : 0.55}">${s.order}</div>`})})
                    .bindTooltip(`${s.site} · ${data.tiers[s.tier]} · ${trip.id} #${s.order}`).on('click', (e) => {
                        L.DomEvent.stopPropagation(e); $(root).trigger('sig-planner-select', [s.cycle, false]);
                    }).addTo(map);
                bounds.push([s.lat, s.lon]);
            });
        });
        (data.other || []).filter((o) => (view.showUnplanned || String(o.cycle) === String(view.selected)) && o.lat != null && o.lon != null).forEach((o) => {
            L.circleMarker([o.lat, o.lon], {radius: String(o.cycle) === String(view.selected) ? 9 : 4,
                color: String(o.cycle) === String(view.selected) ? '#183247' : '#fff', weight: String(o.cycle) === String(view.selected) ? 3 : 1,
                fillColor: DARK, fillOpacity: .65})
                .bindTooltip((o.site || '') + ' · ' + (o.reason || o.kind)).on('click', (e) => {
                    L.DomEvent.stopPropagation(e); $(root).trigger('sig-planner-select', [o.cycle, false]);
                }).addTo(map);
            bounds.push([o.lat, o.lon]);
        });
        if (view.towns && view.townList) view.townList.forEach((t) =>
            L.circleMarker([t.lat, t.lon], {radius: 3, color: '#6b7785', weight: 1, fillOpacity: 0.7}).bindTooltip(`${t.name} · ${t.zone}`).addTo(map));
        map.on('click', () => $(root).trigger('sig-planner-clear-selection'));
        if (view.locateCycle) {
            const hit = view.index && view.index.byCycle[view.locateCycle], item = hit && (hit.stop || hit.other);
            if (item && item.lat != null && item.lon != null) {
                const currentZoom = Number(map.getZoom());
                const targetZoom = Number.isFinite(currentZoom) ? Math.max(currentZoom, 8) : 8;
                map.setView([item.lat, item.lon], targetZoom, {animate: true});
                view.locateCycle = null;
            }
        } else if (view.fitTeam && bounds.length) { map.fitBounds(bounds, {padding: [35, 35], maxZoom: 8}); view.fitTeam = false; }
        else if (view.leafletView) map.setView(view.leafletView.center, view.leafletView.zoom);
        else if (bounds.length) map.fitBounds(bounds, {padding: [20, 20]}); else map.setView([24.5, 45], 6);
        setTimeout(() => map.invalidateSize(), 50);
    }

    function drawMap(data, mount) {
        if (view.cameraAnimation) { cancelAnimationFrame(view.cameraAnimation); view.cameraAnimation = null; }
        if (view.dragCleanup) { view.dragCleanup(); view.dragCleanup = null; }
        if (view.leaflet) {
            const center = view.leaflet.getCenter();
            view.leafletView = {center: [center.lat, center.lng], zoom: view.leaflet.getZoom()};
            view.leaflet.remove(); view.leaflet = null;
        }
        view.box = view.box || BOX0.slice();
        const street = view.base === 'street' && typeof L !== 'undefined';
        const tripNode = (trip) => {
            const hasSelected = trip.stops.some((s) => String(s.cycle) === String(view.selected));
            if ((trip.status !== 'Scheduled' && !view.showUnplanned && !hasSelected) ||
                (view.extent === 'team' && trip.team !== view.selectedTeam)) return {line: '', dots: '', labels: ''};
            const scheduled = trip.status === 'Scheduled';
            const teamColor = TEAM_COLORS[((trip.team || 1) - 1) % TEAM_COLORS.length];
            const pts = trip.stops.map((stop) => project(stop.lon, stop.lat));
            let line = '', dots = '', labels = '';
            if (pts.length > 1 && scheduled) {
                line = `<polyline points="${pts.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${teamColor}" stroke-width="2" stroke-opacity="0.85" data-w="2"/>`;
            }
            trip.stops.forEach((stop, i) => {
                const [x, y] = pts[i];
                const fill = !scheduled ? (trip.status === 'Waiting' ? '#ffffff' : DARK)
                    : (view.mode === 'tier' ? TIER_COLORS[stop.tier] : teamColor);
                const ring = !scheduled ? (stop.must ? '#a4211f' : DARK) : '#ffffff';
                const ringWidth = !scheduled ? (stop.must ? 2.5 : (trip.status === 'Waiting' ? 2 : 1)) : 1.5;
                const tip = `<title>${esc(stop.site)} · ${esc(data.tiers[stop.tier])} · ${esc(trip.id)} #${stop.order}\n${esc(stop.reason)}</title>`;
                const size = scheduled ? 5 : 3.5;
                const op = scheduled ? 1 : 0.5;
                const shape = stop.kind === 'Committed'
                    ? `<rect x="-${size}" y="-${size}" width="${size * 2}" height="${size * 2}" fill="${fill}" fill-opacity="${op}" stroke="${ring}" stroke-width="${ringWidth}">${tip}</rect>`
                    : `<circle r="${size}" fill="${fill}" fill-opacity="${op}" stroke="${ring}" stroke-width="${ringWidth}">${tip}</circle>`;
                const label = scheduled ? `<text y="2.5" text-anchor="middle" font-size="7" fill="#fff" pointer-events="none">${stop.order}</text>` : '';
                dots += `<g class="sig-planner-mk${String(stop.cycle) === String(view.selected) ? ' is-selected' : ''}" data-mk data-site="${esc(stop.site)}" data-cycle="${esc(stop.cycle)}" data-cx="${x}" data-cy="${y}" tabindex="0" role="button" aria-label="${esc(stop.site)}">${shape}${label}</g>`;
            });
            return {line, dots, labels};
        };
        let lines = '', dots = '', labels = '';
        const extraDots = data.other.filter((o) => o.lat != null && (view.showUnplanned || String(o.cycle) === String(view.selected))).map((o) => {
            const [x, y] = project(o.lon, o.lat);
            return `<g class="sig-planner-mk${String(o.cycle) === String(view.selected) ? ' is-selected' : ''}" data-mk data-site="${esc(o.site)}" data-cycle="${esc(o.cycle)}" data-cx="${x}" data-cy="${y}" tabindex="0" role="button" aria-label="${esc(o.site)}"><circle r="4" fill="${DARK}" fill-opacity="0.65" stroke="#fff" stroke-width="1"><title>${esc(o.site)} · ${esc(o.reason)}</title></circle></g>`;
        }).join('');
        // Unplanned sites are drawn first, underneath, so the planned teams stay on top and clickable.
        if (!street) {
            const ordered = [...data.trips].sort((a, b) => (a.status === 'Scheduled') - (b.status === 'Scheduled'));
            dots += extraDots;
            ordered.forEach((trip) => { const n = tripNode(trip); lines += n.line; dots += n.dots; labels += n.labels; });
        }
        const outline = KSA.map(([lon, lat]) => project(lon, lat).join(',')).join(' ');
        // Capitals and Jeddah are always drawn (also at the furthest zoom), in a colour apart from the planned sites.
        const townDots = (view.towns && view.townList) ? view.townList.map((t) => {
            const [x, y] = project(t.lon, t.lat), big = t.name === 'Jeddah', minor = MAIN_TOWNS.has(t.name) ? '' : ' sig-planner-minor', national = NATIONAL_TOWNS.has(t.name) ? ' sig-planner-national-town' : '';
            return `<circle class="sig-planner-cap-dot${minor}${national}" data-r="${big ? 3.6 : 2.6}" cx="${x}" cy="${y}" r="${big ? 3.6 : 2.6}" fill="${CAPITAL}" stroke="#fff" stroke-width="0.6" data-w="0.6" data-town-x="${x}" data-town-y="${y}"><title>${esc(t.name)} · ${esc(t.zone)}</title></circle>` +
                `<text class="sig-planner-cap${minor}${national}" data-f="${big ? 8 : 6.5}" data-town="${esc(t.name)}" data-town-x="${x}" data-town-y="${y}" x="${x + 4}" y="${y - 3}" font-size="12" font-weight="${big ? 700 : 400}" fill="#7a4e12" pointer-events="none">${esc(t.name)}</text>`;
        }).join('') : '';
        const zones = view.zones && view.townList ? `<g clip-path="url(#sigksa)">${zoneCells()}</g>` : '';
        const teamsUsed = [...new Set(data.trips.filter((t) => t.status === 'Scheduled').map((t) => t.team))].sort((x, y) => x - y);
        const legend = view.mode === 'tier'
            ? Object.keys(TIER_COLORS).map((tier) => `<span><i style="background:${TIER_COLORS[tier]}"></i>${esc(data.tiers[tier])}</span>`).join('')
            : teamsUsed.map((t) => `<span><i style="background:${TEAM_COLORS[(t - 1) % TEAM_COLORS.length]}"></i>${esc(teamName(t))}</span>`).join('')
              + `<span><i style="background:${DARK}"></i>${__('Not planned')}</span>`;
        const zoneLegend = (!street && view.zones && view.townList)
            ? Object.keys(ZONE_COLORS).map((z) => `<span><i class="sq" style="background:${ZONE_COLORS[z]}"></i>${esc(z)}</span>`).join('') : '';
        const btn = (attr, label, on) => `<button class="btn btn-xs ${on ? 'btn-primary' : 'btn-default'}" ${attr}>${label}</button>`;
        mount.html(`<div class="sig-planner-maptools">
            ${btn('data-base="drawing"', __('Drawing'), !street)}${btn('data-base="street"', __('Street map'), street)}
            ${btn('data-mode="team"', __('By team'), view.mode === 'team')}${btn('data-mode="tier"', __('By priority'), view.mode === 'tier')}
            ${btn('data-toggle="towns"', __('Towns'), view.towns)}${street ? '' : btn('data-toggle="zones"', __('Zones'), view.zones)}
            ${street ? '' : `<span class="sig-planner-zoom"><button class="btn btn-xs btn-default" data-zoom="in">+</button>
                <button class="btn btn-xs btn-default" data-zoom="out">&minus;</button>
                <button class="btn btn-xs btn-default" data-zoom="reset">${__('Reset')}</button></span>`}
            <span class="sig-planner-legend">${legend}</span></div>
            ${zoneLegend ? `<details class="sig-planner-zones"><summary>${__('Planning zone colours · approximate areas')}</summary><div class="sig-planner-zone-items">${zoneLegend}</div></details>` : ''}
            ${street ? '<div class="sig-planner-leaflet"></div>'
                : `<svg viewBox="${view.box.join(' ')}" class="sig-planner-svg" preserveAspectRatio="xMidYMid meet">
                <defs><clipPath id="sigksa"><polygon points="${outline}"/></clipPath></defs>
                <rect x="${BOX0[0]}" y="${BOX0[1]}" width="${BOX0[2]}" height="${BOX0[3]}" fill="${SEA}"/>
                <polygon points="${outline}" fill="${LAND}"/>${zones}
                <polygon points="${outline}" fill="none" stroke="#9db4c9" stroke-width="1.5" data-w="1.5"/>${townDots}${lines}${dots}${labels}
                <g class="sig-planner-scale" pointer-events="none"><rect fill="#ffffff" fill-opacity="0.85"/><path fill="none" stroke="#33414f"/><text fill="#33414f" text-anchor="middle"></text></g></svg>`}
            <div class="sig-planner-foot">${street
                ? __('Street map tiles come from OpenStreetMap and need internet. Pins show visiting order.')
                : __('Colour = team that visits; dark = not planned this week; amber = town/capital (always shown); click a site for details. Zones follow the nearest reference town; outline is schematic. Ctrl + scroll or pinch to zoom, drag to pan, double-click to zoom in.')}</div>`);
        if (!street) {
            const svg = mount.find('svg')[0], ns = 'http://www.w3.org/2000/svg';
            (data.team_positions || []).filter((p) => p.state !== 'Incident' && p.lat != null && p.lon != null &&
                (view.extent !== 'team' || p.team_no === view.selectedTeam)).forEach((p) => {
                const [x, y] = project(p.lon, p.lat), c = document.createElementNS(ns, 'circle');
                c.setAttribute('cx', x); c.setAttribute('cy', y); c.setAttribute('r', 8);
                c.setAttribute('fill', '#fff'); c.setAttribute('stroke', TEAM_COLORS[((p.team_no || 1) - 1) % TEAM_COLORS.length]);
                c.setAttribute('stroke-width', '2.5'); c.setAttribute('class', 'sig-planner-position-ring');
                const title = document.createElementNS(ns, 'title'); title.textContent = (p.team || p.leader) + ' · ' + (p.site || '');
                c.appendChild(title); svg.appendChild(c);
            });
        }
        mount.find('[data-base]').on('click', (e) => { view.base = $(e.currentTarget).data('base'); drawMap(data, mount); });
        mount.find('[data-mode]').on('click', (e) => { view.mode = $(e.currentTarget).data('mode'); drawMap(data, mount); });
        mount.find('[data-toggle]').on('click', (e) => { const k = $(e.currentTarget).data('toggle'); view[k] = !view[k]; drawMap(data, mount); });
        // Map selection is handled by the shared cycle-based handler in renderFull.
        if (street) { drawStreetMap(data, mount); return; }
        const svg = mount.find('svg')[0];
        const selectedMarker = svg.querySelector('.sig-planner-mk.is-selected');
        if (selectedMarker) selectedMarker.parentNode.appendChild(selectedMarker);
        applyZoom(svg);
        mount.find('[data-zoom]').on('click', (e) => {
            const z = $(e.currentTarget).data('zoom');
            if (z === 'reset') { view.box = BOX0.slice(); applyZoom(svg); } else zoomBy(svg, z === 'in' ? 0.6 : 1 / 0.6);
        });
        let drag = null, suppressMapClick = false;
        svg.addEventListener('click', (e) => {
            if (suppressMapClick) { suppressMapClick = false; e.preventDefault(); e.stopPropagation(); return; }
            if (!e.target.closest('[data-cycle]')) $(root).trigger('sig-planner-clear-selection');
        });
        svg.addEventListener('keydown', (e) => {
            if ((e.key === 'Enter' || e.key === ' ') && e.target.closest('[data-cycle]')) {
                e.preventDefault(); $(root).trigger('sig-planner-select', [e.target.closest('[data-cycle]').getAttribute('data-cycle'), false]);
            } else if (e.key === 'Escape' && view.selected) $(root).trigger('sig-planner-clear-selection');
        });
        const point = (e) => {
            const r = svg.getBoundingClientRect(), [x, y, w, h] = view.box, scale = Math.min(r.width / w, r.height / h);
            const drawnW = w * scale, drawnH = h * scale, left = r.left + (r.width - drawnW) / 2, top = r.top + (r.height - drawnH) / 2;
            return [x + (e.clientX - left) / scale, y + (e.clientY - top) / scale];
        };
        svg.addEventListener('wheel', (e) => {
            if (!(e.ctrlKey || e.metaKey)) return;                // plain scrolling keeps moving the page
            e.preventDefault();
            const d = Math.max(-50, Math.min(50, e.deltaY));      // a touchpad can fire huge deltas
            const [px, py] = point(e);
            zoomBy(svg, Math.exp(d * 0.008), px, py);
        }, {passive: false});
        svg.addEventListener('dblclick', (e) => { const [px, py] = point(e); zoomBy(svg, 0.5, px, py); });
        svg.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            const r = svg.getBoundingClientRect(), [x, y, w, h] = view.box, scale = Math.min(r.width / w, r.height / h);
            drag = {x: e.clientX, y: e.clientY, box: view.box.slice(), unitsPerPixel: 1 / scale};
        });
        const onMapMouseUp = () => {
            drag = null;
            if (suppressMapClick) setTimeout(() => { suppressMapClick = false; }, 0);
            window.removeEventListener('mouseup', onMapMouseUp);
            view.dragCleanup = null;
        };
        window.addEventListener('mouseup', onMapMouseUp);
        view.dragCleanup = () => window.removeEventListener('mouseup', onMapMouseUp);
        svg.addEventListener('mousemove', (e) => {
            if (!drag) return;
            if (!e.buttons) { drag = null; return; }              // button was released outside the map
            if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 5) suppressMapClick = true;
            view.box = clampBox([drag.box[0] - (e.clientX - drag.x) * drag.unitsPerPixel,
                drag.box[1] - (e.clientY - drag.y) * drag.unitsPerPixel, drag.box[2], drag.box[3]]);
            applyZoom(svg);
        });
    }

    function card(label, value, tone) {
        return `<div class="sig-planner-card sig-planner-${tone}"><div class="num">${esc(value)}</div><div class="lbl">${esc(label)}</div></div>`;
    }

    function indexSites(data) {
        const idx = {}, cycles = {};
        data.trips.forEach((trip) => trip.stops.forEach((stop) => {
            const key = String(stop.site || '').toUpperCase(), hit = {stop, trip, data};
            if (key) (idx[key] || (idx[key] = [])).push(hit);
            if (stop.cycle) cycles[stop.cycle] = hit;
        }));
        data.other.forEach((o) => {
            const key = String(o.site || '').toUpperCase(), hit = {other: o, data};
            if (key && !idx[key]) idx[key] = [];
            if (key) idx[key].push(hit);
            if (o.cycle && !cycles[o.cycle]) cycles[o.cycle] = hit;
        });
        return {bySite: idx, byCycle: cycles};
    }

    function hitForSite(site) {
        const hits = view.index && view.index.bySite[String(site || '').toUpperCase()];
        return hits && hits[0];
    }

    // Team nearest to an unplanned site: the closest stop of a scheduled trip.
    function nearestTeam(site, data, cycle) {
        const me = cycle && view.index && view.index.byCycle[String(cycle)] || hitForSite(site);
        const point = me && (me.stop || me.other);
        if (!point || point.lat == null || point.lon == null) return null;
        let best = null;
        data.trips.forEach((t) => {
            if (t.status !== 'Scheduled') return;
            t.stops.forEach((st) => {
                const d = km([point.lat, point.lon], [st.lat, st.lon]);
                if (!best || d < best.km) best = {km: d, team: t.team, day: t.first_day};
            });
        });
        return best;
    }

    const DECISIONS = [['', '—'], ['Must', 'Must'], ['Hold', 'Hold (30 days)'], ['Remove', 'Remove']];
    function decisionSelect(cycle, current) {
        return `<select class="sig-planner-decide" data-cycle="${esc(cycle)}" aria-label="${esc(__('PM decision'))}">${
            DECISIONS.map(([v, label]) => `<option value="${v}"${v === (current || '') ? ' selected' : ''}>${esc(label)}</option>`).join('')}</select>`;
    }

    // A PM decision saves at once and is logged; the plan refreshes. No confirm step.
    function decide(cycle, action) {
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.field_planner_api.set_plan_decision',
            args: {cycle: cycle, action: action || '', reason: ''},
            callback: () => { frappe.show_alert({message: action ? `${action} saved` : __('Decision cleared'), indicator: 'green'}, 3); load(); },
            error: () => frappe.show_alert({message: __('Could not save the decision'), indicator: 'red'}, 5),
        });
    }

    function renderFull(data) {
        const stats = data.summary || {};
        const projectPositions = (data.team_positions || []).filter((p) => p.state !== 'Incident');
        const numbers = new Map(projectPositions.map((p, i) => [p.leader, i + 1]));
        view.teamPositions = (data.team_positions || []).map((p) => Object.assign(p, {team_no: numbers.get(p.leader) || null}));
        view.teams = projectPositions.map((p, i) => ({team: i + 1, leader: p.team || p.leader, leader_id: p.leader}));
        view.teamNames = Object.fromEntries(view.teams.map((t) => [t.team, t.leader]));
        view.data = data;
        view.index = indexSites(data);
        data.rows = [];
        data.trips.forEach((trip) => trip.stops.forEach((stop) => {
            Object.assign(stop, {trip_id: trip.id, trip_status: trip.status, team: trip.team, first_day: trip.first_day,
                last_day: trip.last_day, trip_hours: trip.hours, trip_area: '', project_ref: stop.project || '',
                project_title: stop.project || '', po: String(stop.cycle || '').split('|')[1] || ''});
            data.rows.push(stop);
        }));
        data.other.forEach((r) => data.rows.push(Object.assign(r, {trip_id: '', trip_status: r.kind || 'Unplaced', team: null,
            day: '', first_day: '', last_day: '', trip_hours: null, project_ref: r.project || '', project_title: r.project || '',
            po: String(r.cycle || '').split('|')[1] || ''})));
        view.rows = data.rows;
        if (!view.selectedTeam || !view.teamNames[view.selectedTeam]) view.selectedTeam = view.teams.length ? view.teams[0].team : 1;
        const horizon = workDates(data.summary.week_start, data.params.work_days || 5);
        const assigned = () => view.rows.filter((r) => r.trip_status === 'Scheduled');
        const backlog = () => view.rows.filter((r) => r.trip_status !== 'Scheduled');
        const teamRows = (n) => assigned().filter((r) => Number(r.team) === Number(n));
        const teamTrips = (n) => data.trips.filter((t) => t.status === 'Scheduled' && Number(t.team) === Number(n));
        const selected = () => view.rows.find((r) => r.cycle === view.selected) || assigned()[0] || view.rows[0];
        const statusFor = (r) => {
            if (r.tier === 'T1') return {label: __('TCN overdue'), cls: 'overdue', line: __('No completed visit in the TCN window')};
            if (r.tier === 'T0') return {label: __('TCN linked'), cls: 'tcn', line: __('TCN window') + ' · ' + (r.window || '—')};
            if (r.tier === 'T3') return {label: __('Ready to batch'), cls: 'ready', line: __('MIR ready · no current TCN')};
            if (r.tier === 'T2') return {label: __('Handover follow-up'), cls: 'mismatch', line: __('Tags / handover readiness')};
            return {label: data.tiers[r.tier] || r.tier || __('Review'), cls: '', line: r.reason || ''};
        };
        const statusBadge = (r) => { const s = statusFor(r); return '<span class="sig-planner-status ' + s.cls + '">' + esc(s.label) + '</span>'; };
        const decisionBadge = (r) => r.decision ? '<span class="sig-planner-status decision">' + esc(r.decision) + '</span>' : '';
        const decisionControl = (r) => '<label class="sig-planner-choice">' + __('PM decision') + '<select class="sig-planner-decide" data-cycle="' +
            esc(r.cycle) + '">' + [['', __('Automatic')], ['Must', __('Must · 14 days')], ['Hold', __('Hold · 30 days')], ['Remove', __('Remove')]]
                .map(([v, label]) => '<option value="' + v + '"' + (r.decision === v ? ' selected' : '') + '>' + esc(label) + '</option>').join('') +
            '</select></label>';
        const canUpdatePosition = () => (frappe.user_roles || []).some((r) => ['Projects Manager', 'System Manager'].includes(r));
        const currentPosition = (n) => view.teamPositions.find((p) => Number(p.team_no) === Number(n));
        const teamPositionSummary = (p) => !p ? __('No position reported') :
            p.state === 'Incident' ? __('Incident team · not planned') : !p.site ? __('No position reported') :
                p.state === 'Stale' ? __('Last site: ') + p.site + ' · ' + __('not used') : __('Start: ') + p.site;
        const positionName = (p) => p && (p.team || p.leader) || '';
        const positionState = (p) => !p ? __('No position report') : p.state === 'Incident' ? __('Incident team · not planned') :
            p.state === 'Stale' ? __('Old position · not used') : p.site && (p.lat == null || p.lon == null) ?
                __('Site has no usable coordinates') : p.site ? __('Current starting point') : __('No visit or position report');
        const hasPoint = (r) => r && r.lat != null && r.lon != null && Number(r.lat) !== 0 && Number(r.lon) !== 0;
        const leaderFor = (n) => view.teamNames[n] || __('Team') + ' ' + n;
        const openPosition = (n) => {
            if (!canUpdatePosition()) return;
            const options = view.teamPositions.filter((p) => p.state !== 'Incident' && p.leader);
            if (!options.length) return;
            const current = currentPosition(n || view.selectedTeam) || options[0];
            const d = new frappe.ui.Dialog({
                title: __('Update team position'),
                fields: [
                    {fieldtype: 'Select', fieldname: 'team_leader', label: __('Team'), options: options.map((p) => p.leader + ' | ' + positionName(p)),
                        default: current.leader + ' | ' + positionName(current), reqd: 1},
                    {fieldtype: 'Link', fieldname: 'site', label: __('Current site'), options: 'SIG Site', reqd: 1},
                    {fieldtype: 'HTML', fieldname: 'note', options: '<p class="text-muted">' +
                        __('This updates the planner starting point. It does not create a visit or mark work complete.') + '</p>'},
                ],
                primary_action_label: __('Update position'),
                primary_action(values) {
                    const leader = String(values.team_leader || '').split(' | ')[0];
                    d.get_primary_btn().prop('disabled', true);
                    frappe.call({method: 'sig_warehouse.sig_warehouse.field_planner_api.update_team_position',
                        args: {team_leader: leader, site: values.site},
                        callback: (r) => { d.hide(); frappe.show_alert({message: __('Position updated for {0}; plan recalculated.', [r.message.team]), indicator: 'green'}, 5); load(); },
                        error: () => d.get_primary_btn().prop('disabled', false),
                    });
                },
            });
            d.show();
        };
        const openSettings = () => {
            const d = new frappe.ui.Dialog({
                title: __('Planning settings'),
                fields: [
                    {fieldtype: 'Date', fieldname: 'week_start', label: __('Plan starts'), default: filters.week_start, reqd: 1},
                    {fieldtype: 'Int', fieldname: 'teams', label: __('Project teams (blank uses Setup)'), default: filters.teams || data.params.teams},
                    {fieldtype: 'Float', fieldname: 'scope_hours', label: __('Hours per site'), default: filters.scope_hours || data.params.scope_hours},
                    {fieldtype: 'Float', fieldname: 'diameter_km', label: __('Trip diameter · km'), default: filters.diameter_km || data.params.diameter_km},
                    {fieldtype: 'HTML', fieldname: 'day_length', options: '<p class="text-muted">' +
                        __('Workday length: {0} hours, controlled by planner setup.', [esc(data.params.day_hours)]) + '</p>'},
                ],
                primary_action_label: __('Recalculate plan'),
                primary_action(v) {
                    filters.week_start = v.week_start;
                    filters.teams = v.teams || '';
                    filters.scope_hours = v.scope_hours || '';
                    filters.diameter_km = v.diameter_km || '';
                    d.hide(); load();
                },
            });
            d.show();
        };
        const projectLink = (r) => '/app/sig-site-cycle/' + encodeURIComponent(r.cycle || '');
        const renderPositionRows = () => view.teamPositions.map((p) => {
            const n = Number(p.team_no) || 0, c = n ? TEAM_COLORS[(n - 1) % TEAM_COLORS.length] : '#8997a1';
            return '<tr><td><span class="sig-planner-team-label" style="--team:' + c + '"><i></i>' + esc(positionName(p)) + '</span></td><td>' +
                esc(p.site || '—') + '</td><td>' + esc(p.seen_at || '—') + '</td><td>' + esc(p.source || '—') + '</td><td>' +
                esc(positionState(p)) + '</td><td>' + (p.state !== 'Incident' && canUpdatePosition() ?
                    '<button type="button" class="btn btn-default btn-xs sig-planner-position-update" data-team-no="' + n + '">' + __('Update') + '</button>' : '') +
                '</td></tr>';
        }).join('');
        projectControl = null;
        root.html('<div class="sig-planner-shell">' +
            '<section class="sig-planner-toolbar"><div><span class="sig-planner-eyebrow">SIG OPERATIONS</span><h2>' + __('Plan for tomorrow') +
            '</h2><p>' + esc(fmtDates(horizon[0] || '')) + ' – ' + esc(fmtDates(horizon[horizon.length - 1] || '')) +
            '</p></div><div class="sig-planner-controls">' +
            '<label>' + __('Plan starts') + '<input type="date" readonly value="' + esc(filters.week_start) + '"></label>' +
            '<label class="sig-planner-project-control">' + __('Project / PO') + '<div class="sig-planner-project-link"></div></label>' +
            '<button type="button" class="btn btn-default" data-action="settings">' + __('Planning settings') + '</button>' +
            '<button type="button" class="btn btn-primary" data-action="refresh">' + __('Refresh') + '</button></div></section>' +
            '<div class="sig-planner-metrics" id="sig-planner-metrics"></div>' +
            '<section class="sig-planner-teams" id="sig-planner-teams"></section><section class="sig-planner-context"><div><div class="sig-planner-context-title">' +
            '<i id="sig-planner-team-dot"></i><h3 id="sig-planner-team-name"></h3></div><p id="sig-planner-team-context"></p></div>' +
            (canUpdatePosition() ? '<button type="button" class="btn btn-default sig-planner-update-main" data-action="position">' + __('Update position') + '</button>' : '') +
            '</section><section class="sig-planner-map-card"><div class="sig-planner-live-map-controls">' +
            '<div class="sig-planner-map-segment"><button data-map-base="street" aria-pressed="' + (view.base === 'street') + '">' + __('Road map') +
            '</button><button data-map-base="drawing" aria-pressed="' + (view.base === 'drawing') + '">' + __('Drawing') + '</button></div>' +
            '<div class="sig-planner-map-segment"><button data-map-mode="team" aria-pressed="' + (view.mode === 'team') + '">' + __('By team') +
            '</button><button data-map-mode="tier" aria-pressed="' + (view.mode === 'tier') + '">' + __('By priority') + '</button></div>' +
            '<div class="sig-planner-map-segment"><button data-map-extent="all" aria-pressed="' + (view.extent === 'all') + '">' + __('All teams') +
            '</button><button data-map-extent="team" aria-pressed="' + (view.extent === 'team') + '">' + __('Focus selected team') + '</button></div>' +
            '<button data-map-unplanned="1" aria-pressed="' + view.showUnplanned + '">' + __('Unplaced sites') + '</button>' +
            '<button data-map-towns="1" aria-pressed="' + view.towns + '">' + __('Town references') + '</button>' +
            '<button data-map-zones="1" aria-pressed="' + view.zones + '">' + __('Planning zones') + '</button>' +
            (view.base === 'drawing' ? '<div class="sig-planner-map-segment"><button data-map-zoom="in" aria-label="' + __('Zoom in') + '">+</button>' +
                '<button data-map-zoom="out" aria-label="' + __('Zoom out') + '">−</button>' +
                '<button data-map-zoom="reset">' + __('Reset map') + '</button></div>' : '') +
            '<div class="sig-planner-map-searchbar"><label class="sig-planner-search-label" for="sig-planner-site-search">' + __('Find a site in this plan') + '</label>' +
            '<div class="sig-planner-search"><input id="sig-planner-site-search" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="sig-planner-site-suggestions" ' +
            'aria-label="' + __('Find a site in this plan') + '" placeholder="' + __('Site, project, or PO') + '"><button type="button" data-action="clear-site-search" aria-label="' + __('Clear search and selection') + '">×</button>' +
            '<div id="sig-planner-site-suggestions" class="sig-planner-suggest" role="listbox"></div></div>' +
            '<span class="sig-planner-map-key">' + __('Ring = reported start · numbered pin = proposed stop') + '</span>' +
            '<button type="button" class="sig-planner-expand" data-action="toggle-map-size">' + __('Expand map') + '</button></div></div>' +
            '<div class="sig-planner-mapbody"></div><div class="sig-planner-sitebox"></div></section>' +
            '<div class="sig-planner-tabs" role="tablist"><button role="tab" data-tab="team" aria-selected="true">' + __('Team plan') +
            '</button><button role="tab" data-tab="overall" aria-selected="false">' + __('Overall schedule') + ' <span id="sig-planner-schedule-count"></span></button>' +
            '<button role="tab" data-tab="review" aria-selected="false">' + __('Unplaced & review') + ' <span id="sig-planner-review-count"></span></button>' +
            '<button role="tab" data-tab="positions" aria-selected="false">' + __('Team positions') + '</button></div>' +
            '<details class="sig-planner-rules"><summary>' + __('PM override rules') + '</summary><p><b>Must</b> ' + __('prioritizes work for 14 days or until a visit.') +
            ' <b>Hold</b> ' + __('excludes work for 30 days.') + ' <b>Remove</b> ' + __('keeps it out until cleared.') + ' ' +
            __('Automatic clears the override. A new TCN can restore held or removed work.') + '</p></details>' +
            '<section data-panel="team" class="sig-planner-panel"><div class="sig-planner-panel-heading"><div><h3 id="sig-planner-team-plan-title"></h3><p>' +
            __('Proposed visits in travel order. Arrival times are not calculated.') + '</p></div><span id="sig-planner-team-estimate"></span></div><div id="sig-planner-team-trips"></div></section>' +
            '<section data-panel="overall" class="sig-planner-panel" hidden><div class="sig-planner-panel-heading"><div><h3>' + __('All project teams · five working days') +
            '</h3><p>' + __('Compare teams, then review every proposed visit and decision.') + '</p></div><button type="button" data-action="clear-schedule">' + __('Clear filters') +
            '</button></div><div class="sig-planner-table-wrap"><table id="sig-planner-matrix" class="sig-planner-matrix"></table></div>' +
            '<div class="sig-planner-list-toolbar"><label>' + __('Team') + '<select id="sig-planner-filter-team"></select></label><label>' + __('Day') +
            '<select id="sig-planner-filter-day"></select></label><label class="grow">' + __('Find site / Project') + '<input id="sig-planner-filter-search" type="search"></label>' +
            '<span id="sig-planner-schedule-range"></span></div><div class="sig-planner-table-wrap"><table class="sig-planner-schedule"><thead><tr><th>' +
            __('Proposed day') + '</th><th>' + __('Team') + '</th><th>' + __('Site / Project') + '</th><th>' + __('Readiness / TCN') + '</th><th>' +
            __('Trip') + '</th><th>' + __('PM decision') + '</th></tr></thead><tbody id="sig-planner-schedule-rows"></tbody></table></div></section>' +
            '<section data-panel="review" class="sig-planner-panel" hidden><div class="sig-planner-panel-heading"><div><h3>' + __('Unplaced work & review') +
            '</h3><p>' + __('Includes unplaced work and sites without usable coordinates.') + '</p></div></div><div id="sig-planner-review-filters" class="sig-planner-review-filters"></div>' +
            '<div class="sig-planner-list-toolbar"><label class="grow">' + __('Find site / Project') + '<input id="sig-planner-review-search" type="search"></label>' +
            '<span id="sig-planner-review-range"></span></div><div class="sig-planner-table-wrap"><table class="sig-planner-review"><thead><tr><th>' +
            __('Site / Project') + '</th><th>' + __('Planning state') + '</th><th>' + __('Readiness / TCN') + '</th><th>' + __('Nearest team') +
            '</th><th>' + __('PM decision') + '</th></tr></thead><tbody id="sig-planner-review-rows"></tbody></table></div></section>' +
            '<section data-panel="positions" class="sig-planner-panel" hidden><div class="sig-planner-panel-heading"><div><h3>' + __('Latest team positions') +
            '</h3><p>' + __('Posted visits, WhatsApp reports and PM updates remain separately identified.') + '</p></div></div><div class="sig-planner-table-wrap">' +
            '<div class="sig-planner-position-table"><table class="sig-planner-positions"><thead><tr><th>' + __('Team') + '</th><th>' + __('Last site') + '</th><th>' + __('Last seen · Riyadh') +
            '</th><th>' + __('Source') + '</th><th>' + __('Position status') + '</th><th></th></tr></thead><tbody>' + renderPositionRows() + '</tbody></table></div></div></section>' +
            '<footer class="sig-planner-footer"><span>' + esc(stats.visited_cycles_dismissed || 0) + ' ' + __('visited cycles excluded · Incident teams are not scheduled') +
            '</span><span>' + __('Road connections are proposed sequence, not calculated driving routes.') + '</span></footer></div>');

        projectControl = frappe.ui.form.make_control({parent: root.find('.sig-planner-project-link')[0],
            df: {fieldname: 'planner_project', label: __('Project'), fieldtype: 'Link', options: 'Project',
                change() {
                    const value = this.get_value() || '';
                    if (value !== (filters.project || '')) { filters.project = value; view.selected = null; load(); }
                }}, only_input: true});
        projectControl.refresh();
        if (filters.project) projectControl.set_value(filters.project);
        root.find('#sig-planner-metrics').html([
            card(__('Committed this week'), stats.committed_sites || 0, 'blue'),
            card(__('Overdue TCN'), stats.overdue || 0, 'red'),
            card(__('Close to handover'), stats.close_to_handover || 0, 'amber'),
            card(__('Ready to batch'), stats.ready_to_batch || 0, 'green'),
            card(__('Team-days planned / capacity'), (stats.loaded_team_days || 0) + ' / ' + (stats.capacity_team_days || 0), stats.over_capacity ? 'red' : 'green'),
            card(__('Lapsed or waiting trips'), stats.backlog_trips || 0, 'gray'),
            card(__('No coordinates'), data.has_coordinates ? (stats.no_coordinates || 0) : (stats.candidates || 0),
                stats.no_coordinates || !data.has_coordinates ? 'red' : 'gray'),
        ].join(''));
        root.find('#sig-planner-teams').html(view.teams.map((t) => {
            const p = currentPosition(t.team), c = TEAM_COLORS[(t.team - 1) % TEAM_COLORS.length];
            return '<button type="button" class="sig-planner-team" data-team="' + t.team + '" aria-pressed="' + (Number(view.selectedTeam) === t.team) +
                '" style="--team:' + c + '"><i></i><span><b>' + esc(t.leader) + '</b><small>' +
                esc(teamPositionSummary(p)) + '</small></span></button>';
        }).join(''));
        function updateTeamSummary() {
            const chosen = view.teams.find((t) => t.team === Number(view.selectedTeam));
            root.find('#sig-planner-team-name').text(chosen ? chosen.leader : __('No project team'));
            root.find('#sig-planner-team-dot').css('background', TEAM_COLORS[(Number(view.selectedTeam) - 1) % TEAM_COLORS.length]);
            root.find('#sig-planner-team-context').text(teamRows(view.selectedTeam).length + ' ' + __('planned stops') + ' · ' +
                teamTrips(view.selectedTeam).length + ' ' + __('trips'));
            root.find('#sig-planner-teams [data-team]').attr('aria-pressed', 'false')
                .filter('[data-team="' + Number(view.selectedTeam) + '"]').attr('aria-pressed', 'true');
        }
        updateTeamSummary();
        root.find('#sig-planner-schedule-count').text(assigned().length);
        root.find('#sig-planner-review-count').text(backlog().length);
        root.find('#sig-planner-filter-team').html('<option value="">' + __('All teams') + '</option>' +
            view.teams.map((t) => '<option value="' + t.team + '">' + esc(t.leader) + '</option>').join(''));
        root.find('#sig-planner-filter-day').html('<option value="">' + __('All proposed days') + '</option>' +
            horizon.map((d) => '<option value="' + d + '">' + esc(fmtDates(d)) + '</option>').join(''));

        function drawTeamPlan() {
            const trips = teamTrips(view.selectedTeam);
            root.find('#sig-planner-team-plan-title').text(leaderFor(view.selectedTeam));
            root.find('#sig-planner-team-estimate').text(__('Whole-trip effort estimates include travel.'));
            root.find('#sig-planner-team-trips').html(trips.length ? trips.map((t) => '<article class="sig-planner-trip" style="--team:' +
                TEAM_COLORS[(t.team - 1) % TEAM_COLORS.length] + '"><header><b>' + esc(t.kind) + ' · ' + esc(t.id) + '</b><span>' +
                esc(t.first_day) + ' – ' + esc(t.last_day) + ' · ' + t.stops.length + ' ' + __('sites') + ' · ~' + esc(t.hours) + ' h</span></header>' +
                t.stops.map((s) => {
                    const r = view.rows.find((x) => x.cycle === s.cycle), sig = r ? statusFor(r) : {line: s.reason || ''};
                    return '<div class="sig-planner-stop' + (view.selected === String(s.cycle) ? ' is-selected' : '') + '" data-cycle="' + esc(s.cycle) + '"><div><a class="sig-planner-site-link" href="/app/sig-site-cycle/' +
                        encodeURIComponent(s.cycle) + '">' + esc(s.site) + '</a><small>' + __('Project') + ' ' + esc(s.project || '—') +
                        '</small><div class="sig-planner-badges">' + (r ? statusBadge(r) + decisionBadge(r) : '') +
                        '<span class="sig-planner-muted">' + esc(sig.line) + '</span></div></div><div><b>' + esc(fmtDates(s.day || t.first_day)) +
                        '</b><small>' + __('Stop') + ' ' + s.order + ' · ' + esc(data.tiers[s.tier] || s.tier) + '</small>' +
                        (r ? decisionControl(r) : '') + '</div></div>';
                }).join('') + '<details><summary>' + __('Trip details') + '</summary><p>' + __('Spread') + ': ' + esc(t.diameter_km) +
                ' km · ' + __('Team days') + ': ' + esc(t.team_days) + ' · ' + __('Priority') + ': ' + esc(data.tiers[t.best_tier] || t.best_tier) +
                '</p></details></article>').join('') : '<p class="sig-planner-empty">' + __('No proposed trips for this team.') + '</p>');
        }
        function renderMatrix() {
            const tripsOn = (n, d) => teamTrips(n).filter((t) => (t.days || []).some((x) => String(x).slice(0, 10) === d));
            root.find('#sig-planner-matrix').html('<thead><tr><th>' + __('Project team') + '</th>' +
                horizon.map((d) => '<th>' + esc(fmtDates(d)) + '</th>').join('') + '</tr></thead><tbody>' +
                view.teams.map((t) => '<tr><th><span class="sig-planner-team-label" style="--team:' + TEAM_COLORS[(t.team - 1) % TEAM_COLORS.length] +
                    '"><i></i>' + esc(t.leader) + '</span></th>' + horizon.map((d) => {
                        const trips = tripsOn(t.team, d), count = teamRows(t.team).filter((r) => String(r.day).slice(0, 10) === d).length;
                        const label = count ? count + ' ' + __('proposed visits') : trips.length ? __('Trip continuation') : __('No proposed site work');
                        return '<td>' + (trips.length ? '<button class="sig-planner-matrix-cell" data-team="' + t.team + '" data-day="' + d +
                            '" style="--team:' + TEAM_COLORS[(t.team - 1) % TEAM_COLORS.length] + '"><b>' + label + '</b><small>' +
                            esc(trips.map((x) => x.id).join(' · ')) + '</small></button>' : '<span class="sig-planner-empty-cell">' + label + '</span>') + '</td>';
                    }).join('') + '</tr>').join('') + '</tbody>');
            const tf = root.find('#sig-planner-filter-team').val() || '', df = root.find('#sig-planner-filter-day').val() || '';
            const q = String(root.find('#sig-planner-filter-search').val() || '').toLowerCase();
            const sorted = assigned().filter((r) => (!tf || Number(r.team) === Number(tf)) && (!df || String(r.day).slice(0, 10) === df) &&
                (!q || [r.site, r.project, r.po].some((v) => String(v || '').toLowerCase().includes(q))))
                .sort((a, b) => String(a.day).localeCompare(String(b.day)) || Number(a.team) - Number(b.team) ||
                    String(a.trip_id).localeCompare(String(b.trip_id)) || Number(a.order) - Number(b.order));
            root.find('#sig-planner-schedule-range').text(sorted.length + ' ' + __('of') + ' ' + assigned().length + ' ' + __('proposed visits'));
            root.find('#sig-planner-schedule-rows').html(sorted.length ? sorted.map((r) => {
                const s = statusFor(r);
                return '<tr class="' + (String(view.selected) === String(r.cycle) ? 'is-selected' : '') + '" data-cycle="' + esc(r.cycle) + '"><td><b>' + esc(fmtDates(r.day)) + '</b></td>' +
                    '<td><span class="sig-planner-team-label" style="--team:' + TEAM_COLORS[(r.team - 1) % TEAM_COLORS.length] + '"><i></i>' +
                    esc(leaderFor(r.team)) + '</span></td><td><a class="sig-planner-site-link" href="/app/sig-site-cycle/' +
                    encodeURIComponent(r.cycle) + '">' + esc(r.site) + '</a><small>' + esc(r.project || '—') + (r.po ? ' · PO ' + esc(r.po) : '') +
                    '</small></td><td>' + statusBadge(r) + '<small>' + esc(s.line) + '</small></td><td><b>' + esc(r.trip_id) +
                    '</b><small>~' + esc(r.trip_hours || '—') + ' h · ' + __('whole trip') + '</small></td><td>' + decisionControl(r) + '</td></tr>';
            }).join('') : '<tr><td colspan="6" class="sig-planner-empty">' + __('No visits match the filters.') + '</td></tr>');
        }
        function renderReview() {
            const pending = backlog(), decided = view.rows.filter((r) => !!r.decision), kind = view.reviewKind || 'all';
            const q = String(root.find('#sig-planner-review-search').val() || '').toLowerCase();
            const counts = {all: pending.length, unplaced: pending.filter(hasPoint).length, coordinates: pending.filter((r) => !hasPoint(r)).length, choices: decided.length};
            root.find('#sig-planner-review-filters').html([['all', __('All unplaced')], ['unplaced', __('No team / date')],
                ['coordinates', __('No coordinates')], ['choices', __('PM choices')]].map(([k, l]) =>
                '<button type="button" data-review="' + k + '" aria-pressed="' + (kind === k) + '">' + l + ' <b>' + counts[k] + '</b></button>').join(''));
            let rows = kind === 'choices' ? decided : pending;
            rows = rows.filter((r) => (kind !== 'unplaced' || hasPoint(r)) && (kind !== 'coordinates' || !hasPoint(r)) &&
                (!q || [r.site, r.project, r.po, r.reason].some((x) => String(x || '').toLowerCase().includes(q))));
            root.find('#sig-planner-review-range').text(rows.length + ' ' + __('work items'));
            root.find('#sig-planner-review-rows').html(rows.length ? rows.map((r) => {
                const closest = hasPoint(r) ? nearestTeam(r.site, data, r.cycle) : null, s = statusFor(r);
                return '<tr class="' + (String(view.selected) === String(r.cycle) ? 'is-selected' : '') + '" data-cycle="' + esc(r.cycle) + '"><td><a class="sig-planner-site-link" href="/app/sig-site-cycle/' + encodeURIComponent(r.cycle) + '">' +
                    esc(r.site) + '</a><small>' + esc(r.project || '—') + (r.po ? ' · PO ' + esc(r.po) : '') + '</small></td><td>' +
                    esc(!hasPoint(r) ? __('Coordinates needed') : __('No team / date proposal')) + decisionBadge(r) + '<small>' + esc(r.reason || '') +
                    '</small></td><td>' + statusBadge(r) + '<small>' + esc(s.line) + '</small></td><td>' +
                    (closest ? esc(leaderFor(closest.team)) + ' · ~' + Math.round(closest.km) + ' km' : __('No planned team nearby')) +
                    '</td><td>' + decisionControl(r) + '</td></tr>';
            }).join('') : '<tr><td colspan="5" class="sig-planner-empty">' + __('No work items match this view.') + '</td></tr>');
        }
        function activate(tab) {
            view.activeTab = tab;
            root.find('[data-tab]').attr('aria-selected', 'false').filter('[data-tab="' + tab + '"]').attr('aria-selected', 'true');
            root.find('[data-panel]').prop('hidden', true).filter('[data-panel="' + tab + '"]').prop('hidden', false);
            if (tab === 'team') drawTeamPlan();
            if (tab === 'overall') renderMatrix();
            if (tab === 'review') renderReview();
        }
        root.find('#sig-planner-filter-team').html('<option value="">' + __('All teams') + '</option>' +
            view.teams.map((t) => '<option value="' + t.team + '">' + esc(t.leader) + '</option>').join(''));
        root.find('#sig-planner-filter-day').html('<option value="">' + __('All proposed days') + '</option>' +
            horizon.map((d) => '<option value="' + d + '">' + esc(fmtDates(d)) + '</option>').join(''));
        function fitCurrentExtent() {
            const trips = data.trips.filter((t) => t.status === 'Scheduled' && (view.extent !== 'team' || Number(t.team) === Number(view.selectedTeam)));
            let points = trips.flatMap((t) => t.stops.filter(hasPoint).map((s) => [s.lon, s.lat]));
            points = points.concat((data.team_positions || []).filter((p) => p.state !== 'Incident' && p.lat != null && p.lon != null &&
                (view.extent !== 'team' || Number(p.team_no) === Number(view.selectedTeam))).map((p) => [p.lon, p.lat]));
            if (view.base === 'street') { view.fitTeam = true; view.leafletView = null; return; }
            if (!points.length) { view.box = BOX0.slice(); return; }
            const projected = points.map(([lon, lat]) => project(lon, lat)), xs = projected.map((p) => p[0]), ys = projected.map((p) => p[1]);
            const ratio = BOX0[3] / BOX0[2], width = Math.max(40, Math.max(Math.max(...xs) - Math.min(...xs), (Math.max(...ys) - Math.min(...ys)) / ratio)) * 1.35;
            const height = width * ratio, cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
            view.box = clampBox([cx - width / 2, cy - height / 2, width, height]);
        }
        root.find('#sig-planner-teams').on('click', '[data-team]', (e) => {
            view.selectedTeam = Number($(e.currentTarget).attr('data-team'));
            if (view.extent === 'team') fitCurrentExtent();
            updateTeamSummary(); drawTeamPlan(); refreshMap();
        });
        root.find('.sig-planner-tabs').on('click', '[data-tab]', (e) => activate($(e.currentTarget).attr('data-tab')));
        root.find('.sig-planner-position-table').on('click', '.sig-planner-position-update', (e) => openPosition(Number($(e.currentTarget).attr('data-team-no'))));
        root.find('.sig-planner-shell').on('click', '[data-action]', (e) => {
            const a = $(e.currentTarget).attr('data-action');
            if (a === 'settings') openSettings();
            if (a === 'position') openPosition(view.selectedTeam);
            if (a === 'refresh') load();
            if (a === 'locate-selected' && view.selected) chooseCycle(view.selected, true);
            if (a === 'toggle-map-size') {
                view.expandedMap = !view.expandedMap;
                root.find('.sig-planner-map-card').toggleClass('is-expanded', view.expandedMap);
                $(e.currentTarget).text(view.expandedMap ? __('Restore map') : __('Expand map'));
                if (view.leaflet) setTimeout(() => view.leaflet.invalidateSize(), 80);
            }
            if (a === 'fit-trip' && view.selected) fitSelectedTrip();
            if (a === 'clear-schedule') { root.find('#sig-planner-filter-team, #sig-planner-filter-day').val(''); root.find('#sig-planner-filter-search').val(''); renderMatrix(); }
        });
        root.find('.sig-planner-mapbody, .sig-planner-sitebox').on('keydown', (e) => {
            if (e.key === 'Escape' && view.selected) { e.stopPropagation(); clearSelection(); }
        });
        root.find('#sig-planner-filter-search').on('input', renderMatrix);
        root.find('#sig-planner-filter-team, #sig-planner-filter-day').on('change', renderMatrix);
        root.find('#sig-planner-review-search').on('input', renderReview);
        root.find('#sig-planner-review-filters').on('click', '[data-review]', (e) => { view.reviewKind = $(e.currentTarget).attr('data-review'); renderReview(); });
        root.find('#sig-planner-matrix').on('click', '[data-team][data-day]', (e) => {
            root.find('#sig-planner-filter-team').val($(e.currentTarget).attr('data-team'));
            root.find('#sig-planner-filter-day').val($(e.currentTarget).attr('data-day')); activate('overall'); renderMatrix();
        });
        root.find('.sig-planner-mapbody').on('click', '[data-extent]', (e) => { view.extent = $(e.currentTarget).attr('data-extent'); refreshMap(); });
        root.find('.sig-planner-mapbody').on('click', '[data-unplanned]', () => { view.showUnplanned = !view.showUnplanned; refreshMap(); });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-base]', (e) => setMapBase($(e.currentTarget).attr('data-map-base')));
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-mode]', (e) => { view.mode = $(e.currentTarget).attr('data-map-mode'); refreshMap(); });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-extent]', (e) => { view.extent = $(e.currentTarget).attr('data-map-extent'); fitCurrentExtent(); refreshMap(); });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-unplanned]', () => { view.showUnplanned = !view.showUnplanned; refreshMap(); });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-towns]', () => { view.towns = !view.towns; refreshMap(); });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-zones]', () => {
            view.zones = !view.zones;
            if (view.zones) view.base = 'drawing';
            refreshMap();
        });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-zoom]', (e) => {
            const svg = root.find('.sig-planner-svg')[0], action = $(e.currentTarget).attr('data-map-zoom');
            if (!svg) return;
            if (action === 'reset') { view.box = BOX0.slice(); applyZoom(svg); }
            else zoomBy(svg, action === 'in' ? 0.65 : 1 / 0.65);
        });
        root.find('.sig-planner-live-map-controls').on('click', '[data-map-zoom]', (e) => {
            const svg = root.find('.sig-planner-svg')[0], action = $(e.currentTarget).attr('data-map-zoom');
            if (!svg) return;
            if (action === 'reset') { view.box = BOX0.slice(); applyZoom(svg); }
            else zoomBy(svg, action === 'in' ? 0.65 : 1 / 0.65);
        });
        const search = root.find('#sig-planner-site-search'), suggest = root.find('#sig-planner-site-suggestions');
        let searchHits = [], activeSuggestion = -1, suggestionsOpen = false;
        const closeSuggestions = () => { suggest.empty().hide(); search.attr('aria-expanded', 'false').removeAttr('aria-activedescendant'); activeSuggestion = -1; suggestionsOpen = false; searchHits = []; };
        const renderSuggestions = () => {
            const q = String(search.val() || '').trim().toLowerCase();
            searchHits = q ? Object.entries(view.index.byCycle).map(([cycle, hit]) => {
                const item = hit.stop || hit.other;
                const trip = hit.trip, team = trip ? leaderFor(trip.team) : __('Unplaced');
                const day = trip ? fmtDates(trip.first_day || '') : '';
                const po = String(item.po || String(cycle).split('|')[1] || '');
                return {cycle, hit, site: String(item.site || ''), project: String(item.project || ''), po, team, day,
                    label: `${item.site || ''} ${item.project || ''} ${po} ${team} ${day} ${cycle}`};
            }).filter((x) => x.label.toLowerCase().includes(q))
                .sort((a, b) => Number(a.site.toLowerCase() !== q) - Number(b.site.toLowerCase() !== q) || Number(b.site.toLowerCase().startsWith(q)) - Number(a.site.toLowerCase().startsWith(q)) || a.site.localeCompare(b.site)).slice(0, 12) : [];
            activeSuggestion = -1;
            suggest.html(searchHits.length ? searchHits.map((x, i) => '<button type="button" role="option" id="sig-planner-option-' + i + '" aria-selected="false"' +
                ' data-cycle="' + esc(x.cycle) + '"><b>' + esc(x.site) + '</b><small>' + esc(x.project || __('No project')) + (x.po ? ' · PO ' + esc(x.po) : '') +
                ' · ' + esc(x.team) + (x.day ? ' · ' + esc(x.day) : '') + '</small></button>').join('') : (q ? '<div class="sig-planner-no-results" role="status">' + __('No matching sites in this plan.') + '</div>' : ''));
            suggestionsOpen = !!(q && searchHits.length);
            search.attr('aria-expanded', String(suggestionsOpen));
            if (activeSuggestion >= 0) search.attr('aria-activedescendant', 'sig-planner-option-' + activeSuggestion);
            else search.removeAttr('aria-activedescendant');
            suggest.toggle(!!q);
        };
        search.on('input', renderSuggestions).on('focus', () => { if (String(search.val() || '').trim()) renderSuggestions(); });
        search.on('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                if (!suggestionsOpen) renderSuggestions();
                if (searchHits.length) {
                    e.preventDefault(); activeSuggestion = (activeSuggestion + (e.key === 'ArrowDown' ? 1 : -1) + searchHits.length) % searchHits.length;
                    const active = suggest.find('[role="option"]').attr('aria-selected', 'false').eq(activeSuggestion).attr('aria-selected', 'true');
                    if (active[0]) active[0].scrollIntoView({block: 'nearest'});
                    search.attr('aria-activedescendant', 'sig-planner-option-' + activeSuggestion);
                }
            } else if (e.key === 'Enter') {
                if (activeSuggestion >= 0 && searchHits[activeSuggestion]) { e.preventDefault(); chooseCycle(searchHits[activeSuggestion].cycle, true); }
                else if (searchHits.length === 1) { e.preventDefault(); chooseCycle(searchHits[0].cycle, true); }
            } else if (e.key === 'Escape') { e.stopPropagation(); closeSuggestions(); }
        });
        suggest.on('mousedown', '[data-cycle]', (e) => e.preventDefault());
        suggest.on('click', '[data-cycle]', (e) => chooseCycle($(e.currentTarget).attr('data-cycle'), true));
        search.on('blur', () => setTimeout(closeSuggestions, 120));
        root.find('.sig-planner-shell').on('click', '[data-action="clear-site-search"]', () => {
            search.val(''); closeSuggestions(); clearSelection(); search.trigger('focus');
        });
        root.off('.sigPlannerMap').on('sig-planner-select.sigPlannerMap', (e, cycle, locate) => chooseCycle(cycle, locate))
            .on('sig-planner-clear-selection.sigPlannerMap', () => clearSelection());
        root.find('.sig-planner-mapbody').on('click', '[data-cycle]', (e) => {
            e.stopPropagation(); chooseCycle($(e.currentTarget).attr('data-cycle'), false);
        });
        root.find('.sig-planner-sitebox').on('click', '#sig-planner-map-inspector-close', () => {
            clearSelection();
        });
        root.find('.sig-planner-shell').on('click', '[data-cycle]', (e) => {
            if ($(e.target).is('select, option, a')) return;
            chooseCycle($(e.currentTarget).attr('data-cycle'), false);
        });
        function renderInspector() {
            const r = view.rows.find((x) => x.cycle === view.selected);
            if (!r) { root.find('.sig-planner-sitebox').empty(); return; }
            const s = statusFor(r), pos = r.team ? currentPosition(r.team) : null;
            const canLocate = hasPoint(r);
            const teamColor = r.team ? TEAM_COLORS[(Number(r.team) - 1) % TEAM_COLORS.length] : '#718096';
            const selectedHit = view.index.byCycle[String(r.cycle)], hasTrip = !!(selectedHit && selectedHit.trip && selectedHit.trip.stops && selectedHit.trip.stops.length);
            root.find('.sig-planner-sitebox').html('<div class="sig-planner-sitecard" style="--site-team:' + teamColor + '"><button id="sig-planner-map-inspector-close" type="button" aria-label="' + __('Close') + '">×</button>' +
                '<b><a href="' + projectLink(r) + '">' + esc(r.site) + '</a></b><small>' + esc(r.project || '—') + '</small>' +
                '<button type="button" class="sig-planner-locate" data-action="locate-selected" ' + (canLocate ? '' : 'disabled') + '>' + __('Locate site') + '</button>' +
                (hasTrip ? '<button type="button" class="sig-planner-locate" data-action="fit-trip">' + __('Fit trip') + '</button>' : '') +
                statusBadge(r) + decisionBadge(r) + '<dl><dt>' + __('Plan') + '</dt><dd>' +
                (r.trip_status === 'Scheduled' ? esc(leaderFor(r.team)) + ' · ' + esc(fmtDates(r.day || r.first_day)) : esc(r.trip_status)) +
                '</dd><dt>' + __('TCN window') + '</dt><dd>' + esc(r.window || '—') + '</dd><dt>' + __('Why') + '</dt><dd>' +
                esc(r.reason || s.line) + '</dd><dt>' + __('Team position') + '</dt><dd>' + esc(pos && pos.site || __('No report')) +
                (pos && pos.seen_at ? ' · ' + esc(pos.seen_at) : '') + '</dd><dt>' + __('Coordinates') + '</dt><dd>' +
                (canLocate ? esc(Number(r.lat).toFixed(5) + ', ' + Number(r.lon).toFixed(5)) : __('Unavailable')) + '</dd></dl>' + decisionControl(r) + '</div>');
            const bodyTop = root.find('.sig-planner-mapbody').position().top;
            root.find('.sig-planner-sitebox').css('top', bodyTop + 12);
        }
        function syncSelectedRows() {
            root.find('.sig-planner-stop[data-cycle], .sig-planner-schedule tr[data-cycle], .sig-planner-review tr[data-cycle]')
                .each((_, el) => $(el).toggleClass('is-selected', String($(el).attr('data-cycle')) === String(view.selected)));
        }
        function syncMapControls() {
            root.find('[data-map-base]').attr('aria-pressed', function () { return String($(this).attr('data-map-base') === view.base); });
            root.find('[data-map-mode]').attr('aria-pressed', function () { return String($(this).attr('data-map-mode') === view.mode); });
            root.find('[data-map-extent]').attr('aria-pressed', function () { return String($(this).attr('data-map-extent') === view.extent); });
            root.find('[data-map-unplanned]').attr('aria-pressed', String(view.showUnplanned));
            root.find('[data-map-towns]').attr('aria-pressed', String(view.towns));
            root.find('[data-map-zones]').attr('aria-pressed', String(view.zones));
            root.find('[data-map-zoom]').closest('.sig-planner-map-segment').toggle(view.base === 'drawing');
        }
        function refreshMap() {
            drawMap(data, root.find('.sig-planner-mapbody'));
            syncMapControls(); renderInspector(); syncSelectedRows();
            if (view.activeTab === 'team') drawTeamPlan();
            if (view.expandedMap) root.find('.sig-planner-map-card').addClass('is-expanded');
        }
        function setMapBase(nextBase) {
            if (nextBase === view.base) return;
            if (view.base === 'drawing' && nextBase === 'street') {
                const [x, y, w] = view.box || BOX0, lon = 33 + (x + w / 2) / (0.91 * 40), lat = 34 - (y + (w * BOX0[3] / BOX0[2]) / 2) / 40;
                const scale = BOX0[2] / w;
                view.leafletView = {center: [lat, lon], zoom: Math.max(5, Math.min(11, 6 + Math.log2(scale)))};
            } else if (view.base === 'street' && view.leaflet) {
                const c = view.leaflet.getCenter(), scale = Math.pow(2, Math.max(0, view.leaflet.getZoom() - 6));
                const width = BOX0[2] / scale, height = width * BOX0[3] / BOX0[2], [x, y] = project(c.lng, c.lat);
                view.box = clampBox([x - width / 2, y - height / 2, width, height]);
            }
            view.base = nextBase; refreshMap();
        }
        function chooseCycle(cycle, locate) {
            const hit = view.index.byCycle[String(cycle)], item = hit && (hit.stop || hit.other);
            if (!item) return;
            const oldTeam = view.selectedTeam;
            view.selected = String(cycle);
            if (hit.trip && hit.trip.team && view.extent === 'team') view.selectedTeam = Number(hit.trip.team);
            if (locate && hasPoint(item)) {
                if (view.base === 'drawing') {
                    const [x, y] = project(item.lon, item.lat), currentScale = BOX0[2] / (view.box || BOX0)[2];
                    const width = BOX0[2] / Math.max(currentScale, 3.2), height = width * BOX0[3] / BOX0[2];
                    view.box = clampBox([x - width / 2, y - height / 2, width, height]);
                    view.locateCycle = null;
                } else view.locateCycle = String(cycle);
            }
            if (oldTeam !== view.selectedTeam) updateTeamSummary();
            refreshMap();
            if (locate && view.base === 'drawing' && hasPoint(item)) focusSelectedInDrawing(item);
            if (locate && view.base === 'street' && hasPoint(item)) focusSelectedOnRoad(item);
            if (oldTeam !== view.selectedTeam && view.activeTab === 'team') drawTeamPlan();
            if (locate) root.find('.sig-planner-map-card')[0].scrollIntoView({behavior: 'smooth', block: 'start'});
            closeSuggestions();
        }
        function clearSelection() {
            if (!view.selected) return;
            view.selected = null; view.locateCycle = null;
            refreshMap();
        }
        function focusSelectedInDrawing(item) {
            const svg = root.find('.sig-planner-svg')[0], mapBody = root.find('.sig-planner-mapbody')[0];
            if (!svg || !mapBody || item.lat == null || item.lon == null) return;
            applyZoom(svg);
            const [x, y, w, h] = view.box, rect = svg.getBoundingClientRect(), card = root.find('.sig-planner-sitebox')[0];
            const scale = Math.min(rect.width / w, rect.height / h), drawnW = w * scale, drawnH = h * scale;
            const left = rect.left + (rect.width - drawnW) / 2, top = rect.top + (rect.height - drawnH) / 2;
            const cardRect = card && !card.hidden ? card.getBoundingClientRect() : null;
            const desiredX = cardRect && cardRect.left < rect.right && cardRect.right > rect.left ?
                Math.max(rect.left + 24, Math.min(rect.right - 24, cardRect.left - 24)) : rect.left + rect.width / 2;
            const desiredY = rect.top + rect.height / 2, point = project(item.lon, item.lat);
            const target = clampBox([point[0] - (desiredX - left) / scale, point[1] - (desiredY - top) / scale, w, h]);
            const start = view.box.slice(), duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 350;
            const started = performance.now();
            const frame = (now) => {
                const t = duration ? Math.min(1, (now - started) / duration) : 1, ease = t * t * (3 - 2 * t);
                view.box = start.map((v, i) => v + (target[i] - v) * ease);
                applyZoom(svg);
                if (t < 1) view.cameraAnimation = requestAnimationFrame(frame); else view.cameraAnimation = null;
            };
            if (duration) view.cameraAnimation = requestAnimationFrame(frame); else { view.box = target; applyZoom(svg); }
        }
        function focusSelectedOnRoad(item) {
            const map = view.leaflet, card = root.find('.sig-planner-sitebox')[0];
            if (!map || item.lat == null || item.lon == null) return;
            const size = map.getSize(), mapRect = map.getContainer().getBoundingClientRect(), cardRect = card && card.getBoundingClientRect();
            const desiredX = cardRect && cardRect.left < mapRect.right && cardRect.right > mapRect.left ?
                Math.max(24, Math.min(size.x - 24, cardRect.left - mapRect.left - 24)) : size.x / 2;
            map.panBy([desiredX - size.x / 2, 0], {animate: true, duration: 0.35});
        }
        function fitSelectedTrip() {
            const hit = view.index.byCycle[String(view.selected)], stops = hit && hit.trip ? hit.trip.stops : [];
            const pts = stops.filter(hasPoint);
            if (!pts.length) return;
            if (view.base === 'street' && view.leaflet) {
                view.leaflet.fitBounds(pts.map((p) => [p.lat, p.lon]), {padding: [44, 44], maxZoom: 8, animate: true});
                return;
            }
            const projected = pts.map((p) => project(p.lon, p.lat)), xs = projected.map((p) => p[0]), ys = projected.map((p) => p[1]);
            const width = Math.max(24, Math.max(...xs) - Math.min(...xs)), height = width * BOX0[3] / BOX0[2], pad = 0.16;
            const x = (Math.min(...xs) + Math.max(...xs) - width) / 2 - width * pad;
            const y = (Math.min(...ys) + Math.max(...ys) - height) / 2 - height * pad;
            view.box = clampBox([x, y, width * (1 + 2 * pad), height * (1 + 2 * pad)]);
            refreshMap();
        }
        function renderAll() { drawTeamPlan(); renderMatrix(); renderReview(); renderInspector(); activate(view.activeTab || 'team'); }
        drawMap(data, root.find('.sig-planner-mapbody'));
        renderAll();
        view.lastLoaded = Date.now();
    }

    function workDates(start, count) {
        const out = [], d = new Date(String(start).slice(0, 10) + 'T12:00:00');
        while (out.length < count && !isNaN(d.getTime())) {
            if (![5, 6].includes(d.getDay())) out.push(d.toLocaleDateString('en-CA'));
            d.setDate(d.getDate() + 1);
        }
        return out;
    }

    function render(data) { renderFull(data); }

    function load() {
        root.html(`<p class="sig-planner-foot">${__('Loading…')}</p>`);
        const towns = view.townList ? Promise.resolve() : frappe.call({method: 'sig_warehouse.sig_warehouse.field_planner_api.get_reference_towns'})
            .then((r) => { view.townList = r.message || []; }).catch(() => { view.townList = []; });
        towns.then(() => frappe.call({
            method: 'sig_warehouse.sig_warehouse.field_planner_api.get_field_plan', args: filters,
            callback: (r) => { view.lastLoaded = Date.now(); render(r.message); }, error: () => root.html(`<p class="sig-planner-foot">${__('Could not load the field plan.')}</p>`),
        }));
    }
    wrapper.__sigFieldPlannerRefresh = () => {
        if (Date.now() - (view.lastLoaded || 0) > 30000) load();
    };
    load();
};

frappe.pages['field-planner'].on_page_show = function (wrapper) {
    if (wrapper.__sigFieldPlannerRefresh) wrapper.__sigFieldPlannerRefresh();
};
