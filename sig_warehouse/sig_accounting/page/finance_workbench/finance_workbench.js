// Role-aware navigation only. ERPNext documents and reports remain authoritative.
frappe.pages['finance-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('SIG Accounting'),
        single_column: true
    });

    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const direction = language.startsWith('ar') ? 'rtl' : 'ltr';
    const root = $('<main class="sig-finance-home"></main>')
        .attr('dir', direction)
        .attr('lang', language)
        .appendTo(page.main);

    const daily = [
        {title: __('Payment entries'), description: __('Review receipts, supplier payments, and their invoice allocations.'), icon: 'exchange', doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List']},
        {title: __('Sales invoices'), description: __('Review customer invoices and collection status.'), icon: 'file-text', doctype: 'Sales Invoice', route: ['List', 'Sales Invoice', 'List']},
        {title: __('Purchase invoices'), description: __('Review supplier invoices after the purchasing and receipt handoff.'), icon: 'file-text-o', doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List']},
        {title: __('Journal entries'), description: __('Review controlled accounting entries; draft first and submit with authority.'), icon: 'book', doctype: 'Journal Entry', route: ['List', 'Journal Entry', 'List']}
    ];

    const control = [
        {title: __('General Ledger'), description: __('Trace posted balances to their source vouchers.'), doctype: 'GL Entry', report: 'General Ledger', route: ['query-report', 'General Ledger']},
        {title: __('Trial Balance'), description: __('Check debit and credit balances for the selected period.'), doctype: 'GL Entry', report: 'Trial Balance', route: ['query-report', 'Trial Balance']},
        {title: __('Profit and Loss'), description: __('Review income and expense performance.'), doctype: 'GL Entry', report: 'Profit and Loss Statement', route: ['query-report', 'Profit and Loss Statement']},
        {title: __('Balance Sheet'), description: __('Review assets, liabilities, and equity.'), doctype: 'GL Entry', report: 'Balance Sheet', route: ['query-report', 'Balance Sheet']}
    ];

    const collections = [
        {title: __('Sales Register'), doctype: 'Sales Invoice', report: 'Sales Register', route: ['query-report', 'Sales Register']},
        {title: __('Sales Invoice Trends'), doctype: 'Sales Invoice', report: 'Sales Invoice Trends', route: ['query-report', 'Sales Invoice Trends']},
        {title: __('Accounts Receivable'), doctype: 'Sales Invoice', report: 'Accounts Receivable', route: ['query-report', 'Accounts Receivable']}
    ];

    const payables = [
        {title: __('Purchase Register'), doctype: 'Purchase Invoice', report: 'Purchase Register', route: ['query-report', 'Purchase Register']},
        {title: __('Purchase Invoice Trends'), doctype: 'Purchase Invoice', report: 'Purchase Invoice Trends', route: ['query-report', 'Purchase Invoice Trends']},
        {title: __('Accounts Payable'), doctype: 'Purchase Invoice', report: 'Accounts Payable', route: ['query-report', 'Accounts Payable']}
    ];

    const tawalAndOperations = [
        {
            title: __('Tawal customer invoices'),
            description: __('Review ERP invoices against Tawal portal, receipt, and retention evidence; the ERP outstanding total is not a confirmed collectible balance.'),
            doctype: 'Sales Invoice',
            route: ['List', 'Sales Invoice', 'List'],
            routeOptions: {customer: 'Telecommunications Towers Company / Tawal'}
        },
        {
            title: __('Tawal receipts posted this month'),
            description: __('Count of submitted Tawal receipts; open the filtered list to review invoice allocations.'),
            doctype: 'Payment Entry',
            route: ['List', 'Payment Entry', 'List'],
            routeOptions: {
                party_type: 'Customer',
                party: 'Telecommunications Towers Company / Tawal',
                payment_type: 'Receive',
                docstatus: 1,
                posting_date: ['Timespan', 'this month']
            },
            metric: {
                key: 'tawal-posted-receipts', function: 'Count',
                filters: [
                    ['Payment Entry', 'party_type', '=', 'Customer'],
                    ['Payment Entry', 'party', '=', 'Telecommunications Towers Company / Tawal'],
                    ['Payment Entry', 'payment_type', '=', 'Receive'],
                    ['Payment Entry', 'docstatus', '=', 1],
                    ['Payment Entry', 'posting_date', 'Timespan', 'this month']
                ]
            }
        },
        {
            title: __('Tawal draft payments'),
            description: __('Draft receipts awaiting finance review.'),
            doctype: 'Payment Entry',
            route: ['List', 'Payment Entry', 'List'],
            routeOptions: {party_type: 'Customer', party: 'Telecommunications Towers Company / Tawal', docstatus: 0},
            metric: {
                key: 'tawal-draft-payments', function: 'Count',
                filters: [
                    ['Payment Entry', 'party_type', '=', 'Customer'],
                    ['Payment Entry', 'party', '=', 'Telecommunications Towers Company / Tawal'],
                    ['Payment Entry', 'docstatus', '=', 0]
                ]
            }
        },
        {
            title: __('SNB draft payments'),
            description: __('Draft payment entries carrying an SNB source key.'),
            doctype: 'Payment Entry',
            route: ['List', 'Payment Entry', 'List'],
            routeOptions: {custom_snb_idempotency_key: ['is', 'set'], docstatus: 0},
            metric: {
                key: 'snb-draft-payments', function: 'Count',
                filters: [
                    ['Payment Entry', 'custom_snb_idempotency_key', 'is', 'set'],
                    ['Payment Entry', 'docstatus', '=', 0]
                ]
            }
        },
        {
            title: __('SNB payments submitted this month'),
            description: __('Submitted SNB-linked payments; this is not a bank-reconciliation count.'),
            doctype: 'Payment Entry',
            route: ['List', 'Payment Entry', 'List'],
            routeOptions: {
                custom_snb_idempotency_key: ['is', 'set'],
                docstatus: 1,
                posting_date: ['Timespan', 'this month']
            },
            metric: {
                key: 'snb-submitted-month', function: 'Count',
                filters: [
                    ['Payment Entry', 'custom_snb_idempotency_key', 'is', 'set'],
                    ['Payment Entry', 'docstatus', '=', 1],
                    ['Payment Entry', 'posting_date', 'Timespan', 'this month']
                ]
            }
        },
        {
            title: __('Open supplier invoices'),
            description: __('Submitted supplier invoices with an outstanding balance.'),
            doctype: 'Purchase Invoice',
            route: ['List', 'Purchase Invoice', 'List'],
            routeOptions: {docstatus: 1, outstanding_amount: ['>', 0]},
            metric: {
                key: 'open-supplier-invoices', function: 'Count',
                filters: [
                    ['Purchase Invoice', 'docstatus', '=', 1],
                    ['Purchase Invoice', 'outstanding_amount', '>', 0]
                ]
            }
        },
        {
            title: __('Unsubmitted journal entries'),
            description: __('Review draft journals before an authorized accountant submits them.'),
            doctype: 'Journal Entry',
            route: ['List', 'Journal Entry', 'List'],
            routeOptions: {docstatus: 0},
            metric: {
                key: 'unsubmitted-journals', function: 'Count',
                filters: [['Journal Entry', 'docstatus', '=', 0]]
            }
        }
    ];

    const review = [
        {title: __('Draft payments queue'), description: __('Review draft payment entries before approval or posting.'), doctype: 'Payment Entry', report: 'SIG Finance Draft Payments Queue', route: ['query-report', 'SIG Finance Draft Payments Queue']},
        {title: __('Bank transactions'), description: __('Review statement evidence before matching or reconciliation.'), doctype: 'Bank Transaction', route: ['List', 'Bank Transaction', 'List']}
    ];

    const specialist = [
        {title: __('SIG Petty Cash'), description: __('Open the separate evidence, clearance, and finance handoff workspace.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager', 'SIG Finance Viewer', 'SIG PC Clearance'], route: ['Workspaces', 'SIG Petty Cash']},
        {title: __('ZATCA Integrations'), description: __('Review tax-compliance evidence linked to the source invoice.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], route: ['Workspaces', 'ZATCA Integrations']}
    ];

    const references = [
        {title: __('Chart of accounts'), description: __('Reference the account hierarchy; setup remains a controlled finance task.'), doctype: 'Account', route: ['List', 'Account', 'List']},
        {title: __('Cost centers'), description: __('Reference financial responsibility and reporting dimensions.'), doctype: 'Cost Center', route: ['List', 'Cost Center', 'List']}
    ];

    function canOpen(item) {
        if (item.roleAny && !item.roleAny.some((role) => frappe.user.has_role(role))) return false;
        if (!item.doctype) return true;
        if (!frappe.model.can_read(item.doctype)) return false;
        if (!item.report) return true;
        const reportGrants = frappe.boot?.user?.can_get_report;
        if (Array.isArray(reportGrants) && !reportGrants.includes(item.doctype)) return false;
        const reports = frappe.boot?.allowed_reports;
        if (Array.isArray(reports)) {
            return reports.some((report) => (typeof report === 'string' ? report : report.name) === item.report);
        }
        if (reports && typeof reports === 'object') return item.report in reports;
        return false;
    }

    function card(item, compact = false) {
        const icon = item.icon
            ? `<span class="sig-finance-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>`
            : '';
        const detail = item.description
            ? `<span class="sig-finance-detail">${frappe.utils.escape_html(item.description)}</span>`
            : '';
        return `<button type="button" class="sig-finance-card ${compact ? 'sig-finance-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}"
                    data-route-options="${frappe.utils.escape_html(JSON.stringify(item.routeOptions || null))}">
            <span class="sig-finance-card-top">${icon}<i class="fa fa-external-link sig-finance-open" aria-hidden="true"></i></span>
            <span class="sig-finance-card-title">${frappe.utils.escape_html(item.title)}</span>
            ${item.metric ? `<span class="sig-finance-metric" data-metric-key="${frappe.utils.escape_html(item.metric.key)}">—</span>` : ''}${detail}
        </button>`;
    }

    function section(title, description, items, compact = true) {
        const available = items.filter(canOpen);
        if (!available.length) return '';
        return `<section class="sig-finance-section">
            <div class="sig-finance-section-heading"><h2>${frappe.utils.escape_html(title)}</h2>
                <p>${frappe.utils.escape_html(description)}</p></div>
            <div class="sig-finance-grid ${compact ? 'sig-finance-grid-compact' : ''}">${available.map((item) => card(item, compact)).join('')}</div>
        </section>`;
    }

    root.html(`<header class="sig-finance-header">
            <div><div class="sig-finance-eyebrow">${__('Accounts')}</div>
                <h1>${__('Finance workbench')}</h1>
                <p>${__('Daily finance work, backed by ERPNext records and accounting controls.')}</p>
            </div><span class="sig-finance-header-mark" aria-hidden="true"><i class="fa fa-line-chart"></i></span>
        </header>
        ${section(__('Daily finance work'), __('Open the source documents used for customer, supplier, payment, and journal work.'), daily, false)}
        ${section(__('Financial control'), __('Core statements and ledger traceability. Each report keeps its own filters.'), control)}
        ${section(__('Sales and collections'), __('Customer billing and receivable review, including the Tawal customer lane.'), collections)}
        ${section(__('Purchasing and payables'), __('Supplier invoice review after the Purchase Order and receipt handoff.'), payables)}
        ${section(__('Operational follow-up and positions'), __('Tawal customer review, payment processing, SNB-linked entries, supplier exposure, and draft journals from SIG Accounting.'), tawalAndOperations)}
        ${section(__('Reconciliation and evidence'), __('Review source evidence before matching, approval, or posting.'), review)}
        ${section(__('Specialist finance lanes'), __('Separate controlled workspaces for petty cash and tax-compliance evidence.'), specialist)}
        ${section(__('Reference and setup'), __('Use less-frequent finance masters and reporting references.'), references)}
        <p class="sig-finance-footnote">${__('This page is navigation only. It does not create or post accounting entries; document, workflow, and report permissions remain enforced by ERPNext.')}</p>`);

    root.find('.sig-finance-card').on('click', function () {
        let route;
        let routeOptions;
        try { route = JSON.parse($(this).attr('data-route')); }
        catch (e) { return; }
        try { routeOptions = JSON.parse($(this).attr('data-route-options') || 'null'); }
        catch (e) { routeOptions = null; }
        if (routeOptions) frappe.route_options = routeOptions;
        if (Array.isArray(route) && route.length) frappe.set_route(...route);
    });

    tawalAndOperations.forEach((item) => {
        if (!item.metric || !canOpen(item)) return;
        frappe.call({
            method: 'frappe.desk.doctype.number_card.number_card.get_result',
            args: {
                doc: JSON.stringify({
                    function: item.metric.function,
                    document_type: item.doctype,
                    aggregate_function_based_on: item.metric.field
                }),
                filters: JSON.stringify(item.metric.filters)
            }
        }).then((response) => {
            const value = Number(response.message);
            const formatted = Number.isFinite(value)
                ? new Intl.NumberFormat(language.replace('_', '-'), {maximumFractionDigits: 0}).format(value)
                : '—';
            root.find(`[data-metric-key="${item.metric.key}"]`).text(formatted);
        }).catch(() => {
            root.find(`[data-metric-key="${item.metric.key}"]`).text('—');
        });
    });
};
