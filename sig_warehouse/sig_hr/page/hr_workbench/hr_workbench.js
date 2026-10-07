// Role-aware HR navigation, same pattern as finance-workbench: English in __(), Arabic in translations/ar.csv,
// RTL from frappe.boot.lang. ERPNext documents and reports remain authoritative; the only action here is the
// HR email request (HR Manager / System Manager), which never changes a User or Employee.
frappe.pages['hr-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('SIG HR'), single_column: true});
    // Same escape hatch as the Warehouse workbench: the sidebar's SIG HR entry is redirected here by
    // warehouse_workspace_redirect.js; this opens the native workspace once without redirecting back.
    page.add_inner_button(__('Original HR Workspace'), () => {
        window.sessionStorage.setItem('sig_hr_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG HR');
    });
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-hr-home"></main>')
        .attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr')
        .attr('lang', language)
        .appendTo(page.main);

    const today = frappe.datetime.get_today();
    const inDays = (n) => frappe.datetime.add_days(today, n);
    const ACTIVE = ['Employee', 'status', '=', 'Active'];
    const ONB = 'SIG Employee Onboarding';

    const daily = [
        {title: __('Employees'), description: __('Active employee records, contacts, and assignments.'), icon: 'users', doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active'}},
        {title: __('Onboarding board'), description: __('Each employee\'s access, custody ledger, bank, WhatsApp, and compliance checks.'), icon: 'columns', doctype: ONB, route: ['List', ONB, 'Kanban', 'SIG Onboarding Board']},
        {title: __('People readiness'), description: __('One row per employee: login, mobile, custody ledger, and balance.'), icon: 'id-card', doctype: ONB, report: 'SIG People Readiness', route: ['query-report', 'SIG People Readiness']},
        {title: __('Custody ledger balances'), description: __('Every 1322 custody ledger with its employee, balance, and last posting.'), icon: 'book', doctype: ONB, report: 'SIG Custody Ledger Balances', route: ['query-report', 'SIG Custody Ledger Balances']}
    ];

    const attention = [
        {title: __('Iqama expired'), description: __('Active employees past their Iqama expiry (from the monthly Muqeem upload).'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['<', today]},
            metric: {key: 'iqama-expired', filters: [ACTIVE, ['Employee', 'custom_iqama_expiry_date', '<', today]]}},
        {title: __('Iqama due within 30 days'), description: __('Start renewals now.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['between', [today, inDays(30)]]},
            metric: {key: 'iqama-30', filters: [ACTIVE, ['Employee', 'custom_iqama_expiry_date', 'between', [today, inDays(30)]]]}},
        {title: __('Onboarding exceptions'), description: __('Employees with a missing login, ledger, mobile, or identity data.'), doctype: ONB, route: ['List', ONB, 'List'], routeOptions: {status: 'Exception'},
            metric: {key: 'onb-exceptions', filters: [[ONB, 'status', '=', 'Exception']]}},
        {title: __('Email replies to review'), description: __('Official emails received on WhatsApp, waiting for HR to apply.'), doctype: ONB, route: ['List', ONB, 'List'], routeOptions: {proposed_email: ['is', 'set']},
            metric: {key: 'email-replies', filters: [[ONB, 'proposed_email', 'is', 'set']]}}
    ];

    const compliance = [
        {title: __('Iqama renewals (90 days)'), description: __('Iqama expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['<=', inDays(90)]}},
        {title: __('Passport renewals (90 days)'), description: __('Passport expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_passport_expiry_date: ['<=', inDays(90)]}},
        {title: __('Work permit renewals (90 days)'), description: __('Work permit expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_work_permit_expiry: ['<=', inDays(90)]}},
        {title: __('My open tasks'), description: __('Open to-dos assigned to you.'), doctype: 'ToDo', route: ['List', 'ToDo', 'List'], routeOptions: {status: 'Open', allocated_to: frappe.session.user}}
    ];

    const quality = [
        {title: __('No mobile number'), description: __('Cannot receive WhatsApp or appear in attendance.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', cell_number: ['is', 'not set']},
            metric: {key: 'q-mobile', filters: [ACTIVE, ['Employee', 'cell_number', 'is', 'not set']]}},
        {title: __('Login email not deliverable'), description: __('Login is an internal .local address that cannot receive email.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', user_id: ['like', '%.local']},
            metric: {key: 'q-local', filters: [ACTIVE, ['Employee', 'user_id', 'like', '%.local']]}},
        {title: __('Placeholder birth date'), description: __('Date of birth is the 1900-01-01 placeholder.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', date_of_birth: '1900-01-01'},
            metric: {key: 'q-dob', filters: [ACTIVE, ['Employee', 'date_of_birth', '=', '1900-01-01']]}},
        {title: __('No user linked'), description: __('Active employees without a system user.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', user_id: ['is', 'not set']},
            metric: {key: 'q-user', filters: [ACTIVE, ['Employee', 'user_id', 'is', 'not set']]}},
        {title: __('No custody ledger'), description: __('Active employees without a 1322 custody ledger.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_custody_account: ['is', 'not set']},
            metric: {key: 'q-ledger', filters: [ACTIVE, ['Employee', 'custom_custody_account', 'is', 'not set']]}}
    ];

    const requests = [
        {title: __('Approvals queue'), description: __('Leave, expense, and advance requests waiting for a decision.'), doctype: 'Leave Application', report: 'SIG HR Approvals Queue', route: ['query-report', 'SIG HR Approvals Queue']},
        {title: __('Leave applications'), description: __('Not in use yet: leave policies are configured in a later HR stage.'), doctype: 'Leave Application', route: ['List', 'Leave Application', 'List']},
        {title: __('Expense claims'), description: __('Not in use yet.'), doctype: 'Expense Claim', route: ['List', 'Expense Claim', 'List']},
        {title: __('Employee advances'), description: __('Not in use yet.'), doctype: 'Employee Advance', route: ['List', 'Employee Advance', 'List']}
    ];

    function canOpen(item) {
        if (item.roleAny && !item.roleAny.some((role) => frappe.user.has_role(role))) return false;
        if (!item.doctype) return true;
        if (!frappe.model.can_read(item.doctype)) return false;
        if (!item.report) return true;
        const reports = frappe.boot?.allowed_reports;
        if (Array.isArray(reports)) return reports.some((r) => (typeof r === 'string' ? r : r.name) === item.report);
        if (reports && typeof reports === 'object') return item.report in reports;
        return false;
    }

    function card(item, compact) {
        const icon = item.icon ? `<span class="sig-hr-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>` : '';
        const detail = item.description ? `<span class="sig-hr-detail">${frappe.utils.escape_html(item.description)}</span>` : '';
        const metric = item.metric ? `<span class="sig-hr-metric" data-metric-key="${frappe.utils.escape_html(item.metric.key)}">—</span>` : '';
        return `<button type="button" class="sig-hr-card ${compact ? 'sig-hr-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route || null))}"
                    data-route-options="${frappe.utils.escape_html(JSON.stringify(item.routeOptions || null))}"
                    data-action="${frappe.utils.escape_html(item.action || '')}">
            <span class="sig-hr-card-top">${icon}<i class="fa fa-external-link sig-hr-open" aria-hidden="true"></i></span>
            <span class="sig-hr-card-title">${frappe.utils.escape_html(item.title)}</span>${metric}${detail}
        </button>`;
    }

    function section(title, description, items, compact = true) {
        const available = items.filter(canOpen);
        if (!available.length) return '';
        return `<section class="sig-hr-section">
            <div class="sig-hr-section-heading"><h2>${frappe.utils.escape_html(title)}</h2><p>${frappe.utils.escape_html(description)}</p></div>
            <div class="sig-hr-grid ${compact ? 'sig-hr-grid-compact' : ''}">${available.map((i) => card(i, compact)).join('')}</div>
        </section>`;
    }

    const actions = [
        {title: __('Request official emails'), description: __('Ask employees on .local logins, by WhatsApp, to reply with their official email. Replies are collected for HR review; nothing is changed automatically.'), icon: 'envelope', roleAny: ['HR Manager', 'System Manager'], action: 'email-request'}
    ];

    root.html(`<header class="sig-hr-header">
            <div><div class="sig-hr-eyebrow">${__('Human Resources')}</div>
                <h1>${__('HR workbench')}</h1>
                <p>${__('Daily people work, compliance, and the link between employees and finance.')}</p></div>
            <span class="sig-hr-header-mark" aria-hidden="true"><i class="fa fa-users"></i></span>
        </header>
        ${section(__('Daily people work'), __('Open the employee records and the onboarding checks.'), daily, false)}
        ${section(__('Needs attention'), __('Counts that need action today.'), attention)}
        ${section(__('Compliance'), __('Renewal queues filtered by expiry date, and your open tasks.'), compliance)}
        ${section(__('Data quality'), __('Gaps that block WhatsApp, logins, or custody postings.'), quality)}
        ${section(__('HR actions'), __('Controlled actions for HR managers.'), actions)}
        ${section(__('Requests and approvals'), __('Employee requests. Leave, expense, and advance processes start in a later HR stage.'), requests)}
        <p class="sig-hr-footnote">${__('This page is navigation only. Document, workflow, and report permissions remain enforced by ERPNext.')}</p>`);

    root.find('.sig-hr-card').on('click', function () {
        const action = $(this).attr('data-action');
        if (action === 'email-request') { openEmailRequest(); return; }
        let route, routeOptions;
        try { route = JSON.parse($(this).attr('data-route')); } catch (e) { return; }
        try { routeOptions = JSON.parse($(this).attr('data-route-options') || 'null'); } catch (e) { routeOptions = null; }
        if (routeOptions) frappe.route_options = routeOptions;
        if (Array.isArray(route) && route.length) frappe.set_route(...route);
    });

    function openEmailRequest() {
        const M = 'sig_warehouse.sig_hr.email_request.send_email_requests';
        frappe.call({method: M, args: {mode: 'preview'}}).then((r) => {
            const p = r.message || {};
            const list = (p.recipients || []).map((x) => `<li>${frappe.utils.escape_html(x.name)} · ${frappe.utils.escape_html(x.phone)}${x.already_asked ? ' · ' + __('already asked') : ''}</li>`).join('');
            const d = new frappe.ui.Dialog({
                title: __('Request official emails'),
                fields: [{fieldtype: 'HTML', options: `<p>${__('Recipients')}: <b>${p.count || 0}</b></p><ul class="sig-hr-list">${list}</ul>
                    <p class="text-muted">${__('Message')}:</p><pre class="sig-hr-pre">${frappe.utils.escape_html(p.text || '')}</pre>`}],
                primary_action_label: __('Send to recipients'),
                primary_action() {
                    frappe.confirm(__('Send the WhatsApp message to {0} employees?', [p.count || 0]), () => {
                        frappe.call({method: M, args: {mode: 'send'}, freeze: true}).then((s) => {
                            const m = s.message || {};
                            frappe.msgprint(__('Sent: {0}. Failed: {1}. Skipped (asked recently): {2}.', [m.sent || 0, (m.failed || []).length, m.skipped_recently_asked || 0]));
                            d.hide();
                        });
                    });
                },
                secondary_action_label: __('Send test to test phone'),
                secondary_action() {
                    frappe.call({method: M, args: {mode: 'test'}, freeze: true}).then((s) => {
                        frappe.msgprint(__('Test message sent: {0}.', [(s.message || {}).sent || 0]));
                    });
                }
            });
            d.show();
        });
    }

    [...attention, ...quality].forEach((item) => {
        if (!item.metric || !canOpen(item)) return;
        frappe.call({
            method: 'frappe.desk.doctype.number_card.number_card.get_result',
            args: {doc: JSON.stringify({function: 'Count', document_type: item.doctype}), filters: JSON.stringify(item.metric.filters)}
        }).then((response) => {
            const value = Number(response.message);
            root.find(`[data-metric-key="${item.metric.key}"]`).text(
                Number.isFinite(value) ? new Intl.NumberFormat(language.replace('_', '-'), {maximumFractionDigits: 0}).format(value) : '—');
        }).catch(() => root.find(`[data-metric-key="${item.metric.key}"]`).text('—'));
    });
};
