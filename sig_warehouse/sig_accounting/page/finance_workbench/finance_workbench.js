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
        {variant: 'blue', title: __('Payment entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e3ecf6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"20\" height=\"14\" x=\"2\" y=\"5\" rx=\"2\" /><line x1=\"2\" x2=\"22\" y1=\"10\" y2=\"10\" /></svg></svg>", description: __('Review receipts, supplier payments, and their invoice allocations.'), doctype: 'Payment Entry', route: ['List', 'Payment Entry', 'List']},
        {variant: 'blue', title: __('Sales invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e1efe7\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M14 2v4a2 2 0 0 0 2 2h4\" /><path d=\"M10 9H8\" /><path d=\"M16 13H8\" /><path d=\"M16 17H8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M7 7h10v10\" /><path d=\"M7 17 17 7\" /></svg></svg>", description: __('Review customer invoices and collection status.'), doctype: 'Sales Invoice', route: ['List', 'Sales Invoice', 'List']},
        {variant: 'blue', title: __('Purchase invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M14 2v4a2 2 0 0 0 2 2h4\" /><path d=\"M10 9H8\" /><path d=\"M16 13H8\" /><path d=\"M16 17H8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M17 7 7 17\" /><path d=\"M17 17H7V7\" /></svg></svg>", description: __('Review supplier invoices after the purchasing and receipt handoff.'), doctype: 'Purchase Invoice', route: ['List', 'Purchase Invoice', 'List']},
        {variant: 'blue', title: __('Journal entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4\" /><path d=\"M2 6h4\" /><path d=\"M2 10h4\" /><path d=\"M2 14h4\" /><path d=\"M2 18h4\" /><path d=\"M21.378 5.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z\" /></svg></svg>", description: __('Review controlled accounting entries; draft first and submit with authority.'), doctype: 'Journal Entry', route: ['List', 'Journal Entry', 'List']},
        {variant: 'blue', title: __('Customer addresses'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#dcecec\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0\" /><circle cx=\"12\" cy=\"10\" r=\"3\" /></svg></svg>", description: __('Find or add a customer address. Open it from the customer, or add the customer in Links.'), doctype: 'Address', route: ['List', 'Address', 'List']}
    ];

    const control = [
        {variant: 'navy', title: __('General Ledger'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M12 7v14\" /><path d=\"M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z\" /></svg></svg>", description: __('Trace posted balances to their source vouchers.'), doctype: 'GL Entry', report: 'General Ledger', route: ['query-report', 'General Ledger']},
        {variant: 'navy', title: __('Trial Balance'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z\" /><path d=\"m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z\" /><path d=\"M7 21h10\" /><path d=\"M12 3v18\" /><path d=\"M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2\" /></svg></svg>", description: __('Check debit and credit balances for the selected period.'), doctype: 'GL Entry', report: 'Trial Balance', route: ['query-report', 'Trial Balance']},
        {variant: 'navy', title: __('Profit and Loss'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M3 3v16a2 2 0 0 0 2 2h16\" /><path d=\"M18 17V9\" /><path d=\"M13 17V5\" /><path d=\"M8 17v-3\" /></svg></svg>", description: __('Review income and expense performance.'), doctype: 'GL Entry', report: 'Profit and Loss Statement', route: ['query-report', 'Profit and Loss Statement']},
        {variant: 'navy', title: __('Balance Sheet'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18\" /></svg></svg>", description: __('Review assets, liabilities, and equity.'), doctype: 'GL Entry', report: 'Balance Sheet', route: ['query-report', 'Balance Sheet']}
    ];

    const collections = [
        {variant: 'slate', title: __('Sales Register'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e1efe7\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"8\" height=\"4\" x=\"8\" y=\"2\" rx=\"1\" ry=\"1\" /><path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\" /><path d=\"M12 11h4\" /><path d=\"M12 16h4\" /><path d=\"M8 11h.01\" /><path d=\"M8 16h.01\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M7 7h10v10\" /><path d=\"M7 17 17 7\" /></svg></svg>", doctype: 'Sales Invoice', report: 'Sales Register', route: ['query-report', 'Sales Register']},
        {variant: 'slate', title: __('Sales Invoice Trends'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\" /><polyline points=\"16 7 22 7 22 13\" /></svg></svg>", doctype: 'Sales Invoice', report: 'Sales Invoice Trends', route: ['query-report', 'Sales Invoice Trends']},
        {variant: 'slate', title: __('Accounts Receivable'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17\" /><path d=\"m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9\" /><path d=\"m2 16 6 6\" /><circle cx=\"16\" cy=\"9\" r=\"2.9\" /><circle cx=\"6\" cy=\"5\" r=\"3\" /></svg></svg>", doctype: 'Sales Invoice', report: 'Accounts Receivable', route: ['query-report', 'Accounts Receivable']}
    ];

    const payables = [
        {variant: 'slate', title: __('Purchase Register'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"8\" height=\"4\" x=\"8\" y=\"2\" rx=\"1\" ry=\"1\" /><path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\" /><path d=\"M12 11h4\" /><path d=\"M12 16h4\" /><path d=\"M8 11h.01\" /><path d=\"M8 16h.01\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M17 7 7 17\" /><path d=\"M17 17H7V7\" /></svg></svg>", doctype: 'Purchase Invoice', report: 'Purchase Register', route: ['query-report', 'Purchase Register']},
        {variant: 'slate', title: __('Purchase Invoice Trends'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><polyline points=\"22 17 13.5 8.5 8.5 13.5 2 7\" /><polyline points=\"16 17 22 17 22 11\" /></svg></svg>", doctype: 'Purchase Invoice', report: 'Purchase Invoice Trends', route: ['query-report', 'Purchase Invoice Trends']},
        {variant: 'slate', title: __('Accounts Payable'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1\" /><path d=\"M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4\" /></svg></svg>", doctype: 'Purchase Invoice', report: 'Accounts Payable', route: ['query-report', 'Accounts Payable']}
    ];

    const purchasingDocuments = [
        {variant: 'blue', title: __('Purchase Orders'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><circle cx=\"8\" cy=\"21\" r=\"1\" /><circle cx=\"19\" cy=\"21\" r=\"1\" /><path d=\"M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12\" /></svg></svg>", description: __('Open ERPNext purchase orders for finance and purchasing review.'), doctype: 'Purchase Order', route: ['List', 'Purchase Order', 'List']},
        {variant: 'blue', title: __('Quotations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e1efe7\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M14 2v4a2 2 0 0 0 2 2h4\" /><path d=\"M10 9H8\" /><path d=\"M16 13H8\" /><path d=\"M16 17H8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8\" /><path d=\"M12 18V6\" /></svg></svg>", description: __('Review quotation records in ERPNext.'), doctype: 'Quotation', route: ['List', 'Quotation', 'List']}
    ];

    const tawalAndOperations = [
        {variant: 'navy', title: __('Bank movement router'), iconSvg: '<svg viewBox="0 0 48 48" fill="none"><svg x="3" y="3" width="36" height="36" viewBox="0 0 24 24" fill="#e3ecf6" stroke="#386c91" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" color="#386c91"><line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/></svg><circle cx="36" cy="36" r="9" fill="#386c91" stroke="#fff" stroke-width="2"/><svg x="30.5" y="30.5" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" color="#fff"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg></svg>', description: __('Review SNB and Alinma bank evidence and save accountant routing decisions.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], doctype: 'SNB Movement Review', route: ['snb-movement-router']},
        {
            variant: 'navy',
            title: __('Tawal customer invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><rect x=\"3\" y=\"3\" width=\"34\" height=\"34\" rx=\"8\" fill=\"#2b5a82\"/><text x=\"20\" y=\"20.5\" text-anchor=\"middle\" dominant-baseline=\"central\" font-family=\"Segoe UI,Arial,sans-serif\" font-weight=\"700\" font-size=\"24\" fill=\"#fff\">T</text><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#386c91\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M10 13h4M10 17h4\" /></svg></svg>",
            description: __('Review ERP invoices against Tawal portal, receipt, and retention evidence; the ERP outstanding total is not a confirmed collectible balance.'),
            doctype: 'Sales Invoice',
            route: ['List', 'Sales Invoice', 'List'],
            routeOptions: {customer: 'Telecommunications Towers Company / Tawal'}
        },
        {
            variant: 'cyan',
            title: __('Tawal receipts posted this month'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><rect x=\"3\" y=\"3\" width=\"34\" height=\"34\" rx=\"8\" fill=\"#2b5a82\"/><text x=\"20\" y=\"20.5\" text-anchor=\"middle\" dominant-baseline=\"central\" font-family=\"Segoe UI,Arial,sans-serif\" font-weight=\"700\" font-size=\"24\" fill=\"#fff\">T</text><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M20 6 9 17l-5-5\" /></svg></svg>",
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
            title: __('Tawal draft payments'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><rect x=\"3\" y=\"3\" width=\"34\" height=\"34\" rx=\"8\" fill=\"#2b5a82\"/><text x=\"20\" y=\"20.5\" text-anchor=\"middle\" dominant-baseline=\"central\" font-family=\"Segoe UI,Arial,sans-serif\" font-weight=\"700\" font-size=\"24\" fill=\"#fff\">T</text><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z\" /><path d=\"m15 5 4 4\" /></svg></svg>",
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
            title: __('SNB draft payments'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><rect x=\"3\" y=\"3\" width=\"34\" height=\"34\" rx=\"8\" fill=\"#4a8570\"/><text x=\"20\" y=\"20.5\" text-anchor=\"middle\" dominant-baseline=\"central\" font-family=\"Segoe UI,Arial,sans-serif\" font-weight=\"700\" font-size=\"12.5\" fill=\"#fff\">SNB</text><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z\" /><path d=\"m15 5 4 4\" /></svg></svg>",
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
            title: __('SNB payments submitted this month'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><rect x=\"3\" y=\"3\" width=\"34\" height=\"34\" rx=\"8\" fill=\"#4a8570\"/><text x=\"20\" y=\"20.5\" text-anchor=\"middle\" dominant-baseline=\"central\" font-family=\"Segoe UI,Arial,sans-serif\" font-weight=\"700\" font-size=\"12.5\" fill=\"#fff\">SNB</text><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M20 6 9 17l-5-5\" /></svg></svg>",
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
            title: __('Open supplier invoices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M14 2v4a2 2 0 0 0 2 2h4\" /><path d=\"M10 9H8\" /><path d=\"M16 13H8\" /><path d=\"M16 17H8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M12 5v7l4 2\" /></svg></svg>",
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
            title: __('Unsubmitted journal entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4\" /><path d=\"M2 6h4\" /><path d=\"M2 10h4\" /><path d=\"M2 14h4\" /><path d=\"M2 18h4\" /><path d=\"M21.378 5.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M12 5v7l4 2\" /></svg></svg>",
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
        {variant: 'slate', title: __('Draft payments queue'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect x=\"3\" y=\"5\" width=\"6\" height=\"6\" rx=\"1\" /><path d=\"m3 17 2 2 4-4\" /><path d=\"M13 6h8\" /><path d=\"M13 12h8\" /><path d=\"M13 18h8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z\" /><path d=\"m15 5 4 4\" /></svg></svg>", description: __('Review draft payment entries before approval or posting.'), doctype: 'Payment Entry', report: 'SIG Finance Draft Payments Queue', route: ['query-report', 'SIG Finance Draft Payments Queue']},
        {variant: 'slate', title: __('Bank transactions'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e3ecf6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><line x1=\"3\" x2=\"21\" y1=\"22\" y2=\"22\" /><line x1=\"6\" x2=\"6\" y1=\"18\" y2=\"11\" /><line x1=\"10\" x2=\"10\" y1=\"18\" y2=\"11\" /><line x1=\"14\" x2=\"14\" y1=\"18\" y2=\"11\" /><line x1=\"18\" x2=\"18\" y1=\"18\" y2=\"11\" /><polygon points=\"12 2 20 7 4 7\" /></svg></svg>", description: __('Review statement evidence before matching or reconciliation.'), doctype: 'Bank Transaction', route: ['List', 'Bank Transaction', 'List']}
    ];

    const specialist = [
        {variant: 'warn', title: __('Petty cash'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e1efe7\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"20\" height=\"12\" x=\"2\" y=\"6\" rx=\"2\" /><circle cx=\"12\" cy=\"12\" r=\"2\" /><path d=\"M6 12h.01M18 12h.01\" /></svg></svg>", description: __('Review receipts, create draft clearance journals, and follow Finance submission.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], doctype: 'SIG PC Transaction', route: ['pc-invoice-review'],
            metric: {key: 'pc-pending-review', function: 'Count', filters: [['SIG PC Transaction', 'closure_status', 'in', ['Draft', 'Needs Review']]]}},
        {variant: 'navy', title: __('ZATCA Integrations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"5\" height=\"5\" x=\"3\" y=\"3\" rx=\"1\" /><rect width=\"5\" height=\"5\" x=\"16\" y=\"3\" rx=\"1\" /><rect width=\"5\" height=\"5\" x=\"3\" y=\"16\" rx=\"1\" /><path d=\"M21 16h-3a2 2 0 0 0-2 2v3\" /><path d=\"M21 21v.01\" /><path d=\"M12 7v3a2 2 0 0 1-2 2H7\" /><path d=\"M3 12h.01\" /><path d=\"M12 3h.01\" /><path d=\"M12 16v.01\" /><path d=\"M16 12h1\" /><path d=\"M21 12v.01\" /><path d=\"M12 21v-1\" /></svg></svg>", description: __('Review tax-compliance evidence linked to the source invoice.'), roleAny: ['System Manager', 'Accounts User', 'Accounts Manager'], route: ['Workspaces', 'ZATCA Integrations']}
    ];

    const references = [
        {variant: 'slate', title: __('Chart of accounts'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M21 12h-8\" /><path d=\"M21 6H8\" /><path d=\"M21 18h-8\" /><path d=\"M3 6v4c0 1.1.9 2 2 2h3\" /><path d=\"M3 10v6c0 1.1.9 2 2 2h3\" /></svg></svg>", description: __('Reference the account hierarchy; setup remains a controlled finance task.'), doctype: 'Account', route: ['List', 'Account', 'List']},
        {variant: 'slate', title: __('Cost centers'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><circle cx=\"12\" cy=\"12\" r=\"10\" /><circle cx=\"12\" cy=\"12\" r=\"6\" /><circle cx=\"12\" cy=\"12\" r=\"2\" /></svg></svg>", description: __('Reference financial responsibility and reporting dimensions.'), doctype: 'Cost Center', route: ['List', 'Cost Center', 'List']}
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
            ${item.metric ? `<span class="sig-finance-metric" data-metric-key="${frappe.utils.escape_html(item.metric.key)}">â€”</span>` : ''}${detail}
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
                : 'â€”';
            root.find(`[data-metric-key="${item.metric.key}"]`).text(formatted);
        }).catch(() => {
            root.find(`[data-metric-key="${item.metric.key}"]`).text('â€”');
        });
    });
};
