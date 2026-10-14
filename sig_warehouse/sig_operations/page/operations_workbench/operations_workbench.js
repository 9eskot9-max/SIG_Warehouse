frappe.pages['operations-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Operations Workbench'), single_column: true});
    const root = $('<main class="sig-ops-home"></main>').appendTo(page.main);
    let data = {}, filter = 'tasks', selected = new Set(), pageNumber = 1;
    const pageSize = 50;
    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const date = (v) => v ? frappe.datetime.str_to_user(String(v).slice(0, 10)) : '—';
    const link = (doctype, name, label) => name ? '<a href="#" data-doctype="' + esc(doctype) + '" data-name="' + esc(name) + '">' + esc(label || name) + '</a>' : '—';
    const ownerLabel = (task) => {
        return (task.owner_names || []).join(' / ');
    };
    const cycles = () => data.cycles || [];
    const tasks = () => data.stage_tasks || [];

    function visibleRows() {
        if (filter === 'cycles') return cycles().filter((r) => !r.terminal).map((cycle) => ({kind:'cycle', cycle}));
        let rows = tasks();
        if (filter === 'review') rows = rows.filter((task) => task.kind === 'stage' && task.needs_review);
        if (filter.startsWith('stage:')) {
            const stage = filter.slice(6);
            rows = rows.filter((task) => task.stage === stage);
        }
        return rows.map((task) => ({kind:task.kind, task, cycle:cycles().find((cycle) => cycle.name === task.cycle)}))
            .filter((row) => row.cycle);
    }

    function render() {
        const all = cycles(), route = data.task_route || {}, summary = data.summary || {};
        const allRows = visibleRows();
        const pageCount = Math.max(1, Math.ceil(allRows.length / pageSize));
        pageNumber = Math.min(pageNumber, pageCount);
        const rows = allRows.slice((pageNumber - 1) * pageSize, pageNumber * pageSize);
        const todos = data.todos || [];
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        const todoRows = !data.todo_access ? '<div class="sig-ops-empty">' + __('My ToDos are unavailable for your current ERP role.') + '</div>' : (todos.length ? '<div class="sig-ops-todos">' + todos.map((t) => '<div class="sig-ops-todo"><b>' + link('ToDo', t.name, t.description || __('Follow-up')) + '</b><small>' + (t.reference_type ? esc(t.reference_type) : '') + (t.reference_name ? ' · ' + link(t.reference_type, t.reference_name) : '') + ' · ' + date(t.date) + (t.date && String(t.date).slice(0,10) < frappe.datetime.get_today() ? ' · <span class="sig-ops-overdue">' + __('Overdue') + '</span>' : '') + '</small></div>').join('') + '</div>' : '<div class="sig-ops-empty">' + __('No open ToDos allocated to you. Your stage work is listed below.') + '</div>');
        const stats = '<section class="sig-ops-stats"><div><strong>' + esc(summary.stage_tasks || 0) + '</strong><span>' + __('My stage tasks') + '</span></div><button data-filter="review" class="is-warning"><strong>' + esc(summary.review_tasks || 0) + '</strong><span>' + __('Work to review') + '</span></button><button data-filter="cycles"><strong>' + all.filter((r) => !r.terminal).length + '</strong><span>' + __('Open site cycles') + '</span></button></section>';
        const stageDefs = [
            ['1 - Initial', __('Mapping · BOQ')],
            ['2 - Plan', __('TCN · MIR · Visit')],
            ['3 - Handover', __('Tags · Photos · As-Built Operational')],
            ['4 - Invoicing', __('As-Built BOQ · Invoice')],
        ];
        const stages = stageDefs.map(([stage, description]) => {
            const count = tasks().filter((task) => task.stage === stage && task.kind === 'stage').length;
            return '<button data-stage="' + esc(stage) + '" class="' + (filter === 'stage:' + stage ? 'active' : '') + '"><b>' + count + '</b><span>' + esc(stage) + '</span><small>' + esc(description) + '</small></button>';
        }).join('');
        const visibleCycleRows = new Set();
        const tableRows = rows.map((row) => {
            const cycle = row.cycle, task = row.task || {};
            const firstCycleRow = !visibleCycleRows.has(cycle.name);
            visibleCycleRows.add(cycle.name);
            const selectable = firstCycleRow && (row.kind === 'cycle' || row.kind === 'stage');
            const checked = selected.has(cycle.name);
            const label = row.kind === 'cycle' ? ((cycle.work || []).map((item) => item.label).join(' · ') || __('Open site cycle'))
                : task.label || __('Open cycle');
            const stage = row.kind === 'cycle' ? cycle.stage : task.stage;
            const status = row.kind === 'cycle'
                ? (cycle.needs_review ? __('Review due') : __('Open cycle'))
                : task.status;
            const reason = row.kind === 'cycle'
                ? (cycle.delay_reason || cycle.delay_note || '')
                : (task.review_reason || '');
            const closeButton = firstCycleRow && data.can_close_cycles
                ? '<button class="btn btn-default sig-ops-close-one" data-cycle-name="' + esc(cycle.name) + '">' + __('Close cycle') + '</button>' : '';
            const projectLabel = cycle.alias || cycle.family || '—';
            return '<tr data-cycle="' + esc(cycle.name) + '" class="' + (checked ? 'selected' : '') + '"><td>' + (selectable ? '<input type="checkbox" class="sig-ops-cycle-check" value="' + esc(cycle.name) + '" ' + (checked ? 'checked' : '') + '>' : '') + '</td><td><b>' + link('SIG Site Cycle', cycle.name, cycle.site) + '</b><small>' + __('WO') + ': ' + esc(cycle.wo || '—') + '</small></td><td><b>' + esc(cycle.ba || '—') + '</b><small>' + esc(projectLabel) + '</small></td><td><span class="sig-ops-stage-label">' + esc(stage || cycle.stage) + '</span></td><td>' + esc(label) + (task.shared ? '<small>' + esc(ownerLabel(task)) + '</small>' : '') + '</td><td><span class="' + ((row.kind === 'cycle' ? cycle.needs_review : task.needs_review) ? 'sig-ops-badge warning' : 'sig-ops-badge') + '">' + esc(status || __('Open')) + '</span>' + (reason ? '<small>' + esc(reason) + '</small>' : '') + closeButton + '</td></tr>';
        }).join('');
        const pager = pageCount > 1 ? '<div class="sig-ops-pagination"><button class="btn btn-default sig-ops-prev" ' + (pageNumber <= 1 ? 'disabled' : '') + '>' + __('Previous') + '</button><span>' + __('Page {0} of {1}', [pageNumber, pageCount]) + '</span><button class="btn btn-default sig-ops-next" ' + (pageNumber >= pageCount ? 'disabled' : '') + '>' + __('Next') + '</button></div>' : '';
        const routeMessage = route.ready ? '' : '<div class="sig-ops-empty">' + __('Stage task routing needs review: ') + esc(route.issue || __('Your Employee link could not be verified.')) + '</div>';
        const title = filter === 'cycles' ? __('Open site cycles') : filter === 'review' ? __('Review due') : filter.startsWith('stage:') ? esc(filter.slice(6)) : __('My stage tasks');
        root.html('<header class="sig-ops-header"><div><div class="sig-ops-eyebrow">' + __('SIG Operations') + '</div><h1>' + __('Operations Workbench') + '</h1></div><nav class="sig-ops-header-actions" aria-label="' + __('Operations links') + '"><button class="btn btn-default sig-ops-projects">' + __('Projects') + '</button><button class="btn btn-default sig-ops-cycles">' + __('Site Cycles') + '</button><button class="btn btn-default sig-ops-visits">' + __('Site Visits') + '</button><button class="btn btn-default sig-ops-refresh">' + __('Refresh') + '</button></nav></header>' +
            '<section class="sig-ops-panel sig-ops-my-todos"><div class="sig-ops-panel-head"><div><h2>' + __('My ToDos') + ' <span class="sig-ops-count">' + esc(data.todo_access ? (summary.todos || 0) : '—') + ((data.todos_has_more || (data.complete && !data.complete.todos)) ? '+' : '') + '</span></h2><p>' + __('Personal follow-ups allocated to your signed-in ERP account.') + '</p></div>' + (data.todo_create ? '<button class="btn btn-default sig-ops-new-todo">' + __('Create a follow-up') + '</button>' : '') + (data.todo_access ? '<button class="btn btn-primary sig-ops-all-todos">' + __('Open My ToDos') + '</button>' : '') + '</div>' + todoRows + ((data.todos_has_more || (data.complete && !data.complete.todos)) ? '<div class="sig-ops-footnote">' + __('Showing the first 50. Open My ToDos to view the complete list.') + '</div>' : '') + '</section>' +
            stats + '<section class="sig-ops-stage"><div class="sig-ops-stage-title"><h2>' + __('Delivery stages') + '</h2></div><div class="sig-ops-stage-flow">' + stages + '</div></section>' +
            '<section class="sig-ops-panel sig-ops-main"><div class="sig-ops-panel-head"><div><h2>' + title + '</h2></div><div class="sig-ops-actions"><button class="btn btn-default sig-ops-export">' + __('Export Excel') + '</button><button class="btn btn-primary sig-ops-close" ' + (data.can_close_cycles && selected.size ? '' : 'disabled') + '>' + __('Close selected cycles') + '</button></div></div>' +
            '<div class="sig-ops-toolbar"><nav>' + [['tasks', __('My stage tasks')], ['review', __('Review due')], ['cycles', __('Open cycles')]].map(([key, label]) => '<button data-filter="' + key + '" class="' + (filter === key ? 'active' : '') + '">' + label + '</button>').join('') + '</nav><span class="sig-ops-filter-count">' + allRows.length + ' ' + __('items') + '</span></div>' + routeMessage +
            '<div class="sig-ops-selection"><label><input type="checkbox" class="sig-ops-select-visible"> ' + __('Select cycles on this page') + '</label><span class="sig-ops-selected-count">' + selected.size + ' ' + __('cycles selected') + '</span><small>' + (allRows.length ? (pageNumber - 1) * pageSize + 1 : 0) + '–' + Math.min(pageNumber * pageSize, allRows.length) + ' ' + __('of') + ' ' + allRows.length + '</small></div>' +
            (rows.length ? '<div class="sig-ops-table-wrap"><table class="sig-ops-table"><thead><tr><th></th><th>' + __('Site / WO') + '</th><th>' + __('Project') + '</th><th>' + __('Stage') + '</th><th>' + __('Task / pending work') + '</th><th>' + __('Status / action') + '</th></tr></thead><tbody>' + tableRows + '</tbody></table></div>' + pager : '<div class="sig-ops-empty">' + __('No work in this view.') + '</div>') +
            '<div class="sig-ops-footnote">' + __('Matching evidence closes stage tasks. Delay flags the same task. Cycle closure records a reason and actor/time; unrelated personal ToDos remain open.') + '</div></section>');
        root.find('button[data-filter]').on('click', function () { filter = $(this).data('filter'); pageNumber = 1; selected.clear(); render(); });
        root.find('[data-stage]').on('click', function () { filter = 'stage:' + $(this).data('stage'); pageNumber = 1; selected.clear(); render(); });
        root.find('.sig-ops-refresh').on('click', load);
        root.find('.sig-ops-projects').on('click', () => frappe.set_route('List', 'Project'));
        root.find('.sig-ops-cycles').on('click', () => frappe.set_route('site-cycles'));
        root.find('.sig-ops-visits').on('click', () => frappe.set_route('site-visits'));
        root.find('.sig-ops-cycle-check').on('change', function () {
            if (this.checked && !selected.has(this.value) && selected.size >= 50) { this.checked = false; return frappe.msgprint(__('Select up to 50 cycles per bulk closure.')); }
            this.checked ? selected.add(this.value) : selected.delete(this.value);
            updateSelection(rows);
        });
        root.find('.sig-ops-select-visible').on('change', function () {
            const visible = Array.from(new Set(rows
                .filter((row) => row.kind === 'cycle' || row.kind === 'stage')
                .map((row) => row.cycle.name)));
            if (this.checked) {
                const unselected = visible.filter((name) => !selected.has(name));
                const available = Math.max(0, 50 - selected.size);
                unselected.slice(0, available).forEach((name) => selected.add(name));
                if (unselected.length > available) frappe.show_alert({message: __('Selected up to 50 cycles. Clear some to select more.'), indicator:'orange'});
            } else visible.forEach((name) => selected.delete(name));
            updateSelection(rows);
        });
        root.find('.sig-ops-prev').on('click', () => { pageNumber = Math.max(1, pageNumber - 1); render(); });
        root.find('.sig-ops-next').on('click', () => { pageNumber += 1; render(); });
        root.find('a[data-doctype]').on('click', function (e) { e.preventDefault(); frappe.set_route('Form', $(this).data('doctype'), $(this).data('name')); });
        root.find('.sig-ops-close').on('click', closeSelected);
        root.find('.sig-ops-close-one').on('click', function () { closeCycles([$(this).data('cycle-name')]); });
        root.find('.sig-ops-export').on('click', exportExcel);
        root.find('.sig-ops-all-todos').on('click', () => { frappe.route_options = {allocated_to: frappe.session.user, status: ['not in', ['Closed', 'Cancelled']]}; frappe.set_route('List', 'ToDo'); });
        root.find('.sig-ops-new-todo').on('click', () => frappe.new_doc('ToDo', {allocated_to: frappe.session.user, status: 'Open'}));
        updateSelection(rows);
    }

    function updateSelection(rows) {
        root.find('.sig-ops-selected-count').text(selected.size + ' ' + __('cycles selected'));
        root.find('.sig-ops-close').prop('disabled', !data.can_close_cycles || !selected.size);
        root.find('tr[data-cycle]').each(function () {
            const isSelected = selected.has($(this).data('cycle'));
            $(this).toggleClass('selected', isSelected);
            $(this).find('.sig-ops-cycle-check').prop('checked', isSelected);
        });
        const available = Array.from(new Set(rows
            .filter((row) => row.kind === 'cycle' || row.kind === 'stage')
            .map((row) => row.cycle.name)));
        const checked = available.filter((name) => selected.has(name)).length;
        root.find('.sig-ops-select-visible').prop('checked', available.length > 0 && checked === available.length)
            .prop('indeterminate', checked > 0 && checked < available.length);
    }

    function closeCycles(names) {
        names = Array.from(new Set(names)).filter(Boolean);
        if (!names.length || !data.can_close_cycles) return;
        frappe.prompt([{fieldname:'reason', label:__('Closure reason'), fieldtype:'Small Text', reqd:1}], (values) => {
            frappe.call({method:'sig_warehouse.sig_warehouse.operations_workbench.close_cycles', args:{cycles:names, reason:values.reason}})
                .then((r) => { selected.clear(); frappe.show_alert({message: __('Closed {0} site cycles.', [((r.message || {}).closed || []).length]), indicator:'green'}); load(); });
        }, __('Close selected site cycles'), __('Close cycles'));
    }

    function closeSelected() {
        if (!selected.size) return frappe.msgprint(__('Select one or more cycles first.'));
        closeCycles(Array.from(selected));
    }

    function exportExcel() {
        window.open('/api/method/sig_warehouse.sig_warehouse.operations_workbench.export_workbook?filter=' + encodeURIComponent(filter), '_blank');
    }

    function load() {
        root.html('<div class="sig-ops-loading">' + __('Loading operations…') + '</div>');
        frappe.call({method:'sig_warehouse.sig_warehouse.operations_workbench.get_overview'})
            .then((r) => { data = r.message || {}; render(); })
            .catch(() => root.html('<div class="sig-ops-error">' + __('Operations data could not be loaded. Check your ERP access and refresh.') + '</div>'));
    }
    load();
};

