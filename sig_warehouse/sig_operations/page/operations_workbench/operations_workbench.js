frappe.pages['operations-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Operations Workbench'), single_column: true});
    const root = $('<main class="sig-ops-home"></main>').appendTo(page.main);
    let data = {}, filter = 'open', selected = new Set(), pageNumber = 1;
    const pageSize = 50;
    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const date = (v) => v ? frappe.datetime.str_to_user(String(v).slice(0, 10)) : '—';
    const link = (doctype, name, label) => name ? '<a href="#" data-doctype="' + esc(doctype) + '" data-name="' + esc(name) + '">' + esc(label || name) + '</a>' : '—';
    const cycles = () => data.cycles || [];

    function render() {
        const all = cycles();
        const filtered = all.filter((r) => filter === 'review' ? r.needs_review : (filter.startsWith('stage:') ? r.stage === filter.slice(6) : !r.terminal));
        const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
        pageNumber = Math.min(pageNumber, pageCount);
        const rows = filtered.slice((pageNumber - 1) * pageSize, pageNumber * pageSize);
        const todos = data.todos || [], summary = data.summary || {};
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        const stats = '<section class="sig-ops-stats"><button data-filter="open"><strong>' + all.filter((r) => !r.terminal).length + '</strong><span>' + __('Open site cycles') + '</span></button><button data-filter="review" class="is-warning"><strong>' + all.filter((r) => r.needs_review).length + '</strong><span>' + __('Pending work to review') + '</span></button></section>';
        const stages = ['Scope & readiness', 'Preparation', 'Handover', 'Completion documents'].map((stage) => '<button data-stage="' + esc(stage) + '" class="' + (filter === 'stage:' + stage ? 'active' : '') + '"><b>' + all.filter((r) => !r.terminal && r.stage === stage).length + '</b><span>' + esc(stage) + '</span>' + (stage === 'Handover' ? '<small>' + __('Tags · Photos · As-Built BOQ run in parallel') + '</small>' : '') + '</button>').join('<i class="fa fa-angle-right" aria-hidden="true"></i>');
        const todoRows = !data.todo_access ? '<div class="sig-ops-empty">' + __('My ToDos are unavailable for your current ERP role.') + '</div>' : (todos.length ? '<div class="sig-ops-todos">' + todos.map((t) => '<div class="sig-ops-todo"><b>' + link('ToDo', t.name, t.description || __('Follow-up')) + '</b><small>' + (t.reference_type ? esc(t.reference_type) : '') + (t.reference_name ? ' · ' + link(t.reference_type, t.reference_name) : '') + ' · ' + date(t.date) + (t.date && String(t.date).slice(0,10) < frappe.datetime.get_today() ? ' · <span class="sig-ops-overdue">' + __('Overdue') + '</span>' : '') + '</small></div>').join('') + '</div>' : '<div class="sig-ops-empty">' + __('No open ToDos allocated to you.') + '</div>');
        const tableRows = rows.map((r) => {
            const labels = (r.work || []).map((w) => esc(w.label));
            const pending = labels.length ? labels.slice(0, 2).join(' · ') + (labels.length > 2 ? ' <small>+' + (labels.length - 2) + ' ' + __('more') + '</small>' : '') : __('No pending evidence task');
            const signal = r.needs_review ? [r.is_delayed && __('Delayed'), r.is_aged && __('Aged'), r.past_due && __('Past due')].filter(Boolean).join(' · ') : __('On track');
            return '<tr data-cycle="' + esc(r.name) + '" class="' + (selected.has(r.name) ? 'selected' : '') + '"><td><input type="checkbox" class="sig-ops-cycle-check" value="' + esc(r.name) + '" ' + (selected.has(r.name) ? 'checked' : '') + '></td><td><b>' + link('SIG Site Cycle', r.name, r.site) + '</b><small>' + __('WO') + ': ' + esc(r.wo || '—') + '</small></td><td><b>' + esc(r.ba || r.project_id || '—') + '</b><small>' + esc(r.alias || '—') + '</small></td><td><span class="sig-ops-stage-label">' + esc(r.stage) + '</span></td><td>' + pending + '</td><td><span class="' + (r.needs_review ? 'sig-ops-badge warning' : 'sig-ops-badge') + '">' + esc(signal) + '</span>' + (r.delay_reason ? '<small>' + esc(r.delay_reason) + (r.delay_note ? ' · ' + esc(r.delay_note) : '') + '</small>' : '') + '</td></tr>';
        }).join('');
        const pager = pageCount > 1 ? '<div class="sig-ops-pagination"><button class="btn btn-default sig-ops-prev" ' + (pageNumber <= 1 ? 'disabled' : '') + '>' + __('Previous') + '</button><span>' + __('Page {0} of {1}', [pageNumber, pageCount]) + '</span><button class="btn btn-default sig-ops-next" ' + (pageNumber >= pageCount ? 'disabled' : '') + '>' + __('Next') + '</button></div>' : '';
        root.html('<header class="sig-ops-header"><div><div class="sig-ops-eyebrow">' + __('SIG Operations') + '</div><h1>' + __('Operations Workbench') + '</h1></div><button class="btn btn-default sig-ops-refresh">' + __('Refresh') + '</button></header>' +
            '<section class="sig-ops-panel sig-ops-my-todos"><div class="sig-ops-panel-head"><div><h2>' + __('My ToDos') + ' <span class="sig-ops-count">' + esc(data.todo_access ? (summary.todos || 0) : '—') + ((data.todos_has_more || (data.complete && !data.complete.todos)) ? '+' : '') + '</span></h2><p>' + __('Pending follow-ups allocated to your signed-in ERP account.') + '</p></div>' + (data.todo_create ? '<button class="btn btn-default sig-ops-new-todo">' + __('Create a follow-up') + '</button>' : '') + (data.todo_access ? '<button class="btn btn-primary sig-ops-all-todos">' + __('Open My ToDos') + '</button>' : '') + '</div></div>' + todoRows + ((data.todos_has_more || (data.complete && !data.complete.todos)) ? '<div class="sig-ops-footnote">' + __('Showing the first 50. Open My ToDos to view the complete list.') + '</div>' : '') + '</section>' +
            stats + '<section class="sig-ops-stage"><div class="sig-ops-stage-title"><h2>' + __('Delivery stages') + '</h2><span>' + __('Stage work closes from matching evidence.') + '</span></div><div class="sig-ops-stage-flow">' + stages + '</div></section>' +
            '<section class="sig-ops-panel sig-ops-main"><div class="sig-ops-panel-head"><div><h2>' + __('Site cycles') + '</h2><p>' + __('The linked site name opens its cycle. WO and project details stay on the same row.') + '</p></div><div class="sig-ops-actions"><button class="btn btn-default sig-ops-export">' + __('Export Excel') + '</button><button class="btn btn-primary sig-ops-close" ' + (data.can_close_cycles ? '' : 'disabled') + (!selected.size ? ' disabled' : '') + '>' + __('Close selected cycles') + '</button></div></div>' +
            '<div class="sig-ops-toolbar"><nav>' + [['open', __('Open cycles')], ['review', __('Review due')]].map(([key, label]) => '<button data-filter="' + key + '" class="' + (filter === key ? 'active' : '') + '">' + label + '</button>').join('') + '</nav><span class="sig-ops-filter-count">' + filtered.length + ' ' + __('cycles') + '</span></div>' +
            '<div class="sig-ops-selection"><label><input type="checkbox" class="sig-ops-select-visible"> ' + __('Select this page (up to 50)') + '</label><span class="sig-ops-selected-count">' + selected.size + ' ' + __('selected') + '</span><small>' + (filtered.length ? (pageNumber - 1) * pageSize + 1 : 0) + '–' + Math.min(pageNumber * pageSize, filtered.length) + ' ' + __('of') + ' ' + filtered.length + (data.complete && !data.complete.cycles ? ' · ' + __('partial read') : '') + '</small></div>' +
            (rows.length ? '<div class="sig-ops-table-wrap"><table class="sig-ops-table"><thead><tr><th></th><th>' + __('Site / WO') + '</th><th>' + __('Project') + '</th><th>' + __('Stage') + '</th><th>' + __('Pending work') + '</th><th>' + __('Status / delay') + '</th></tr></thead><tbody>' + tableRows + '</tbody></table></div>' + pager : '<div class="sig-ops-empty">' + __('No open cycles in this view.') + '</div>') +
            (data.can_close_cycles ? '<div class="sig-ops-footnote">' + __('Cycle closure clears obsolete pipeline tasks and records the reason. Evidence history stays available.') + '</div>' : '') + '</section>');
        root.find('button[data-filter]').on('click', function () { filter = $(this).data('filter'); pageNumber = 1; selected.clear(); render(); });
        root.find('[data-stage]').on('click', function () { filter = 'stage:' + $(this).data('stage'); pageNumber = 1; selected.clear(); render(); });
        root.find('.sig-ops-refresh').on('click', load);
        root.find('.sig-ops-cycle-check').on('change', function () {
            if (this.checked && !selected.has(this.value) && selected.size >= 50) { this.checked = false; return frappe.msgprint(__('Select up to 50 cycles per bulk closure.')); }
            this.checked ? selected.add(this.value) : selected.delete(this.value);
            this.closest('tr').classList.toggle('selected', this.checked);
            updateSelection(rows);
        });
        root.find('.sig-ops-select-visible').on('change', function () {
            const visible = rows.filter((r) => !r.terminal);
            if (this.checked) {
                const unselected = visible.filter((r) => !selected.has(r.name)), available = Math.max(0, 50 - selected.size);
                unselected.slice(0, available).forEach((r) => selected.add(r.name));
                if (unselected.length > available) frappe.show_alert({message: __('Selected up to 50 cycles. Clear some to select more.'), indicator:'orange'});
            } else visible.forEach((r) => selected.delete(r.name));
            updateSelection(rows);
        });
        root.find('.sig-ops-prev').on('click', () => { pageNumber = Math.max(1, pageNumber - 1); render(); });
        root.find('.sig-ops-next').on('click', () => { pageNumber += 1; render(); });
        root.find('a[data-doctype]').on('click', function (e) { e.preventDefault(); frappe.set_route('Form', $(this).data('doctype'), $(this).data('name')); });
        root.find('.sig-ops-close').on('click', closeSelected);
        root.find('.sig-ops-export').on('click', exportExcel);
        root.find('.sig-ops-all-todos').on('click', () => { frappe.route_options = {allocated_to: frappe.session.user, status: ['not in', ['Closed', 'Cancelled']]}; frappe.set_route('List', 'ToDo'); });
        root.find('.sig-ops-new-todo').on('click', () => frappe.new_doc('ToDo', {allocated_to: frappe.session.user, status: 'Open'}));
    }

    function updateSelection(rows) {
        root.find('.sig-ops-selected-count').text(selected.size + ' ' + __('selected'));
        root.find('.sig-ops-close').prop('disabled', !data.can_close_cycles || !selected.size);
        const live = rows.filter((r) => !r.terminal), checked = live.filter((r) => selected.has(r.name)).length;
        root.find('.sig-ops-select-visible').prop('checked', live.length > 0 && checked === live.length).prop('indeterminate', checked > 0 && checked < live.length);
    }
    function closeSelected() {
        const names = Array.from(selected);
        if (!names.length) return frappe.msgprint(__('Select one or more open site cycles first.'));
        frappe.prompt([{fieldname:'reason', label:__('Closure reason'), fieldtype:'Small Text', reqd:1}], (values) => {
            frappe.call({method:'sig_warehouse.sig_warehouse.operations_workbench.close_cycles', args:{cycles:names, reason:values.reason}})
                .then((r) => { selected.clear(); frappe.show_alert({message: __('Closed {0} site cycles.', [((r.message || {}).closed || []).length]), indicator:'green'}); load(); });
        }, __('Close selected site cycles'), __('Close cycles'));
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
