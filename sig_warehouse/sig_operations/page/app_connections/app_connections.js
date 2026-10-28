frappe.pages['app-connections'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('App Connections'), single_column: true});
    const root = $('<div class="sig-connections"></div>').appendTo(page.main);
    function load() {
        frappe.call({method: 'sig_warehouse.sig_operations.app_connections.status'}).then(({message: s}) => {
            root.empty();
            const card = $('<section class="connection-card"></section>').appendTo(root);
            $('<h3>Todoist</h3>').appendTo(card);
            $('<p></p>').text(s.connected ? __('Connected') : __('Not connected')).appendTo(card);
            if (!s.configured) $('<p></p>').text(__('Ask your ERP administrator to configure the Todoist app.')).appendTo(card);
            if (s.connected) {
                $('<p></p>').text(s.project_name ? __('Project: {0}', [s.project_name]) : __('Choose a project for your ERP tasks.')).appendTo(card);
                $('<button class="btn btn-default btn-sm"></button>').text(__('Choose project')).appendTo(card).on('click', chooseProject);
                $('<button class="btn btn-default btn-sm" style="margin-left:8px"></button>').text(__('Disconnect')).appendTo(card).on('click', () => {
                    frappe.confirm(__('Disconnect your Todoist account?'), () => frappe.call({method:'sig_warehouse.sig_operations.app_connections.disconnect'}).then(load));
                });
            } else if (s.configured) {
                $('<button class="btn btn-primary btn-sm"></button>').text(__('Connect to Todoist')).appendTo(card).on('click', () => {
                    frappe.call({method:'sig_warehouse.sig_operations.app_connections.begin'}).then(r => { window.location.assign(r.message); });
                });
            }
            $('<p class="text-muted connection-note"></p>').text(__('New ERP ToDos assigned to 9eskot9 and selected SNB-to-ERP import issues are sent one way to this Todoist project. ERP remains the source of truth; completion is not synchronized back.')).appendTo(card);
            const delivery = $('<section class="delivery-status"></section>').appendTo(root);
            $('<h4></h4>').text(__('Recent ERP task deliveries')).appendTo(delivery);
            if (!s.deliveries || !s.deliveries.length) {
                $('<p class="text-muted"></p>').text(__('No ERP tasks have been queued for Todoist yet.')).appendTo(delivery);
            } else {
                const list = $('<ul></ul>').appendTo(delivery);
                s.deliveries.forEach(item => {
                    const label = `${item.task_content || item.source_name || item.source_type} — ${item.delivery_status}`;
                    $('<li></li>').text(label + (item.last_error ? `: ${item.last_error}` : '')).appendTo(list);
                });
            }
        });
    }
    function chooseProject() {
        frappe.call({method:'sig_warehouse.sig_operations.app_connections.projects'}).then(({message: projects}) => {
            if (!projects.length) { frappe.msgprint(__('No accessible Todoist projects found.')); return; }
            const dialog = new frappe.ui.Dialog({title: __('Choose Todoist project'), fields: [{fieldname:'project', fieldtype:'Select', label:__('Project'), reqd:1, options: projects.map(p => ({label: p.name, value: p.id}))}], primary_action_label:__('Save'), primary_action(values) {
                frappe.call({method:'sig_warehouse.sig_operations.app_connections.select_project', args:{project_id:values.project}}).then(() => {dialog.hide(); load();});
            }});
            dialog.show();
        });
    }
    load();
};
