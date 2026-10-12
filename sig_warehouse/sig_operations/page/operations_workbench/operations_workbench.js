frappe.pages['operations-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Operations Workbench'), single_column: true});
    page.add_inner_button(__('Material Request Pipeline'), () => {
        window.sessionStorage.setItem('sig_operations_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Operations');
    });
    page.add_inner_button(__('Original Projects Workspace'), () => {
        window.sessionStorage.setItem('sig_projects_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Projects');
    });
    const root = $('<main class="sig-ops-home"></main>').appendTo(page.main);
    const esc = (value) => frappe.utils.escape_html(value == null ? '' : String(value));
    const date = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 10)) : '—';
    const dateTime = (value) => value ? frappe.datetime.str_to_user(String(value).slice(0, 16)) : __('No recorded update');

    function render(data) {
        const c = data.summary || {};
        const todos = data.todos || [];
        const projects = data.projects || [];
        const exceptions = data.exceptions || [];
        const complete = data.complete || {};
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        root.html(`<header class="sig-ops-header"><div><div class="sig-ops-eyebrow">${__('SIG Operations')}</div>
            <h1>${__('Operations Workbench')}</h1><p>${__('Field delivery: your allocated follow-ups and current project and site-cycle records.')}</p></div>
            <span class="sig-ops-mark" aria-hidden="true"><i class="fa fa-map-marker"></i></span></header>
            <section class="sig-ops-stats" aria-label="${__('Overview')}">
                <div><strong>${esc(c.todos || 0)}</strong><span>${__('Open tasks allocated to you')}${complete.todos ? '' : ` · ${__('partial list')}`}</span></div>
                <div class="is-warning"><strong>${esc(c.overdue_todos || 0)}</strong><span>${__('Overdue allocated tasks')}${complete.todos ? '' : ` · ${__('partial list')}`}</span></div>
                <div><strong>${esc(c.cycles || 0)}</strong><span>${__('Open site cycles')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
                <div class="is-danger"><strong>${esc(c.delayed || 0)}</strong><span>${__('Delayed open cycles')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
                <div class="is-warning"><strong>${esc(c.aged || 0)}</strong><span>${__('Aged open cycles')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
                <div><strong>${esc(c.past_due || 0)}</strong><span>${__('Past-due stage dates')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
            </section>
            <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('Needs attention')}</h2><p>${__('Open site cycles ordered by delay, age, and stage date.')}</p></div><span>${esc(c.exceptions || 0)} ${__('total')} · ${esc(exceptions.length)} ${__('top rows shown')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
                ${exceptions.length ? `<div class="sig-ops-table-wrap"><table class="sig-ops-table"><thead><tr><th>${__('Site')}</th><th>${__('Project / stage')}</th><th>${__('Signals and reason')}</th><th>${__('Stage date')}</th><th>${__('Last recorded activity')}</th></tr></thead><tbody>${exceptions.map((row) => {
                    const signals = [row.delayed ? __('Delayed') : '', row.aged ? __('Aged') : '', row.past_due ? __('Stage date passed') : ''].filter(Boolean);
                    return `<tr class="sig-ops-exception" data-doctype="SIG Site Cycle" data-name="${esc(row.name)}"><td><b>${esc(row.site)}</b></td><td>${row.project ? `<span>${esc(row.project)}</span>` : ''}<small>${esc(row.stage)}</small></td><td><div class="sig-ops-signals">${signals.map((label) => `<span>${esc(label)}</span>`).join('')}</div><small>${esc(row.delay_reason)}</small></td><td>${date(row.stage_due_on)}</td><td>${dateTime(row.last_event_at)}</td></tr>`;
                }).join('')}</tbody></table></div>` : `<div class="sig-ops-empty">${__('No delayed, aged, or past-due open cycles are visible to your role.')}</div>`}</section>
            <div class="sig-ops-columns"><section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('Project summary')}</h2><p>${__('Open cycle counts for projects you can read.')}</p></div><span>${esc(projects.length)} ${__('projects')}${complete.cycles ? '' : ` · ${__('partial list')}`}</span></div>
                ${projects.length ? `<div class="sig-ops-table-wrap"><table class="sig-ops-table"><thead><tr><th>${__('Project')}</th><th>${__('Open cycles')}</th><th>${__('Delayed')}</th><th>${__('Aged')}</th><th>${__('Past due')}</th></tr></thead><tbody>${projects.map((row) => `<tr class="sig-ops-project" data-doctype="Project" data-name="${esc(row.name)}"><td><b>${esc(row.project_name)}</b><small>${esc(row.status)}</small></td><td>${esc(row.cycles)}</td><td>${esc(row.delayed)}</td><td>${esc(row.aged)}</td><td>${esc(row.past_due)}</td></tr>`).join('')}</tbody></table></div>` : `<div class="sig-ops-empty">${__('No open cycles linked to projects you can read.')}</div>`}</section>
                <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('My open tasks')}</h2><p>${__('Tasks allocated to your ERP user.')}</p></div><span>${esc(c.todos || 0)} ${complete.todos ? '' : `· ${__('partial list')}`}</span></div>
                    ${todos.length ? `<div class="sig-ops-list">${todos.map((row) => `<button class="sig-ops-row" data-doctype="ToDo" data-name="${esc(row.name)}"><span><b>${esc(row.description || __('Follow-up'))}</b><small>${esc(row.reference_type)}${row.reference_name ? ` · ${esc(row.reference_name)}` : ''}</small></span><span class="sig-ops-date">${date(row.date)}</span></button>`).join('')}</div>` : `<div class="sig-ops-empty">${__('No open tasks are allocated to you.')}</div>`}</section></div>`);
        root.find('[data-doctype][data-name]').on('click', function () {
            const doctype = $(this).attr('data-doctype');
            const name = $(this).attr('data-name');
            if (doctype && name) frappe.set_route('Form', doctype, name);
        });
    }

    root.html(`<div class="sig-ops-loading">${__('Loading field delivery records…')}</div>`);
    frappe.call({method: 'sig_warehouse.sig_warehouse.operations_workbench.get_overview'})
        .then((r) => render(r.message || {}), () => root.html(`<div class="sig-ops-error">${__('Field delivery records could not be loaded.')}</div>`));
};
