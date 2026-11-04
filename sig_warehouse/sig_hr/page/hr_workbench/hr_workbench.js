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
        {variant: 'blue', title: __('Custom Setup'), description: __('Employee-to-project assignments, onboarding checks, and workbook setup.'), icon: 'sliders', route: ['custom-setup']},
        {variant: 'blue', title: __('Employee project assignments'), description: __('Approved, dated project roles for employees.'), icon: 'users', doctype: 'SIG Employee Project Assignment', route: ['List', 'SIG Employee Project Assignment', 'List']},
        {variant: 'cyan', title: __('Candidate onboarding'), description: __('Start and review a candidate intake.'), icon: 'user-plus', roleAny: ['HR Manager', 'System Manager'], doctype: 'SIG Candidate Intake', route: ['List', 'SIG Candidate Intake', 'List']},
        {variant: 'blue', title: __('Employees'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"24\" cy=\"15\" r=\"8\" fill=\"#f8e5d6\"/><path d=\"M8 40c1-10 7-15 16-15s15 5 16 15z\" fill=\"#dcecff\"/></svg>", description: __('Active employee records, contacts, and assignments.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active'}},
        {variant: 'blue', title: __('Onboarding board'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><path d=\"M24 22v14m-7-7h14\"/></svg>", description: __('Each employee\'s access, custody ledger, bank, WhatsApp, and compliance checks.'), doctype: ONB, route: ['List', ONB, 'Kanban', 'SIG Onboarding Board']},
        {variant: 'blue', title: __('People readiness'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"10\" width=\"38\" height=\"29\" rx=\"4\" fill=\"#e8f0ff\"/><circle cx=\"16\" cy=\"21\" r=\"4\"/><path d=\"M10 32c1-4 3-6 6-6s5 2 6 6\"/><path d=\"m27 25 3 3 7-8\"/></svg>", description: __('One row per employee: login, mobile, custody ledger, and balance.'), doctype: ONB, report: 'SIG People Readiness', route: ['query-report', 'SIG People Readiness']},
        {variant: 'blue', title: __('Custody ledger balances'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M33 18v17M36 21c-2-2-6-2-6 1 0 3 6 2 6 5s-4 3-6 1\"/></svg>", description: __('Every 1322 custody ledger with its employee, balance, and last posting.'), doctype: ONB, report: 'SIG Custody Ledger Balances', route: ['query-report', 'SIG Custody Ledger Balances']}
    ];

    const attendance = [
        {variant: 'blue', title: __('Attendance'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"9\" width=\"36\" height=\"32\" rx=\"4\" fill=\"#fff0dc\"/><path d=\"M6 18h36M15 5v8M33 5v8\"/><path d=\"m17 29 5 5 10-12\"/></svg>", description: __('Daily attendance and employee history.'), doctype: 'Employee Checkin', route: ['hr-attendance']}
    ];

    const attention = [
        {variant: 'bad', title: __('Iqama expired'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"10\" width=\"38\" height=\"29\" rx=\"4\" fill=\"#e8f0ff\"/><circle cx=\"16\" cy=\"21\" r=\"4\"/><path d=\"M10 32c1-4 3-6 6-6s5 2 6 6\"/><path d=\"m28 20 8 10m0-10-8 10\"/></svg>", description: __('Active employees past their Iqama expiry (from the monthly Muqeem upload).'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['<', today]},
            metric: {key: 'iqama-expired', filters: [ACTIVE, ['Employee', 'custom_iqama_expiry_date', '<', today]]}},
        {variant: 'warn', title: __('Iqama due within 30 days'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"10\" width=\"38\" height=\"29\" rx=\"4\" fill=\"#e8f0ff\"/><circle cx=\"16\" cy=\"21\" r=\"4\"/><path d=\"M10 32c1-4 3-6 6-6s5 2 6 6\"/><circle cx=\"32\" cy=\"25\" r=\"6\"/><path d=\"M32 21v4l3 2\"/></svg>", description: __('Start renewals now.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['between', [today, inDays(30)]]},
            metric: {key: 'iqama-30', filters: [ACTIVE, ['Employee', 'custom_iqama_expiry_date', 'between', [today, inDays(30)]]]}},
        {variant: 'warn', title: __('Onboarding exceptions'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"24\" cy=\"14\" r=\"7\" fill=\"#f8e5d6\"/><path d=\"M8 40c1-10 7-15 16-15s15 5 16 15z\" fill=\"#dcecff\"/><path d=\"M21 31c0-3 6-3 6 0 0 2-3 2-3 4m0 2h.1\"/></svg>", description: __('Employees with a missing login, ledger, mobile, or identity data.'), doctype: ONB, route: ['List', ONB, 'List'], routeOptions: {status: 'Exception'},
            metric: {key: 'onb-exceptions', filters: [[ONB, 'status', '=', 'Exception']]}},
        {variant: 'cyan', title: __('Email replies to review'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"11\" width=\"38\" height=\"27\" rx=\"4\" fill=\"#f1e8fb\"/><path d=\"m7 14 17 9 17-9\"/><path d=\"M21 29c0-4 6-4 6 0 0 2-3 2-3 4m0 2h.1\"/></svg>", description: __('Official emails received on WhatsApp, waiting for HR to apply.'), doctype: ONB, route: ['List', ONB, 'List'], routeOptions: {proposed_email: ['is', 'set']},
            metric: {key: 'email-replies', filters: [[ONB, 'proposed_email', 'is', 'set']]}}
    ];

    const compliance = [
        {variant: 'warn', title: __('Iqama renewals (90 days)'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"10\" width=\"38\" height=\"29\" rx=\"4\" fill=\"#e8f0ff\"/><circle cx=\"16\" cy=\"21\" r=\"4\"/><path d=\"M10 32c1-4 3-6 6-6s5 2 6 6\"/><path d=\"M26 19h11M26 24h11M26 29h7\"/></svg>", description: __('Iqama expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_iqama_expiry_date: ['<=', inDays(90)]}},
        {variant: 'warn', title: __('Passport renewals (90 days)'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"10\" y=\"5\" width=\"29\" height=\"39\" rx=\"4\" fill=\"#e1edf9\"/><circle cx=\"24\" cy=\"25\" r=\"8\"/><path d=\"M16 25h16M24 17c-5 5-5 11 0 16M24 17c5 5 5 11 0 16M17 12h14\"/></svg>", description: __('Passport expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_passport_expiry_date: ['<=', inDays(90)]}},
        {variant: 'warn', title: __('Work permit renewals (90 days)'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 5h24v38H12z\" fill=\"#e6f1fb\"/><path d=\"M17 13h14M17 18h14M17 23h9\"/><circle cx=\"29\" cy=\"33\" r=\"5\"/><path d=\"m26 37-2 5 5-2 5 2-2-5\"/></svg>", description: __('Work permit expiring within 90 days or already expired.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_work_permit_expiry: ['<=', inDays(90)]}},
        {variant: 'blue', title: __('My open tasks'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><path d=\"m17 29 5 5 10-12\"/></svg>", description: __('Open to-dos assigned to you.'), doctype: 'ToDo', route: ['List', 'ToDo', 'List'], routeOptions: {status: 'Open', allocated_to: frappe.session.user}}
    ];

    const quality = [
        {variant: 'slate', title: __('No mobile number'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"13\" y=\"4\" width=\"22\" height=\"40\" rx=\"5\" fill=\"#e4efff\"/><path d=\"M20 9h8M21 39h6\"/><path d=\"M20 25c0-5 8-5 8 0 0 3-4 4-4 6m0 4h.1\"/></svg>", description: __('Cannot receive WhatsApp or appear in attendance.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', cell_number: ['is', 'not set']},
            metric: {key: 'q-mobile', filters: [ACTIVE, ['Employee', 'cell_number', 'is', 'not set']]}},
        {variant: 'slate', title: __('Login email not deliverable'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"11\" width=\"38\" height=\"27\" rx=\"4\" fill=\"#f1e8fb\"/><path d=\"m7 14 17 9 17-9\"/><path d=\"m20 28 8 7m0-7-8 7\"/></svg>", description: __('Login is an internal .local address that cannot receive email.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', user_id: ['like', '%.local']},
            metric: {key: 'q-local', filters: [ACTIVE, ['Employee', 'user_id', 'like', '%.local']]}},
        {variant: 'slate', title: __('Placeholder birth date'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"9\" width=\"36\" height=\"32\" rx=\"4\" fill=\"#fff0dc\"/><path d=\"M6 18h36M15 5v8M33 5v8\"/><path d=\"M20 25c0-5 8-5 8 0 0 3-4 4-4 6m0 4h.1\"/></svg>", description: __('Date of birth is the 1900-01-01 placeholder.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', date_of_birth: '1900-01-01'},
            metric: {key: 'q-dob', filters: [ACTIVE, ['Employee', 'date_of_birth', '=', '1900-01-01']]}},
        {variant: 'slate', title: __('No user linked'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"24\" cy=\"14\" r=\"7\" fill=\"#f8e5d6\"/><path d=\"M8 40c1-10 7-15 16-15s15 5 16 15z\" fill=\"#dcecff\"/><path d=\"m20 31 8 7m0-7-8 7\"/></svg>", description: __('Active employees without a system user.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', user_id: ['is', 'not set']},
            metric: {key: 'q-user', filters: [ACTIVE, ['Employee', 'user_id', 'is', 'not set']]}},
        {variant: 'slate', title: __('No custody ledger'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M30 21c0-4 6-4 6 0 0 2-3 3-3 5m0 4h.1\"/></svg>", description: __('Active employees without a 1322 custody ledger.'), doctype: 'Employee', route: ['List', 'Employee', 'List'], routeOptions: {status: 'Active', custom_custody_account: ['is', 'not set']},
            metric: {key: 'q-ledger', filters: [ACTIVE, ['Employee', 'custom_custody_account', 'is', 'not set']]}}
    ];

    const requests = [
        {variant: 'slate', title: __('Approvals queue'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><path d=\"M15 19h3v3h-3zM22 20h11M15 27h3v3h-3zM22 28h11M15 35h3v3h-3zM22 36h8\"/></svg>", description: __('Leave, expense, and advance requests waiting for a decision.'), doctype: 'Leave Application', report: 'SIG HR Approvals Queue', route: ['query-report', 'SIG HR Approvals Queue']},
        {variant: 'slate', title: __('Leave applications'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"9\" width=\"36\" height=\"32\" rx=\"4\" fill=\"#fff0dc\"/><path d=\"M6 18h36M15 5v8M33 5v8\"/><path d=\"M17 21h14M17 26h14M17 31h11\"/></svg>", description: __('Not in use yet: leave policies are configured in a later HR stage.'), doctype: 'Leave Application', route: ['List', 'Leave Application', 'List']},
        {variant: 'slate', title: __('Expense claims'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M24 20v17M28 23c-2-3-8-3-8 1 0 4 8 2 8 6s-6 4-8 1\"/></svg>", description: __('Not in use yet.'), doctype: 'Expense Claim', route: ['List', 'Expense Claim', 'List']},
        {variant: 'slate', title: __('Employee advances'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 30h10l6 3h13c3 0 3 4 0 4H23M5 41h14l6 3 15-8c4-2 2-6-1-5l-6 2\"/><circle cx=\"25\" cy=\"15\" r=\"9\" fill=\"#fff0d4\"/><path d=\"M25 10v10m3-8c-2-2-6-1-6 1 0 3 6 1 6 4s-4 3-6 1\"/></svg>", description: __('Not in use yet.'), doctype: 'Employee Advance', route: ['List', 'Employee Advance', 'List']}
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
        const icon = item.iconSvg ? `<span class="sig-hr-icon" aria-hidden="true">${item.iconSvg}</span>` : '';
        const detail = item.description ? `<span class="sig-hr-detail">${frappe.utils.escape_html(item.description)}</span>` : '';
        const metric = item.metric ? `<span class="sig-hr-metric" data-metric-key="${frappe.utils.escape_html(item.metric.key)}">—</span>` : '';
        return `<button type="button" class="sig-hr-card sig-hr-card--${item.variant || 'slate'} ${compact ? 'sig-hr-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route || null))}"
                    data-route-options="${frappe.utils.escape_html(JSON.stringify(item.routeOptions || null))}"
                    data-action="${frappe.utils.escape_html(item.action || '')}">
            <span class="sig-hr-card-top">${icon}</span>
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
        {variant: 'blue', title: __('Request official emails'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"11\" width=\"38\" height=\"27\" rx=\"4\" fill=\"#f1e8fb\"/><path d=\"m7 14 17 9 17-9\"/><path d=\"M24 26v10m-5-5h10\"/></svg>", description: __('Ask employees on .local logins, by WhatsApp, to reply with their official email. Replies are collected for HR review; nothing is changed automatically.'), roleAny: ['HR Manager', 'System Manager'], action: 'email-request'}
    ];

    root.html(`<header class="sig-hr-header">
            <div><div class="sig-hr-eyebrow">${__('Human Resources')}</div>
                <h1>${__('HR workbench')}</h1>
                <p>${__('Daily people work, compliance, and the link between employees and finance.')}</p></div>
            <span class="sig-hr-header-mark" aria-hidden="true"><i class="fa fa-users"></i></span>
        </header>
        ${section(__('Daily people work'), __('Open the employee records and the onboarding checks.'), daily, false)}
        ${section(__('Attendance'), __('Review daily attendance and employee history.'), attendance)}
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
