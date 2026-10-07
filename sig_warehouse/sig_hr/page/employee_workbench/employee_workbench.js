// Employee self-service page (replaces the plain "SIG - My Work" workspace for users holding the Employee or
// Employee Self Service role - see warehouse_workspace_redirect.js). Same pattern as hr-workbench / finance-workbench:
// English in __(), Arabic in translations/ar.csv, RTL from frappe.boot.lang, role-aware cards (a card is shown only if
// the user can read/create the target), filtered routes. Navigation only: ERPNext permissions and User Permissions
// (an employee sees only their own records) remain authoritative.
frappe.pages['employee-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Employee Page'), single_column: true});
    page.add_inner_button(__('Original Employee Workspace'), () => {
        window.sessionStorage.setItem('sig_my_work_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG - My Work');
    });
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-emp-home"></main>')
        .attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr')
        .attr('lang', language)
        .appendTo(page.main);

    const FIELDS = ['name', 'employee_name', 'custom_iqama_expiry_date', 'custom_passport_expiry_date', 'custom_work_permit_expiry'];

    function canOpen(item) {
        if (!item.doctype) return true;
        if (item.needsCreate) return frappe.model.can_create(item.doctype);
        return frappe.model.can_read(item.doctype);
    }

    // Days left until a date, colour class and text (expired / due soon / ok). Dates come from the employee's own record.
    function expiryInfo(value) {
        if (!value) return {text: __('Not recorded'), cls: 'sig-emp-metric-muted'};
        const days = frappe.datetime.get_day_diff(value, frappe.datetime.get_today());
        const date = frappe.datetime.str_to_user(value);
        if (days < 0) return {text: `${date} · ${__('Expired {0} days ago', [Math.abs(days)])}`, cls: 'sig-emp-metric-bad'};
        if (days <= 30) return {text: `${date} · ${__('{0} days left', [days])}`, cls: 'sig-emp-metric-warn'};
        return {text: date, cls: ''};
    }

    function card(item) {
        const icon = item.icon ? `<span class="sig-emp-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>` : '';
        const detail = item.description ? `<span class="sig-emp-detail">${frappe.utils.escape_html(item.description)}</span>` : '';
        const metric = item.metricText ? `<span class="sig-emp-metric ${item.metricClass || ''}">${frappe.utils.escape_html(item.metricText)}</span>` : '';
        return `<button type="button" class="sig-emp-card"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route || null))}"
                    data-route-options="${frappe.utils.escape_html(JSON.stringify(item.routeOptions || null))}">
            <span class="sig-emp-card-top">${icon}<i class="fa fa-external-link sig-emp-open" aria-hidden="true"></i></span>
            <span class="sig-emp-card-title">${frappe.utils.escape_html(item.title)}</span>${metric}${detail}
        </button>`;
    }

    function section(title, description, items) {
        const available = items.filter(canOpen);
        if (!available.length) return '';
        return `<section class="sig-emp-section">
            <div class="sig-emp-section-heading"><h2>${frappe.utils.escape_html(title)}</h2><p>${frappe.utils.escape_html(description)}</p></div>
            <div class="sig-emp-grid">${available.map(card).join('')}</div>
        </section>`;
    }

    function render(emp) {
        const me = emp && emp.name ? emp : null;
        const mine = me ? {employee: me.name} : null;
        const tasks = me ? [
            {title: __('Raise an HR ticket'), description: __('Ask HR for help, a correction, or a document.'), icon: 'life-ring', doctype: 'SIG HR Ticket', needsCreate: true, route: ['Form', 'SIG HR Ticket', 'new'], routeOptions: mine},
            {title: __('My HR tickets'), description: __('Track the tickets you raised.'), icon: 'ticket', doctype: 'SIG HR Ticket', route: ['List', 'SIG HR Ticket', 'List'], routeOptions: mine},
            {title: __('My check-ins'), description: __('Your attendance punches from WhatsApp and the office.'), icon: 'clock-o', doctype: 'Employee Checkin', route: ['List', 'Employee Checkin', 'List'], routeOptions: mine},
            {title: __('My employee record'), description: __('View your details. Ask HR to correct anything that is wrong.'), icon: 'id-card', doctype: 'Employee', route: ['Form', 'Employee', me.name]}
        ] : [];
        const docs = me ? [
            {title: __('Iqama expiry'), description: __('From your employee record. Contact HR to update it.'), icon: 'calendar', doctype: 'Employee', route: ['Form', 'Employee', me.name], metricText: expiryInfo(me.custom_iqama_expiry_date).text, metricClass: expiryInfo(me.custom_iqama_expiry_date).cls},
            {title: __('Passport expiry'), description: __('From your employee record. Contact HR to update it.'), icon: 'calendar', doctype: 'Employee', route: ['Form', 'Employee', me.name], metricText: expiryInfo(me.custom_passport_expiry_date).text, metricClass: expiryInfo(me.custom_passport_expiry_date).cls},
            {title: __('Work permit expiry'), description: __('From your employee record. Contact HR to update it.'), icon: 'calendar', doctype: 'Employee', route: ['Form', 'Employee', me.name], metricText: expiryInfo(me.custom_work_permit_expiry).text, metricClass: expiryInfo(me.custom_work_permit_expiry).cls}
        ] : [];
        // Leave, expense claim, advance and payslip cards are added here when HR-2 / HR-3 / HR-4 go live
        // (they have no records yet, so a card would only lead to an empty list).

        const hello = me ? __('Welcome, {0}', [frappe.utils.escape_html(me.employee_name || me.name)]) : __('Welcome');
        const missing = me ? '' : `<div class="sig-emp-notice">${__('No employee record is linked to this login. Ask HR to link your user to your employee record.')}</div>`;
        root.html(`<header class="sig-emp-header">
                <div><div class="sig-emp-eyebrow">${__('My work')}</div>
                    <h1>${__('Employee page')}</h1>
                    <p>${hello}</p></div>
                <span class="sig-emp-header-mark" aria-hidden="true"><i class="fa fa-user-circle-o"></i></span>
            </header>
            ${missing}
            ${section(__('My tasks'), __('Open your requests, tickets, and attendance.'), tasks)}
            ${section(__('My documents'), __('Expiry dates from your employee record.'), docs)}
            <p class="sig-emp-footnote">${__('This page is navigation only. Document, workflow, and report permissions remain enforced by ERPNext.')}</p>`);

        root.find('.sig-emp-card').on('click', function () {
            let route, routeOptions;
            try { route = JSON.parse($(this).attr('data-route')); } catch (e) { return; }
            try { routeOptions = JSON.parse($(this).attr('data-route-options') || 'null'); } catch (e) { routeOptions = null; }
            if (routeOptions) frappe.route_options = routeOptions;
            if (Array.isArray(route) && route.length) frappe.set_route(...route);
        });
    }

    frappe.call({
        method: 'frappe.client.get_value',
        args: {doctype: 'Employee', filters: {user_id: frappe.session.user, status: 'Active'}, fieldname: FIELDS}
    }).then((r) => render(r.message), () => render(null));
};
