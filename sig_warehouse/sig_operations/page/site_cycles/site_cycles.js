frappe.pages['site-cycles'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Site Cycles'), single_column: true});
    const root = $('<main class="sig-cycles-page"></main>').appendTo(page.main);
    const state = {data: {}, family: '', project: '', periodDays: 10, stage: '', query: '', includeClosed: false, page: 1, selected: '', events: [], eventStatus: 'idle', loadId: 0};
    const pageSize = 50;
    const stageDefs = [
        ['1 - Initial', __('Mapping · BOQ'), 'initial'],
        ['2 - Plan', __('TCN · MIR · Visit'), 'plan'],
        ['3 - Handover', __('Tags · As-Built Operational'), 'handover'],
        ['4 - Invoicing', __('As-Built BOQ file'), 'invoicing'],
    ];
    const esc = (value) => frappe.utils.escape_html(value == null ? '' : String(value));
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : '—';
    const ownerLabel = (item) => (item.owner_names || []).join(' / ');
    const cycleAlias = (cycle) => cycle.alias || cycle.project_alias || cycle.family || '—';
    const money = (value) => {
        const amount = Number(value);
        return Number.isFinite(amount) && amount > 0
            ? `${new Intl.NumberFormat(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(amount)} SAR`
            : '';
    };
    const stageTone = (stage) => stage.startsWith('1 -') ? 'initial'
        : stage.startsWith('2 -') ? 'plan'
            : stage.startsWith('3 -') ? 'handover'
                : stage.startsWith('4 -') ? 'invoicing' : 'closed';

    function cyclesForFamily() {
        return allCycles().filter((cycle) => !state.family || cycle.family === state.family)
            .filter((cycle) => !state.project || cycle.project_id === state.project);
    }

    function allCycles() {
        return (state.data.cycles || []).concat(state.includeClosed ? (state.data.closed_cycles || []) : []);
    }

    // Match the legacy Evidence Dashboard: keep the project-family clusters
    // together, then show the most advanced active stages first inside each
    // cluster. Within a stage, older due items come first, followed by site.
    function legacyCycleOrder(cycle) {
        const family = String(cycle.family || '').trim().toLowerCase();
        const familyOrder = /5g|colocation/.test(family) ? 1
            : /capex/.test(family) ? 2
                : /incident/.test(family) ? 3 : 9;
        const stage = String(cycle.stage || '').match(/^([1-4])/);
        const stageRank = stage ? Number(stage[1]) : 0;
        const due = String(cycle.stage_due_on || '9999-12-31').slice(0, 10);
        const site = String(cycle.site || '').toLowerCase();
        return [familyOrder, -stageRank, due, site];
    }

    function sortCyclesLikeLegacy(cycles) {
        return cycles.sort((a, b) => {
            const left = legacyCycleOrder(a);
            const right = legacyCycleOrder(b);
            for (let i = 0; i < left.length; i++) {
                if (left[i] < right[i]) return -1;
                if (left[i] > right[i]) return 1;
            }
            return 0;
        });
    }

    function visibleCycles() {
        const query = state.query.toLowerCase();
        return sortCyclesLikeLegacy(cyclesForFamily().filter((cycle) => {
            if (state.stage && cycle.stage !== state.stage) return false;
            const haystack = [cycle.site, cycle.name, cycle.wo, cycle.ba, cycle.project_id, cycle.alias, cycle.family].join(' ').toLowerCase();
            return !query || haystack.includes(query);
        }));
    }

    function shell() {
        root.html(`<header class="sig-cycles-header"><div><div class="sig-cycles-eyebrow">${__('SIG Operations')}</div>
            <h1>${__('Site Cycles')}</h1><p class="sig-cycles-scope-caption">${__('Open site cycles across all project scopes.')}</p></div>
            <nav><button type="button" class="btn btn-default sig-cycles-workbench">${__('Operations Workbench')}</button>
                <button type="button" class="btn btn-default sig-cycles-visits">${__('Site Visits')}</button>
                <button type="button" class="btn btn-default sig-cycles-export" style="display:none">${__('Export Excel')}</button>
                <button type="button" class="btn btn-default sig-cycles-refresh">${__('Refresh')}</button></nav></header>
            <div class="sig-cycles-pending-total"><strong class="sig-cycles-pending-number">—</strong><span>${__('Pending cycles')}</span><small class="sig-cycles-period"></small></div>
            <section class="sig-cycles-stages"><div class="sig-cycles-section-head"><div><h2>${__('Current stage')}</h2>
                <p>${__('Click a stage to filter the cycle list.')}</p></div><button type="button" class="btn btn-default btn-xs sig-cycles-clear-stage">${__('All stages')}</button></div>
                <div class="sig-cycles-stage-grid"></div></section>
            <div class="sig-cycles-summary"></div>
            <div class="sig-cycles-toolbar"><label>${__('Project')}<select class="form-control sig-cycles-project"></select></label>
                <label>${__('Family')}<select class="form-control sig-cycles-family"></select></label>
                <label>${__('Period')}<select class="form-control sig-cycles-period-filter"><option value="10">${__('10 completed days')}</option><option value="30">${__('30 completed days')}</option><option value="90">${__('90 completed days')}</option></select></label>
                <label class="sig-cycles-search">${__('Find a cycle')}<input class="form-control" placeholder="${__('Site, BA, alias or WO')}"></label>
                <label class="sig-cycles-history-toggle"><input type="checkbox"> ${__('Include closed cycles')}</label>
                <span class="sig-cycles-count"></span></div>
            <div class="sig-cycles-layout"><section class="sig-cycles-table-wrap"></section><aside class="sig-cycles-detail"></aside></div>
            <div class="sig-cycles-footnote">${__('Open items close when matching evidence is recorded. Review due flags existing pending work; age alone does not create a task. Historical KPI timing is reconstructed from recorded evidence; averages exclude unknown starts.')}</div>`);
        root.find('.sig-cycles-workbench').on('click', () => frappe.set_route('operations-workbench'));
        root.find('.sig-cycles-visits').on('click', () => frappe.set_route('site-visits'));
        root.find('.sig-cycles-export').on('click', () => window.open(
            '/api/method/sig_warehouse.sig_warehouse.operations_workbench.export_workbook?filter=cycles&scope=all', '_blank'));
        root.find('.sig-cycles-refresh').on('click', load);
        root.find('.sig-cycles-family').on('change', function () { state.family = this.value; state.page = 1; state.selected = ''; state.events = []; render(); });
        root.find('.sig-cycles-project').on('change', function () { state.project = this.value; state.page = 1; state.selected = ''; state.events = []; render(); });
        root.find('.sig-cycles-period-filter').on('change', function () { state.periodDays = Number(this.value) || 10; load(); });
        root.find('.sig-cycles-history-toggle input').on('change', function () { state.includeClosed = this.checked; state.page = 1; state.selected = ''; state.events = []; render(); });
        root.find('.sig-cycles-search input').on('input', frappe.utils.debounce(function () { state.query = this.value.trim(); state.page = 1; render(); }, 250));
        root.find('.sig-cycles-clear-stage').on('click', () => { state.stage = ''; state.page = 1; render(); });
    }

    function renderSummary() {
        const scoped = (state.data.kpi_cycles || []).filter((cycle) =>
            (!state.family || cycle.family === state.family) && (!state.project || cycle.project_id === state.project));
        const completed = scoped.filter((cycle) => cycle.completion_in_period);
        const durations = completed.map((cycle) => cycle.elapsed_days).filter((value) => value !== null && value !== undefined && value !== '').map(Number).filter(Number.isFinite);
        const average = durations.length ? `${(durations.reduce((sum, value) => sum + value, 0) / durations.length).toFixed(1)} d` : '—';
        const start = state.data.period_start;
        const end = state.data.period_end;
        const lastDay = end ? new Date(`${end}T00:00:00Z`) : null;
        if (lastDay) lastDay.setUTCDate(lastDay.getUTCDate() - 1);
        root.find('.sig-cycles-pending-number').text(cyclesForFamily().filter((cycle) => !cycle.terminal).length.toLocaleString());
        root.find('.sig-cycles-period').text(start && lastDay ? `${date(start)} – ${date(lastDay.toISOString().slice(0, 10))}` : '');
        const cards = [
            [completed.length, __('Completed cycles /{0}d', [state.periodDays]), __('Qualifying cycle closures')],
            [average, __('Average Cycle'), `n=${durations.length} ${__('of')} ${completed.length}`],
        ];
        root.find('.sig-cycles-summary').html(cards.map(([value, label, detail]) => `<div title="${esc(label === __('Average Cycle') ? __('Known Initial-to-completion intervals only; unknown starts are excluded.') : '')}"><strong>${esc(value)}</strong><span>${esc(label)}<small>${esc(detail)}</small></span></div>`).join(''));
    }

    function renderFilters() {
        const all = (state.data.cycles || []).concat(state.data.closed_cycles || []);
        const select = root.find('.sig-cycles-family').empty();
        select.append($('<option></option>').val('').text(__('All project scopes')));
        [...new Set(all.map((cycle) => cycle.family).filter(Boolean))].sort().forEach((family) => {
            select.append($('<option></option>').val(family).text(family));
        });
        select.val(state.family);
        const project = root.find('.sig-cycles-project').empty();
        project.append($('<option></option>').val('').text(__('All projects')));
        const projects = new Map(all.filter((cycle) => cycle.project_id).map((cycle) => [cycle.project_id, cycle.project || cycle.project_id]));
        [...projects.entries()].sort((a, b) => String(a[1]).localeCompare(String(b[1]))).forEach(([id, label]) => {
            project.append($('<option></option>').val(id).text(label));
        });
        project.val(state.project);
        root.find('.sig-cycles-period-filter').val(String(state.periodDays));
        root.find('.sig-cycles-search input').val(state.query);
        root.find('.sig-cycles-history-toggle input').prop('checked', state.includeClosed);
    }

    function renderStages() {
        const scoped = (state.data.cycles || []).filter((cycle) =>
            (!state.family || cycle.family === state.family) && (!state.project || cycle.project_id === state.project));
        const kpiCycles = (state.data.kpi_cycles || []).filter((cycle) =>
            (!state.family || cycle.family === state.family) && (!state.project || cycle.project_id === state.project));
        const stages = stageDefs.map(([stage, caption, tone]) => {
            const count = scoped.filter((cycle) => cycle.stage === stage).length;
            const movements = kpiCycles.flatMap((cycle) => (cycle.stage_exits_in_period || []).filter((item) => item.stage === stage));
            const durations = movements.map((item) => item.days).filter((value) => value !== null && value !== undefined && value !== '').map(Number).filter(Number.isFinite);
            const average = durations.length ? `${(durations.reduce((sum, value) => sum + value, 0) / durations.length).toFixed(1)} d` : '—';
            return `<button type="button" data-stage="${esc(stage)}" data-tone="${tone}" class="${state.stage === stage ? 'active' : ''}"><strong>${count}</strong><span>${esc(stage)}</span><small>${esc(caption)}</small><div class="sig-cycles-stage-kpis"><small><span>${__('Completed /{0}d', [state.periodDays])}</span><b title="${esc(__('Stage movement count from accepted evidence.'))}">${movements.length}</b></small><small><span>${__('Average stage')}</span><b title="n=${durations.length}; ${__('reconstructed from recorded evidence')}">${esc(average)}</b></small></div></button>`;
        }).join('');
        root.find('.sig-cycles-stage-grid').html(stages).find('button[data-stage]').on('click', function () {
            state.stage = state.stage === $(this).data('stage') ? '' : $(this).data('stage');
            state.page = 1;
            render();
        });
    }

    function workHtml(cycle) {
        const items = (cycle.work || []).filter((item) => item.key !== 'asbuilt_operational');
        const hasOperationalTask = (cycle.work || []).some((item) => item.key === 'asbuilt_operational');
        const tasks = items.length ? items.map((item) => {
            const stage = item.stage || cycle.stage;
            const stageNote = stage !== cycle.stage ? `<small>${esc(stage)}</small>` : '';
            const owners = ownerLabel(item);
            return `<div class="sig-cycles-work-item"><span>${esc(item.label || __('Open item'))}</span><small>${owners ? esc(owners) : ''}</small>${stageNote}</div>`;
        }).join('') : (hasOperationalTask ? '' : `<span class="sig-cycles-muted">${__('No open stage item projected')}</span>`);
        return tasks + operationalStatusHtml(cycle);
    }

    function operationalStatusHtml(cycle) {
        const operational = cycle.asbuilt_operational || {};
        if (operational.display === false) return '';
        if (operational.visible !== true) {
            return `<div class="sig-cycles-operational-status unavailable"><span>${__('As-Built Operational')}</span><small>${__('Status unavailable')}</small></div>`;
        }
        if (!operational.applicable) return '';
        const closed = Boolean(operational.closed);
        const state = closed ? __('Closed') : __('Open');
        const owners = !closed ? ownerLabel({owner_names: operational.owner_names || []}) : '';
        return `<div class="sig-cycles-operational-status ${closed ? 'closed' : 'open'}"><span>${__('As-Built Operational')}</span><small>${state}${owners ? ` · ${esc(owners)}` : ''}</small></div>`;
    }

    function renderTable() {
        const allRows = visibleCycles();
        const pageCount = Math.max(1, Math.ceil(allRows.length / pageSize));
        state.page = Math.min(state.page, pageCount);
        const rows = allRows.slice((state.page - 1) * pageSize, state.page * pageSize);
        root.find('.sig-cycles-count').text(`${allRows.length} ${__('cycles')}`);
        const body = rows.map((cycle) => {
            const alias = cycleAlias(cycle);
            const woValue = money(cycle.gross_value);
            const signal = cycle.terminal
                ? `<span class="sig-cycles-badge closed">${__('Closed')}</span>`
                : cycle.needs_review
                ? `<span class="sig-cycles-badge warning">${__('Review due')}</span>`
                : `<span class="sig-cycles-badge">${__('Open')}</span>`;
            const reason = cycle.delay_reason || cycle.delay_note;
            return `<tr data-cycle="${esc(cycle.name)}" class="${state.selected === cycle.name ? 'selected' : ''}">
                <td><a href="#" class="sig-cycles-site" data-cycle="${esc(cycle.name)}">${esc(cycle.site)}</a>${woValue ? ` <span class="sig-cycles-value">- ${esc(woValue)}</span>` : ''}<small>${__('WO')}: ${esc(cycle.wo || '—')}</small></td>
                <td><strong>${esc(cycle.ba || cycle.project_id || '—')}</strong><small>${esc(alias)}</small></td>
                <td><span class="sig-cycles-stage tone-${stageTone(cycle.stage)}">${esc(cycle.stage)}</span></td>
                <td>${workHtml(cycle)}</td><td>${signal}${reason ? `<small>${esc(reason)}</small>` : ''}${cycle.stage_due_on ? `<small>${__('Due')}: ${date(cycle.stage_due_on)}</small>` : ''}</td></tr>`;
        }).join('');
        const pager = pageCount > 1 ? `<div class="sig-cycles-pager"><button type="button" class="btn btn-default btn-xs sig-cycles-prev" ${state.page <= 1 ? 'disabled' : ''}>${__('Previous')}</button>
            <span>${__('Page {0} of {1}', [state.page, pageCount])}</span><button type="button" class="btn btn-default btn-xs sig-cycles-next" ${state.page >= pageCount ? 'disabled' : ''}>${__('Next')}</button></div>` : '';
        const table = `<div class="sig-cycles-table-title"><strong>${state.stage ? esc(state.stage) : state.includeClosed ? __('Cycles and closed history') : __('All open cycles')}</strong><span>${allRows.length} ${__('cycles')}</span></div>
            <table><thead><tr><th>${__('Site / WO')}</th><th>${__('Project')}</th><th>${__('Cycle stage')}</th><th>${__('Open items')}</th><th>${__('Signal')}</th></tr></thead>
            <tbody>${body || `<tr><td colspan="5" class="sig-cycles-empty">${__('No open cycles match these filters.')}</td></tr>`}</tbody></table>${pager}`;
        root.find('.sig-cycles-table-wrap').html(table);
        root.find('tr[data-cycle]').on('click', function (event) {
            if ($(event.target).closest('a').length) return;
            selectCycle($(this).data('cycle'));
        });
        root.find('.sig-cycles-site').on('click', function (event) {
            event.preventDefault();
            frappe.set_route('Form', 'SIG Site Cycle', $(this).data('cycle'));
        });
        root.find('.sig-cycles-prev').on('click', () => { state.page = Math.max(1, state.page - 1); renderTable(); });
        root.find('.sig-cycles-next').on('click', () => { state.page = Math.min(pageCount, state.page + 1); renderTable(); });
    }

    function renderDetail() {
        const cycle = allCycles().find((item) => item.name === state.selected);
        if (!cycle) {
            root.find('.sig-cycles-detail').html(`<div class="sig-cycles-detail-empty">${__('Select a cycle to see its open items and evidence history.')}</div>`);
            return;
        }
        const evidence = (state.events || []).map((event) => `<div class="sig-cycles-event"><strong>${esc(event.code)}</strong><small>${esc(date(event.occurred_at))}</small></div>`).join('');
        const evidenceContent = state.eventStatus === 'loading' ? `<p class="sig-cycles-muted">${__('Loading evidence history…')}</p>`
            : state.eventStatus === 'error' ? `<p class="sig-cycles-muted">${__('Evidence history is unavailable for this cycle.')}</p>`
                : evidence || `<p class="sig-cycles-muted">${__('No evidence events recorded.')}</p>`;
        const items = (cycle.work || []).map((item) => {
            if (item.key === 'asbuilt_operational') return '';
            const owners = ownerLabel(item);
            return `<div class="sig-cycles-detail-item"><strong>${esc(item.label || __('Open item'))}</strong><small>${esc(item.stage || cycle.stage)}${owners ? ` · ${esc(owners)}` : ''}</small></div>`;
        }).join('');
        const hasOperationalTask = (cycle.work || []).some((item) => item.key === 'asbuilt_operational');
        const operationalStatus = operationalStatusHtml(cycle);
        const timingRows = (cycle.stage_timings || []).map((item) => {
            const running = Boolean(item.running);
            const value = running ? item.elapsed_days : item.days;
            const duration = value === null || value === undefined || !Number.isFinite(Number(value))
                ? '—' : `${Number(value).toFixed(1)} d`;
            return `<div class="sig-cycles-timing-row ${running ? 'running' : value == null ? 'unknown' : ''}"><span>${esc(item.stage)}</span><b>${esc(duration)}</b></div>`;
        }).join('');
        const elapsed = cycle.elapsed_days === null || cycle.elapsed_days === undefined || !Number.isFinite(Number(cycle.elapsed_days))
            ? '—' : `${Number(cycle.elapsed_days).toFixed(1)} d`;
        root.find('.sig-cycles-detail').html(`<div class="sig-cycles-detail-head"><div><h2>${esc(cycle.site)}</h2><p>${esc(cycle.ba || cycle.project_id || '—')} · ${esc(cycleAlias(cycle))}</p></div>
            <button type="button" class="btn btn-default btn-xs sig-cycles-open-form">${__('Open cycle')}</button></div>
            <div class="sig-cycles-detail-body"><div class="sig-cycles-detail-stage">${esc(cycle.stage)}${cycle.wo ? ` · ${__('WO')} ${esc(cycle.wo)}` : ''}</div>
                <div class="sig-cycles-elapsed"><span>${cycle.terminal ? __('Elapsed') : __('Elapsed so far')}</span><b>${esc(elapsed)}</b></div>
                <h3>${__('Time in each stage')}</h3><div class="sig-cycles-timing-list">${timingRows || `<p class="sig-cycles-muted">${__('Stage timing unavailable')}</p>`}</div>
                ${operationalStatus ? `<h3>${__('As-Built Operational')}</h3>${operationalStatus}` : ''}
                <h3>${__('Open stage items')}</h3>${items || (hasOperationalTask ? '' : `<p class="sig-cycles-muted">${__('No open stage item projected.')}</p>`)}
                <h3>${__('Evidence history')}</h3>${evidenceContent}</div>`);
        root.find('.sig-cycles-open-form').on('click', () => frappe.set_route('Form', 'SIG Site Cycle', cycle.name));
    }

    function selectCycle(name) {
        state.selected = name;
        state.events = [];
        state.eventStatus = 'loading';
        renderTable();
        renderDetail();
        frappe.call({method: 'sig_warehouse.sig_warehouse.project_progress.get_events', args: {cycle: name}})
            .then((response) => { state.events = response.message || []; state.eventStatus = 'ready'; renderDetail(); })
            .catch(() => { state.events = []; state.eventStatus = 'error'; renderDetail(); });
    }

    function render() {
        root.find('.sig-cycles-export').toggle(Boolean(state.data.can_export));
        root.find('.sig-cycles-scope-caption').text(__('Open site cycles across all project scopes.'));
        renderFilters();
        renderSummary();
        renderStages();
        renderTable();
        renderDetail();
    }

    function load() {
        const loadId = ++state.loadId;
        let settled = false;
        root.find('.sig-cycles-table-wrap').html(`<div class="sig-cycles-loading">${__('Loading site cycles…')}</div>`);
        const timeout = window.setTimeout(() => {
            if (settled || state.loadId !== loadId) return;
            settled = true;
            root.find('.sig-cycles-table-wrap').html(`<div class="sig-cycles-error">${__('Site Cycles is taking too long to load.')} <button type="button" class="btn btn-default btn-xs sig-cycles-retry">${__('Retry')}</button></div>`);
            root.find('.sig-cycles-retry').on('click', load);
        }, 45000);
        frappe.call({method: 'sig_warehouse.sig_warehouse.operations_workbench.get_cycle_dashboard', args: {period_days: state.periodDays}})
            .then((response) => {
                if (state.loadId !== loadId) return;
                settled = true;
                window.clearTimeout(timeout);
                const overview = response.message || {};
                const cycles = (overview.cycles || []).filter((cycle) => !cycle.terminal);
                const closedCycles = (overview.closed_cycles || []).filter((cycle) => cycle.terminal);
                const stages = Object.fromEntries(stageDefs.map(([stage]) => [
                    stage, cycles.filter((cycle) => cycle.stage === stage).length,
                ]));
                state.data = {
                    cycles,
                    closed_cycles: closedCycles,
                    kpi_cycles: overview.kpi_cycles || [],
                    kpi_summary: overview.kpi_summary || {},
                    period_start: overview.period_start || '',
                    period_end: overview.period_end || '',
                    period_days: overview.period_days || state.periodDays,
                    as_of: overview.as_of || '',
                    scope: 'all',
                    can_export: Boolean(overview.can_export),
                    complete: (overview.complete || {}).cycles !== false,
                    summary: {
                        cycles: cycles.length,
                        open_items: cycles.reduce((total, cycle) => total + (cycle.work || []).length, 0),
                        review_due: cycles.filter((cycle) => cycle.needs_review).length,
                        stages,
                    },
                };
                if (state.selected && !allCycles().some((cycle) => cycle.name === state.selected)) state.selected = '';
                render();
                if (state.data.complete === false) root.prepend(`<div class="sig-cycles-notice">${__('The visible cycle list is partial. Refine the source data before treating these counts as complete.')}</div>`);
            })
            .catch(() => {
                if (state.loadId !== loadId) return;
                settled = true;
                window.clearTimeout(timeout);
                root.find('.sig-cycles-table-wrap').html(`<div class="sig-cycles-error">${__('Site Cycles could not be loaded. Check your ERP access and refresh.')} <button type="button" class="btn btn-default btn-xs sig-cycles-retry">${__('Retry')}</button></div>`);
                root.find('.sig-cycles-retry').on('click', load);
            });
    }

    shell();
    load();
};
