// Role-aware navigation only. ERPNext documents and reports remain authoritative.
frappe.pages['finance-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '',
        single_column: true
    });
    $(wrapper).find('.page-head').hide();

    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const direction = language.startsWith('ar') ? 'rtl' : 'ltr';
    const root = $('<main class="sig-finance-home"></main>')
        .attr('dir', direction)
        .attr('lang', language)
        .appendTo(page.main);

    const daily = [
        {variant: 'blue', title: __('Payment entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"10\" width=\"38\" height=\"28\" rx=\"5\" fill=\"#def3eb\"/><path d=\"M5 19h38M11 31h10\"/></svg>", description: __('Review receipts, supplier payments, and their invoice allocations.'), doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List']},
        {variant: 'blue', title: __('Sales invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M17 19h13M17 24h10M19 34h13m-4-4 4 4-4 4\"/></svg>", description: __('Review customer invoices and collection status.'), doctype: 'Sales Invoice', route: ['List', 'Sales Invoice', 'List']},
        {variant: 'blue', title: __('Purchase invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M17 19h13M17 24h10M32 34H19m4-4-4 4 4 4\"/></svg>", description: __('Review supplier invoices after the purchasing and receipt handoff.'), doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List']},
        {variant: 'blue', title: __('Journal entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M29 17h8M29 22h8M29 34l7-8 2 2-7 8-3 1z\"/></svg>", description: __('Review controlled accounting entries; draft first and submit with authority.'), doctype: 'Journal Entry', route: ['List', 'Journal Entry', 'List']},
        {variant: 'blue', title: __('Customer addresses'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 36c0-8 7-8 14-8s14 0 14-10\"/><circle cx=\"7\" cy=\"37\" r=\"4\" fill=\"#e6f1ff\"/><path d=\"M35 6c-6 0-9 5-9 9 0 7 9 14 9 14s9-7 9-14c0-4-3-9-9-9z\" fill=\"#e2f4ed\"/><circle cx=\"35\" cy=\"15\" r=\"2\"/></svg>", description: __('Find or add a customer address. Open it from the customer, or add the customer in Links.'), doctype: 'Address', route: ['List', 'Address', 'List']}
    ];

    const control = [
        {variant: 'navy', title: __('General Ledger'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M29 17h9M29 22h9M29 27h7\"/></svg>", description: __('Trace posted balances to their source vouchers.'), doctype: 'GL Entry', report: 'General Ledger', route: ['query-report', 'General Ledger']},
        {variant: 'navy', title: __('Trial Balance'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 6v34M9 41h30M11 14h26M13 14 6 27h14zM35 14l-7 13h14z\" fill=\"#fff3d9\"/><path d=\"M5 27c2 6 13 6 16 0M27 27c2 6 13 6 16 0\"/></svg>", description: __('Check debit and credit balances for the selected period.'), doctype: 'GL Entry', report: 'Trial Balance', route: ['query-report', 'Trial Balance']},
        {variant: 'navy', title: __('Profit and Loss'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"6\" width=\"36\" height=\"36\" rx=\"5\" fill=\"#e6f5ed\"/><path d=\"M12 35V23h5v12M22 35V17h5v18M32 35V11h5v24\"/></svg>", description: __('Review income and expense performance.'), doctype: 'GL Entry', report: 'Profit and Loss Statement', route: ['query-report', 'Profit and Loss Statement']},
        {variant: 'navy', title: __('Balance Sheet'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M28 18h4v4h-4zM35 18h4v4h-4zM28 26h4v4h-4zM35 26h4v4h-4z\"/></svg>", description: __('Review assets, liabilities, and equity.'), doctype: 'GL Entry', report: 'Balance Sheet', route: ['query-report', 'Balance Sheet']}
    ];

    const collections = [
        {variant: 'slate', title: __('Sales Register'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M28 19h10M28 24h8M29 33h9m-3-3 3 3-3 3\"/></svg>", doctype: 'Sales Invoice', report: 'Sales Register', route: ['query-report', 'Sales Register']},
        {variant: 'slate', title: __('Sales Invoice Trends'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"6\" width=\"36\" height=\"36\" rx=\"5\" fill=\"#e6f5ed\"/><path d=\"M12 35V14M12 35h24\"/><path d=\"m15 30 7-7 5 3 9-11m-5 0h5v5\"/></svg>", doctype: 'Sales Invoice', report: 'Sales Invoice Trends', route: ['query-report', 'Sales Invoice Trends']},
        {variant: 'slate', title: __('Accounts Receivable'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 29h10l6 3h13c3 0 3 4 0 4H23M5 40h14l6 3 15-8c4-2 2-6-1-5l-6 2M12 15l7-6h11l6 6-12 9z\" fill=\"#e5f2eb\"/></svg>", doctype: 'Sales Invoice', report: 'Accounts Receivable', route: ['query-report', 'Accounts Receivable']}
    ];

    const payables = [
        {variant: 'slate', title: __('Purchase Register'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M28 19h10M28 24h8M38 33h-9m3-3-3 3 3 3\"/></svg>", doctype: 'Purchase Invoice', report: 'Purchase Register', route: ['query-report', 'Purchase Register']},
        {variant: 'slate', title: __('Purchase Invoice Trends'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"6\" width=\"36\" height=\"36\" rx=\"5\" fill=\"#e6f5ed\"/><path d=\"M12 35V14M12 35h24\"/><path d=\"m15 17 7 7 5-3 9 11m-5 0h5v-5\"/></svg>", doctype: 'Purchase Invoice', report: 'Purchase Invoice Trends', route: ['query-report', 'Purchase Invoice Trends']},
        {variant: 'slate', title: __('Accounts Payable'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M6 12h31a4 4 0 0 1 4 4v23H6a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3z\" fill=\"#f8e8d7\"/><path d=\"M29 22h12v9H29a4 4 0 0 1 0-9zM32 26h1\"/></svg>", doctype: 'Purchase Invoice', report: 'Accounts Payable', route: ['query-report', 'Accounts Payable']}
    ];

    const purchasingDocuments = [
        {variant: 'blue', title: __('Purchase Orders'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 8h5l4 22h23l5-16H12\" fill=\"#e6f5ee\"/><circle cx=\"18\" cy=\"37\" r=\"3\"/><circle cx=\"34\" cy=\"37\" r=\"3\"/></svg>", description: __('Open ERPNext purchase orders for finance and purchasing review.'), doctype: 'Purchase Order', route: ['List', 'Purchase Order', 'List']},
        {variant: 'blue', title: __('Quotations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M20 25c0-5 8-5 8 0 0 3-4 4-4 6m0 4h.1\"/></svg>", description: __('Review quotation records in ERPNext.'), doctype: 'Quotation', route: ['List', 'Quotation', 'List']}
    ];

    const tawalAndOperations = [
        {variant: 'navy', title: __('Bank movement router'), iconSvg: '<svg viewBox="0 0 48 48" fill="none" stroke="#386c91" stroke-width="1.7"><path d="M5 16 24 7l19 9M8 20h32M9 38h30M12 20v16M24 20v16M36 20v16"/><path d="m17 28 4 4 9-10"/></svg>', description: __('Review SNB and Alinma bank evidence and save accountant routing decisions.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], doctype: 'SNB Movement Review', route: ['snb-movement-router']},
        {
            variant: 'navy',
            title: __('Tawal customer invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M17 21h14M17 26h14M17 31h11\"/></svg>",
            description: __('Review ERP invoices against Tawal portal, receipt, and retention evidence; the ERP outstanding total is not a confirmed collectible balance.'),
            doctype: 'Sales Invoice',
            route: ['List', 'Sales Invoice', 'List'],
            routeOptions: {customer: 'Telecommunications Towers Company / Tawal'}
        },
        {
            variant: 'cyan',
            title: __('Tawal receipts posted this month'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"m17 29 5 5 10-12\"/></svg>",
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
            variant: 'warn',
            title: __('Tawal draft payments'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><circle cx=\"24\" cy=\"29\" r=\"8\"/><path d=\"M24 24v5l4 2\"/></svg>",
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
            variant: 'warn',
            title: __('SNB draft payments'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m4 16 20-10 20 10zM7 39h34M9 19v16M39 19v16\" fill=\"#e7edf9\"/><circle cx=\"24\" cy=\"27\" r=\"7\"/><path d=\"M24 23v4l3 2\"/></svg>",
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
            variant: 'cyan',
            title: __('SNB payments submitted this month'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m4 16 20-10 20 10zM7 39h34M9 19v16M39 19v16\" fill=\"#e7edf9\"/><path d=\"m17 27 5 5 10-11\"/></svg>",
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
            variant: 'navy',
            title: __('Open supplier invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M24 20v17M28 23c-2-3-8-3-8 1 0 4 8 2 8 6s-6 4-8 1\"/></svg>",
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
            variant: 'warn',
            title: __('Unsubmitted journal entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><circle cx=\"33\" cy=\"26\" r=\"6\"/><path d=\"M33 22v4l3 2\"/></svg>",
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
        {variant: 'slate', title: __('Draft payments queue'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><circle cx=\"24\" cy=\"29\" r=\"8\"/><path d=\"M24 24v5l4 2\"/></svg>", description: __('Review draft payment entries before approval or posting.'), doctype: 'Payment Entry', report: 'SIG Finance Draft Payments Queue', route: ['query-report', 'SIG Finance Draft Payments Queue']},
        {variant: 'slate', title: __('Bank transactions'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m4 17 20-10 20 10zM7 39h34M11 20v16M19 20v16M29 20v16M37 20v16\" fill=\"#e7edf9\"/></svg>", description: __('Review statement evidence before matching or reconciliation.'), doctype: 'Bank Transaction', route: ['List', 'Bank Transaction', 'List']}
    ];

    const specialist = [
        {variant: 'warn', title: __('Petty cash'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M6 12h31a4 4 0 0 1 4 4v23H6a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3z\" fill=\"#f8e8d7\"/><path d=\"M29 22h12v9H29a4 4 0 0 1 0-9zM32 26h1\"/></svg>", description: __('Review receipts, create draft clearance journals, and follow Finance submission.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], doctype: 'SIG PC Transaction', route: ['pc-invoice-review'],
            metric: {key: 'pc-pending-review', function: 'Count', filters: [['SIG PC Transaction', 'closure_status', 'in', ['Draft', 'Needs Review']]]}},
        {variant: 'navy', title: __('ZATCA Integrations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 5 40 11v12c0 9-7 15-16 20C15 38 8 32 8 23V11z\" fill=\"#e1f4ed\"/><path d=\"m16 24 5 5 11-12\"/></svg>", description: __('Review tax-compliance evidence linked to the source invoice.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], route: ['Workspaces', 'ZATCA Integrations']}
    ];

    const references = [
        {variant: 'slate', title: __('Chart of accounts'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"17\" y=\"4\" width=\"14\" height=\"10\" rx=\"2\" fill=\"#e1f0fa\"/><rect x=\"3\" y=\"32\" width=\"14\" height=\"10\" rx=\"2\" fill=\"#e1f0fa\"/><rect x=\"31\" y=\"32\" width=\"14\" height=\"10\" rx=\"2\" fill=\"#e1f0fa\"/><path d=\"M24 14v9M10 32v-9h28v9\"/></svg>", description: __('Reference the account hierarchy; setup remains a controlled finance task.'), doctype: 'Account', route: ['List', 'Account', 'List']},
        {variant: 'slate', title: __('Cost centers'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M6 18 24 7l18 11v24H6z\" fill=\"#e1f2ee\"/><path d=\"M12 42V21h24v21M17 27h14M17 33h14\"/></svg>", description: __('Reference financial responsibility and reporting dimensions.'), doctype: 'Cost Center', route: ['List', 'Cost Center', 'List']}
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
        const icon = item.iconSvg
            ? `<span class="sig-finance-icon" aria-hidden="true">${item.iconSvg}</span>`
            : '';
        const detail = item.description
            ? `<span class="sig-finance-detail">${frappe.utils.escape_html(item.description)}</span>`
            : '';
        return `<button type="button" class="sig-finance-card sig-finance-card--${item.variant || 'slate'} ${compact ? 'sig-finance-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}"
                    data-route-options="${frappe.utils.escape_html(JSON.stringify(item.routeOptions || null))}">
            <span class="sig-finance-card-top">${icon}</span>
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
        ${section(__('Purchasing documents'), __('Open purchase orders and quotations.'), purchasingDocuments, false)}
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

    // Cards with a live count: the Tawal/SNB positions and the petty cash review queue.
    [...tawalAndOperations, ...specialist].forEach((item) => {
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
