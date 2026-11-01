// The home page uses the same role-filtered Page list as the existing SIG Hub.
frappe.pages['sig-hub'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: '', single_column: true });
    $(wrapper).find('.page-head').hide();
    const root = $('<main class="sig-hub"></main>').appendTo(page.main);
    const hero = $('<header class="sig-hub-head"><div class="sig-hub-kicker"></div><h1></h1><p></p></header>').appendTo(root);
    hero.find('.sig-hub-kicker').text(__('Your personal workspace'));
    hero.find('h1').text(__('My Page'));
    hero.find('p').text(__('Your priorities and work in one place.'));
    const tasksSection = $('<section class="sig-hub-section"><h2></h2><div class="sig-hub-tasks" aria-live="polite"></div></section>').appendTo(root);
    tasksSection.find('h2').text(__('My focus and open tasks'));
    if (frappe.model.can_create('ToDo')) {
        $('<button type="button" class="sig-hub-add"></button>').text(__('Add a task')).appendTo(tasksSection.find('h2'))
            .on('click', () => frappe.new_doc('ToDo', { allocated_to: frappe.session.user }));
    }
    const tasks = tasksSection.find('.sig-hub-tasks').text(__('Loading...'));
    const benchSection = $('<section class="sig-hub-section"><h2></h2><div class="sig-hub-grid"></div></section>').appendTo(root);
    benchSection.find('h2').text(__('Workbenches'));
    const grid = benchSection.find('.sig-hub-grid').text(__('Loading...'));
    const moreSection = $('<section class="sig-hub-section"><h2></h2><div class="sig-hub-grid"></div></section>').appendTo(root);
    moreSection.find('h2').text(__('Other available SIG tools'));
    const more = moreSection.find('.sig-hub-grid');
    const targets = [
        ['Operations', 'operations-workbench'],
        ['Finance', 'finance-workbench'],
        ['HR', 'hr-workbench'],
        ['Warehouse', 'warehouse-workspace'],
        ['Petty Cash', 'pc-invoice-review']
    ];
    function card(label, description, route, target = grid) {
        const link = $('<a class="sig-hub-card" href="#"><strong></strong><span></span></a>').appendTo(target);
        link.find('strong').text(__(label));
        link.find('span').text(__(description));
        link.on('click', (e) => { e.preventDefault(); frappe.set_route(route); });
    }
    frappe.call({ method: 'sig_warehouse.sig_warehouse.hub.get_cards' }).then((r) => {
        grid.empty();
        const all = ((r && r.message) || []).flatMap((group) => group.cards || []);
        targets.forEach(([label, name]) => {
            const entry = all.find((item) => item.route && item.route[0] === name);
            if (entry) card(label, entry.description, entry.route);
        });
        const employee = all.find((item) => item.route && item.route[0] === 'employee-workbench');
        if (employee) card('My employee page', employee.description, employee.route, more);
        if ((frappe.user_roles || []).includes('System Manager')) {
            card('Setup', 'System configuration and administration', ['setup', 'home'], more);
        }
        if (!grid.children().length) grid.text(__('No workbench is available for your roles.'));
        const main = new Set(targets.map((item) => item[1]).concat(['employee-workbench']));
        all.filter((item) => item.route && !main.has(item.route[0])).forEach((item) => {
            card(item.label, item.description, item.route, more);
        });
        if (!more.children().length) moreSection.hide();
    }).catch(() => grid.text(__('Workbenches could not be loaded.')));

    function loadTasks() {
    if (!frappe.model.can_read('ToDo')) {
        tasks.text(__('Tasks are unavailable for your role.'));
        return;
    }
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'ToDo',
            filters: { allocated_to: frappe.session.user, status: ['not in', ['Closed', 'Cancelled']] },
            fields: ['name', 'description', 'date'],
            order_by: 'date asc',
            limit_page_length: 8
        }
    }).then((r) => {
        tasks.empty();
        const rows = (r && r.message) || [];
        if (!rows.length) return tasks.text(__('No open tasks assigned to you.'));
        rows.forEach((row) => {
            const link = $('<a href="#" class="sig-hub-task"><strong></strong><span></span></a>').appendTo(tasks);
            // Descriptions can contain rich text; show text only.
            const description = new DOMParser().parseFromString(row.description || '', 'text/html').body.textContent.trim();
            link.find('strong').text(description || row.name);
            link.find('span').text(row.date || __('No due date'));
            link.on('click', (e) => { e.preventDefault(); frappe.set_route('Form', 'ToDo', row.name); });
        });
    }).catch(() => tasks.text(__('Your tasks could not be loaded.')));
    }
    $(wrapper).on('sig-refresh-tasks', loadTasks);
    loadTasks();
};

frappe.pages['sig-hub'].on_page_show = function (wrapper) {
    $(wrapper).trigger('sig-refresh-tasks');
};
