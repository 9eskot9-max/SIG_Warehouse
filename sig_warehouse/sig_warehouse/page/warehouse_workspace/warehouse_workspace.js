// Read-only navigation front door for the SIG Warehouse Workspace.
// Existing ERPNext forms, boards, reports, and permission checks remain authoritative.
frappe.pages['warehouse-workspace'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '',
        single_column: true
    });
    $(wrapper).find('.page-head').hide();
    const openOriginalWorkspace = () => {
        window.sessionStorage.setItem('sig_warehouse_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Warehouse');
    };
    const language = String(frappe.boot?.lang || 'en').toLowerCase();
    const root = $('<main class="sig-wh-home"></main>')
        .attr('dir', language.startsWith('ar') ? 'rtl' : 'ltr')
        .attr('lang', language)
        .appendTo(page.main);

    const primary = [
        {
            title: __('Purchasing & receiving'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><circle cx=\"8\" cy=\"21\" r=\"1\" /><circle cx=\"19\" cy=\"21\" r=\"1\" /><path d=\"M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M20 6 9 17l-5-5\" /></svg></svg>", variant: 'navy',
            description: __('Create and track native Item, Purchase Order, and Purchase Receipt drafts.'),
            doctype: 'SIG Warehouse Intake',
            permission: 'read',
            route: ['purchasing-receiving']
        },
        {
            title: __('Complete receipt prices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"m15 5 6.3 6.3a2.4 2.4 0 0 1 0 3.4L17 19\" /><path d=\"M9.586 5.586A2 2 0 0 0 8.172 5H3a1 1 0 0 0-1 1v5.172a2 2 0 0 0 .586 1.414L8.29 18.29a2.426 2.426 0 0 0 3.42 0l3.58-3.58a2.426 2.426 0 0 0 0-3.42z\" /><circle cx=\"6.5\" cy=\"9.5\" r=\".5\" fill=\"currentColor\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b5605a\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M12 6v7\" /><path d=\"M12 18h.01\" /></svg></svg>", variant: 'amber',
            description: __('Find draft Purchase Receipts with missing item rates and complete them in the native ERP form.'),
            doctype: 'Purchase Receipt',
            permission: 'read',
            route: ['purchase-receipt-pricing']
        },
        {
            title: __('Dispatch materials'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2\" /><path d=\"M15 18H9\" /><path d=\"M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14\" /><circle cx=\"17\" cy=\"18\" r=\"2\" /><circle cx=\"7\" cy=\"18\" r=\"2\" /></svg></svg>", variant: 'blue',
            description: __('Review material requests and issue approved items from the dispatch queue.'),
            doctype: 'Material Request',
            permission: 'write',
            page_roles: ['System Manager', 'Stock Manager', 'Stock User', 'Warehouse Manager'],
            route: ['dispatch-queue']
        },
        {
            title: __('Receive materials'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M12 22v-9\" /><path d=\"M15.17 2.21a1.67 1.67 0 0 1 1.63 0L21 4.57a1.93 1.93 0 0 1 0 3.36L8.82 14.79a1.655 1.655 0 0 1-1.64 0L3 12.43a1.93 1.93 0 0 1 0-3.36z\" /><path d=\"M20 13v3.87a2.06 2.06 0 0 1-1.11 1.83l-6 3.08a1.93 1.93 0 0 1-1.78 0l-6-3.08A2.06 2.06 0 0 1 4 16.87V13\" /><path d=\"M21 12.43a1.93 1.93 0 0 0 0-3.36L8.83 2.2a1.64 1.64 0 0 0-1.63 0L3 4.57a1.93 1.93 0 0 0 0 3.36l12.18 6.86a1.636 1.636 0 0 0 1.63 0z\" /></svg></svg>", variant: 'blue',
            description: __('Review and record goods received against purchase orders.'),
            doctype: 'Purchase Receipt',
            permission: 'create',
            route: ['List', 'Purchase Receipt']
        },
        {
            title: __('Stock entries and transfers'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"m16 3 4 4-4 4\" /><path d=\"M20 7H4\" /><path d=\"m8 21-4-4 4-4\" /><path d=\"M4 17h16\" /></svg></svg>", variant: 'blue',
            description: __('Review stock movements or start a transfer through the existing Stock Entry controls.'),
            doctype: 'Stock Entry',
            permission: 'create',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Returns and custody'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M9 14 4 9l5-5\" /><path d=\"M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11\" /></svg></svg>", variant: 'blue',
            description: __('Open the returns queue; declare return, custody, or consumption from the source stock entry.'),
            doctype: 'Stock Entry',
            report: 'SIG Returns Pending',
            route: ['query-report', 'SIG Returns Pending']
        }
    ];

    const queues = [
        {
            title: __('Dispatch Kanban board'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2\" /><path d=\"M15 18H9\" /><path d=\"M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14\" /><circle cx=\"17\" cy=\"18\" r=\"2\" /><circle cx=\"7\" cy=\"18\" r=\"2\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M12 5v7l4 2\" /></svg></svg>", variant: 'warn',
            description: __('Card board view of the same dispatch queue.'),
            doctype: 'Material Request',
            route: ['List', 'Material Request', 'Kanban', 'SIG Dispatch Queue']
        },
        {
            title: __('Dispatch operations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2\" /><path d=\"M15 18H9\" /><path d=\"M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14\" /><circle cx=\"17\" cy=\"18\" r=\"2\" /><circle cx=\"7\" cy=\"18\" r=\"2\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#386c91\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M5 12h14\" /><path d=\"m12 5 7 7-7 7\" /></svg></svg>", variant: 'navy',
            description: __('Trace recorded dispatch operations.'),
            doctype: 'SIG Dispatch Operation',
            route: ['List', 'SIG Dispatch Operation']
        },
        {
            title: __('As-Built'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M4.9 16.1C1 12.2 1 5.8 4.9 1.9\" /><path d=\"M7.8 4.7a6.14 6.14 0 0 0-.8 7.5\" /><circle cx=\"12\" cy=\"9\" r=\"2\" /><path d=\"M16.2 4.8c2 2 2.26 5.11.8 7.47\" /><path d=\"M19.1 1.9a9.96 9.96 0 0 1 0 14.1\" /><path d=\"M9.5 18h5\" /><path d=\"m8 22 4-11 4 11\" /></svg></svg>", variant: 'slate',
            description: __('Review issued, returned, and custody quantities by project/site.'),
            doctype: 'Stock Entry',
            report: 'SIG As-Built',
            route: ['query-report', 'SIG As-Built']
        }
    ];

    const stock = [
        {
            title: __('Item catalog'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M17 21v-2a1 1 0 0 1-1-1v-1a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1\" /><path d=\"M19 15V6.5a1 1 0 0 0-7 0v11a1 1 0 0 1-7 0V9\" /><path d=\"M21 21v-2h-4\" /><path d=\"M3 5h4V3\" /><path d=\"M7 5a1 1 0 0 1 1 1v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a1 1 0 0 1 1-1V3\" /></svg></svg>", variant: 'slate',
            description: __('Find the approved ERP item code, name, and stock unit.'),
            doctype: 'Item',
            route: ['List', 'Item']
        },
        {
            title: __('Warehouses'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#dcecec\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z\" /><path d=\"M6 18h12\" /><path d=\"M6 14h12\" /><rect width=\"12\" height=\"12\" x=\"6\" y=\"10\" /></svg></svg>", variant: 'slate',
            description: __('Look up warehouse locations and their hierarchy.'),
            doctype: 'Warehouse',
            route: ['List', 'Warehouse']
        },
        {
            title: __('SIG stock balance'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z\" /><path d=\"m7 16.5-4.74-2.85\" /><path d=\"m7 16.5 5-3\" /><path d=\"M7 16.5v5.17\" /><path d=\"M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z\" /><path d=\"m17 16.5-5-3\" /><path d=\"m17 16.5 4.74-2.85\" /><path d=\"M17 16.5v5.17\" /><path d=\"M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z\" /><path d=\"M12 8 7.26 5.15\" /><path d=\"m12 8 4.74-2.85\" /><path d=\"M12 13.5V8\" /></svg></svg>", variant: 'cyan',
            description: __('Inspect current item and warehouse balances.'),
            doctype: 'Bin',
            report: 'SIG Stock Balance',
            route: ['query-report', 'SIG Stock Balance']
        },
        {
            title: __('Stock value by warehouse'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#dcecec\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z\" /><path d=\"M6 18h12\" /><path d=\"M6 14h12\" /><rect width=\"12\" height=\"12\" x=\"6\" y=\"10\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8\" /><path d=\"M12 18V6\" /></svg></svg>", variant: 'cyan',
            description: __('Review the valuation view by warehouse.'),
            doctype: 'Bin',
            report: 'SIG Stock Value By Warehouse',
            route: ['query-report', 'SIG Stock Value By Warehouse']
        },
        {
            title: __('Custody by custodian'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5\" /><path d=\"M14 6a6 6 0 0 1 6 6v3\" /><path d=\"M4 15v-3a6 6 0 0 1 6-6\" /><rect x=\"2\" y=\"15\" width=\"20\" height=\"4\" rx=\"1\" /></svg></svg>", variant: 'cyan',
            description: __('Review stock currently recorded in hand.'),
            doctype: 'SIG IH Position',
            report: 'SIG In-Hand Custody By Custodian',
            route: ['query-report', 'SIG In-Hand Custody By Custodian']
        }
    ];

    const movement = [
        {
            title: __('Stock ledger'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M12 7v14\" /><path d=\"M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z\" /></svg></svg>", variant: 'navy',
            description: __('Trace posted stock movements and their accounting impact.'),
            doctype: 'Stock Ledger Entry',
            report: 'Stock Ledger',
            route: ['query-report', 'Stock Ledger']
        },
        {
            title: __('MIR fulfilment'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#dcecec\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"8\" height=\"4\" x=\"8\" y=\"2\" rx=\"1\" ry=\"1\" /><path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\" /><path d=\"m9 14 2 2 4-4\" /></svg></svg>", variant: 'amber',
            description: __('Compare requested, issued, and remaining quantities per request line.'),
            doctype: 'Material Request',
            report: 'SIG MIR Fulfilment',
            route: ['query-report', 'SIG MIR Fulfilment']
        },
        {
            title: __('Material ledger by project'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e6e4f2\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M12 7v14\" /><path d=\"M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#386c91\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z\" /><path d=\"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12\" /><path d=\"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17\" /></svg></svg>", variant: 'slate',
            description: __('Review issued-minus-returned quantities by project and item.'),
            doctype: 'Stock Entry',
            report: 'SIG Material Ledger By Project',
            route: ['query-report', 'SIG Material Ledger By Project']
        },
        {
            title: __('Stock entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M16 16h6\" /><path d=\"M19 13v6\" /><path d=\"M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l2-1.14\" /><path d=\"m7.5 4.27 9 5.15\" /><polyline points=\"3.29 7 12 12 20.71 7\" /><line x1=\"12\" x2=\"12\" y1=\"22\" y2=\"12\" /></svg></svg>", variant: 'navy',
            description: __('Search posted transfers and issues; goods receipts remain in Purchase Receipts.'),
            doctype: 'Stock Entry',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Purchase receipts'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z\" /><path d=\"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8\" /><path d=\"M12 17.5v-11\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M20 6 9 17l-5-5\" /></svg></svg>", variant: 'navy',
            description: __('Review posted goods receipts and their purchase-order links.'),
            doctype: 'Purchase Receipt',
            route: ['List', 'Purchase Receipt']
        }
    ];

    const controls = [
        {
            title: __('AI item prompt and key'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z\" /><path d=\"M20 3v4\" /><path d=\"M22 5h-4\" /><path d=\"M4 17v2\" /><path d=\"M5 18H3\" /></svg></svg>", variant: 'slate',
            description: __('Edit the item extraction prompt and maintain the encrypted OpenAI key.'),
            doctype: 'SIG AI Prompt Settings',
            route: ['Form', 'SIG AI Prompt Settings', 'SIG AI Prompt Settings']
        },
        {
            title: __('Stock reconciliation â€” controlled'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z\" /><path d=\"m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z\" /><path d=\"M7 21h10\" /><path d=\"M12 3v18\" /><path d=\"M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#386c91\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" ry=\"2\" /><path d=\"M7 11V7a5 5 0 0 1 10 0v4\" /></svg></svg>", variant: 'navy',
            description: __('Use for an approved physical-count correction; this is not a routine adjustment shortcut.'),
            doctype: 'Stock Reconciliation',
            permission: 'create',
            route: ['List', 'Stock Reconciliation']
        },
        {
            title: __('Item groups'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z\" /><path d=\"M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z\" /><path d=\"M3 5a2 2 0 0 0 2 2h3\" /><path d=\"M3 3v13a2 2 0 0 0 2 2h3\" /></svg></svg>", variant: 'slate',
            description: __('Reference the approved catalog grouping.'),
            doctype: 'Item Group',
            route: ['List', 'Item Group']
        },
        {
            title: __('Units of measure'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"6\" y=\"6\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z\" /><path d=\"m14.5 12.5 2-2\" /><path d=\"m11.5 9.5 2-2\" /><path d=\"m8.5 6.5 2-2\" /><path d=\"m17.5 15.5 2-2\" /></svg></svg>", variant: 'slate',
            description: __('Reference ERPNext stock and purchase units.'),
            doctype: 'UOM',
            route: ['List', 'UOM']
        }
    ];

    const purchasingDocuments = [
        {
            title: __('Supplier RFQs'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"20\" height=\"16\" x=\"2\" y=\"4\" rx=\"2\" /><path d=\"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#b98536\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\" /><path d=\"M12 18h.01\" /></svg></svg>", variant: 'amber',
            description: __('Prepare an ERP quotation request and send its letter to selected suppliers by WhatsApp.'),
            doctype: 'Request for Quotation',
            linked_doctypes: ['Supplier'],
            permission: 'create',
            route: ['List', 'Request for Quotation']
        },
        {
            title: __('Purchase Orders'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#f3e9d6\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><rect width=\"8\" height=\"4\" x=\"8\" y=\"2\" rx=\"1\" ry=\"1\" /><path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\" /><path d=\"M12 11h4\" /><path d=\"M12 16h4\" /><path d=\"M8 11h.01\" /><path d=\"M8 16h.01\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M20 6 9 17l-5-5\" /></svg></svg>", variant: 'slate',
            description: __('Purchasing owns the order; use it as receipt context, not a warehouse approval.'),
            doctype: 'Purchase Order',
            route: ['List', 'Purchase Order']
        },
        {
            title: __('Quotations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\"><svg x=\"3\" y=\"3\" width=\"36\" height=\"36\" viewBox=\"0 0 24 24\" fill=\"#e1efe7\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#386c91\"><path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\" /><path d=\"M14 2v4a2 2 0 0 0 2 2h4\" /><path d=\"M10 9H8\" /><path d=\"M16 13H8\" /><path d=\"M16 17H8\" /></svg><circle cx=\"36\" cy=\"36\" r=\"9\" fill=\"#4f8f72\" stroke=\"#fff\" stroke-width=\"2\"/><svg x=\"30.5\" y=\"30.5\" width=\"11\" height=\"11\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\" color=\"#fff\"><path d=\"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8\" /><path d=\"M12 18V6\" /></svg></svg>", variant: 'slate',
            description: __('Review the purchasing quotation reference; purchasing owns the commercial decision.'),
            doctype: 'Quotation',
            route: ['List', 'Quotation']
        }
    ];

    function card(item, compact) {
        const icon = item.iconSvg
            ? `<span class="sig-wh-icon" aria-hidden="true">${item.iconSvg}</span>`
            : '';
        const description = item.description
            ? `<span class="sig-wh-description">${frappe.utils.escape_html(item.description)}</span>`
            : '';
        return `<button type="button" class="sig-wh-card sig-wh-card--${item.variant || 'slate'} ${compact ? 'sig-wh-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}">
            <span class="sig-wh-card-top">${icon}</span>
            <span class="sig-wh-card-title">${frappe.utils.escape_html(item.title)}</span>
            ${description}
        </button>`;
    }

    function allowed(item) {
        if (!frappe.model.can_read(item.doctype)) return false;
        if ((item.linked_doctypes || []).some((doctype) => !frappe.model.can_read(doctype))) return false;
        if (item.page_roles && !frappe.user.has_role(item.page_roles)) return false;
        if (item.permission === 'write' && !frappe.model.can_write(item.doctype)) return false;
        if (item.permission === 'create' && !frappe.model.can_create(item.doctype)) return false;
        if (item.report) {
            const reportGrants = frappe.boot?.user?.can_get_report;
            if (Array.isArray(reportGrants) && !reportGrants.includes(item.doctype)) return false;
            const reports = frappe.boot?.allowed_reports;
            if (Array.isArray(reports)) {
                const found = reports.some((report) => (typeof report === 'string' ? report : report.name) === item.report);
                if (!found) return false;
            } else if (reports && typeof reports === 'object' && !Array.isArray(reports) && !(item.report in reports)) {
                return false;
            }
        }
        return true;
    }

    function section(title, detail, items) {
        const available = items.filter(allowed);
        if (!available.length) return '';
        return `<section class="sig-wh-section sig-wh-lower-section">
            <div class="sig-wh-section-heading"><div><h2>${frappe.utils.escape_html(title)}</h2>
                <p>${frappe.utils.escape_html(detail)}</p></div></div>
            <div class="sig-wh-reference-grid">${available.map((item) => card(item, true)).join('')}</div>
        </section>`;
    }

    function render() {
        const availablePrimary = primary.filter(allowed);
        root.html(`<header class="sig-wh-header">
                <div><div class="sig-wh-eyebrow">${__('SIG Warehouse')}</div>
                    <h1>${__('Warehouse workbench')}</h1>
                    <p>${__('Daily warehouse work, with stock records and controls kept in their existing ERPNext flows.')}</p>
                </div>
                <div class="sig-wh-header-actions"><button type="button" class="btn btn-default sig-wh-native-workspace">${__('Original Warehouse Workspace')}</button>
                    <span class="sig-wh-header-mark" aria-hidden="true"><i class="fa fa-cubes"></i></span></div>
            </header>
            ${availablePrimary.length ? `<section class="sig-wh-section" aria-labelledby="sig-wh-primary-title">
                <div class="sig-wh-section-heading"><div><h2 id="sig-wh-primary-title">${__('Start work')}</h2>
                    <p>${__('Choose the task you need to complete.')}</p></div></div>
                <div class="sig-wh-primary-grid">${availablePrimary.map((item) => card(item, false)).join('')}</div>
            </section>` : ''}
            ${section(__('Open queues'), __('Work waiting for review or follow-up.'), queues)}
            ${section(__('Purchasing documents'), __('Review purchase orders and quotations; purchasing owns commercial decisions.'), purchasingDocuments)}
            ${section(__('Stock and locations'), __('Item and warehouse references, followed by current position.'), stock)}
            ${section(__('Movement history'), __('Use these views for traceability and project follow-up.'), movement)}
            ${section(__('Controls and handoffs'), __('Less-frequent setup and controlled stock corrections.'), controls)}
            <p class="sig-wh-footnote">${__('Tiles open existing ERPNext records and reports. Your current role permissions control visibility and actions; item creation follows the approved master-data controls, and this page does not create a second stock ledger.')}</p>`);

        root.find('.sig-wh-card').on('click', function () {
            let route;
            try { route = JSON.parse($(this).attr('data-route')); }
            catch (e) { return; }
            if (Array.isArray(route) && route.length) frappe.set_route(...route);
        });
        root.find('.sig-wh-native-workspace').on('click', openOriginalWorkspace);
    }

    render();
};
