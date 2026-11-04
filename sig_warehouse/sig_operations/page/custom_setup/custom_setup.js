frappe.pages['custom-setup'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Custom Setup'), single_column: true});
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-hr-home"></main>')
        .attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr')
        .attr('lang', language)
        .appendTo(page.main);

    const cards = [
        {title: __('Employee project assignments'), description: __('Maintain approved, dated links between employees, projects, and their project roles.'), doctype: 'SIG Employee Project Assignment', route: ['List', 'SIG Employee Project Assignment', 'List'], roles: ['HR Manager', 'HR User', 'Projects Manager', 'Projects User', 'System Manager'], icon: 'users'},
        {title: __('Candidate onboarding'), description: __('Create an HR-controlled intake, request the structured reply, and review it before Employee creation.'), doctype: 'SIG Candidate Intake', route: ['List', 'SIG Candidate Intake', 'List'], roles: ['HR Manager', 'System Manager'], icon: 'user-plus'},
        {title: __('Employee onboarding checks'), description: __('Review the existing employee readiness, access, custody, bank, WhatsApp, and compliance checks.'), doctype: 'SIG Employee Onboarding', route: ['List', 'SIG Employee Onboarding', 'List'], roles: ['HR Manager', 'HR User', 'System Manager'], icon: 'address-card'},
        {title: __('Employees'), description: __('Open native Employee records. Changes to a linked employee can affect the linked User; follow the HR change controls.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], roles: ['HR Manager', 'HR User', 'System Manager'], icon: 'id-card'},
        {title: __('User access'), description: __('Review employee-linked Users and Role Profiles as a separate IT/HR approval step.'), doctype: 'User', route: ['List', 'User', 'List'], roles: ['HR Manager', 'System Manager'], icon: 'user'},
        {title: __('Payroll assignments'), description: __('Review native Salary Structure Assignments after payroll approval; proposed intake salary is not posted automatically.'), doctype: 'Salary Structure Assignment', route: ['List', 'Salary Structure Assignment', 'List'], roles: ['HR Manager', 'Accounts Manager', 'System Manager'], icon: 'money'},
        {title: __('Field Reporter Maps'), description: __('Maintain verified Employee-to-phone mappings for field reports.'), doctype: 'SIG Field Reporter Map', route: ['List', 'SIG Field Reporter Map', 'List'], roles: ['HR Manager', 'Projects Manager', 'SIG Field Ops', 'System Manager'], icon: 'phone'},
        {title: __('Workbook setup'), description: __('Manage Excel/RV80/SIGPC project, builder, tag, and workbook integration settings.'), doctype: 'SIG Excel Setup', route: ['Form', 'SIG Excel Setup', 'SIG Excel Setup'], roles: ['SIG Excel Setup Editor', 'SIG Excel Setup Reader', 'System Manager'], icon: 'table'}
    ];

    const available = cards.filter((card) =>
        card.roles.some((role) => frappe.user.has_role(role)) && frappe.model.can_read(card.doctype));
    const html = available.map((item) => `
        <button type="button" class="sig-hr-card sig-hr-card--blue" data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}">
            <span class="sig-hr-card-top"><span class="sig-hr-icon"><i class="fa fa-${item.icon}"></i></span><i class="fa fa-external-link sig-hr-open"></i></span>
            <span class="sig-hr-card-title">${frappe.utils.escape_html(item.title)}</span>
            <span class="sig-hr-detail">${frappe.utils.escape_html(item.description)}</span>
        </button>`).join('');

    root.html(`<header class="sig-hr-header"><div><div class="sig-hr-eyebrow">${__('ERP configuration')}</div>
        <h1>${__('Custom Setup')}</h1>
        <p>${__('A single place to reach business setup records. Each linked system remains responsible for its own data, approvals, and permissions.')}</p></div>
        <span class="sig-hr-header-mark" aria-hidden="true"><i class="fa fa-sliders"></i></span></header>
        <section class="sig-hr-section"><div class="sig-hr-section-heading"><h2>${__('People and project setup')}</h2>
        <p>${__('Employee assignments are stored in ERP as dated, approved records. Workbook configuration is a separate integration concern.')}</p></div>
        <div class="sig-hr-grid">${html || `<p>${__('You do not have access to any setup records on this page.')}</p>`}</div></section>
        <p class="sig-hr-footnote">${__('This page only provides navigation. Record permissions and linked-record access are enforced by ERPNext.')}</p>`);

    root.find('.sig-hr-card').on('click', function () {
        try {
            const route = JSON.parse($(this).attr('data-route'));
            if (Array.isArray(route) && route.length) frappe.set_route(...route);
        } catch (e) { /* Ignore a malformed navigation target. */ }
    });
};
