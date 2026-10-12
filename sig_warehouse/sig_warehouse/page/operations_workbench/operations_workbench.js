frappe.pages['operations-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Field Delivery'), single_column: true});
    page.add_inner_button(__('Original Projects Workspace'), () => {
        window.sessionStorage.setItem('sig_projects_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Projects');
    });
    const root = $('<main class="sig-ops-home"></main>').appendTo(page.main);
    const esc = (value) => frappe.utils.escape_html(String(value || ''));
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : '—';

    function render(data) {
        const c = data.counts || {};
        const todos = data.todos || [];
        const projects = data.projects || [];
        const cycles = data.cycles || [];
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        root.html(`<header class="sig-ops-header"><div><div class="sig-ops-eyebrow">${__('SIG Projects')}</div>
            <h1>${__('Field Delivery')}</h1><p>${__('Your allocated follow-ups and current project and site-cycle records.')}</p></div>
            <span class="sig-ops-mark" aria-hidden="true"><i class="fa fa-map-marker"></i></span></header>
            <section class="sig-ops-stats" aria-label="${__('Overview')}">
                <div><strong>${esc(c.todos)}</strong><span>${__('Open tasks allocated to you')}</span></div>
                <div><strong>${esc(c.overdue)}</strong><span>${__('Overdue allocated tasks')}</span></div>
                <div><strong>${esc(c.projects)}</strong><span>${__('Projects loaded for your role')}</span></div>
                <div><strong>${esc(c.cycles)}</strong><span>${__('Site cycles loaded for your role')}</span></div>
            </section>
            <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('My open tasks')}</h2><p>${__('Tasks allocated to your ERP user.')}</p></div></div>
                ${todos.length ? `<div class="sig-ops-list">${todos.map((row) => `<button class="sig-ops-row" data-doctype="ToDo" data-name="${esc(row.name)}"><span><b>${esc(row.description || __('Follow-up'))}</b><small>${esc(row.reference_type)}${row.reference_name ? ` · ${esc(row.reference_name)}` : ''}</small></span><span class="sig-ops-date">${date(row.date)}</span></button>`).join('')}</div>` : `<div class="sig-ops-empty">${__('No open tasks are allocated to you.')}</div>`}</section>
            <div class="sig-ops-columns"><section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('Projects')}</h2><p>${__('Permission-filtered project overview.')}</p></div></div>
                ${projects.length ? `<div class="sig-ops-list">${projects.map((row) => `<button class="sig-ops-row" data-doctype="Project" data-name="${esc(row.name)}"><span><b>${esc(row.project_name || row.name)}</b><small>${esc(row.status || __('Status unavailable'))}</small></span><span class="sig-ops-date">${date(row.expected_end_date)}</span></button>`).join('')}</div>` : `<div class="sig-ops-empty">${__('No projects are available to your role.')}</div>`}</section>
                <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('Site cycles')}</h2><p>${__('Permission-filtered field-delivery records.')}</p></div></div>
                ${cycles.length ? `<div class="sig-ops-list">${cycles.map((row) => `<button class="sig-ops-row" data-doctype="SIG Site Cycle" data-name="${esc(row.name)}"><span><b>${esc(row.site_key || row.site || row.name)}</b><small>${esc(row.project)} · ${esc(row.stage)}</small></span><span class="sig-ops-date">${date(row.stage_due_on)}</span></button>`).join('')}</div>` : `<div class="sig-ops-empty">${__('No site cycles are available to your role.')}</div>`}</section></div>`);
        root.find('.sig-ops-row').on('click', function () {
            const doctype = $(this).attr('data-doctype');
            const name = $(this).attr('data-name');
            if (doctype && name) frappe.set_route('Form', doctype, name);
        });
    }

    root.html(`<div class="sig-ops-loading">${__('Loading field delivery records…')}</div>`);
    frappe.call({method: 'sig_warehouse.sig_warehouse.operations_workbench.get_overview'})
        .then((r) => render(r.message || {}))
        .catch(() => root.html(`<div class="sig-ops-error">${__('Field delivery records could not be loaded.')}</div>`));
};
