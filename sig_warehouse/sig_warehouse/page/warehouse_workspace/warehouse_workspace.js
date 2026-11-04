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
            title: __('Purchasing & receiving'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 8h5l4 22h23l5-16H12\" fill=\"#e6f5ee\"/><circle cx=\"18\" cy=\"37\" r=\"3\"/><circle cx=\"34\" cy=\"37\" r=\"3\"/><path d=\"m20 22 4 4 8-8\"/></svg>", variant: 'navy',
            description: __('Create and track native Item, Purchase Order, and Purchase Receipt drafts.'),
            doctype: 'SIG Warehouse Intake',
            permission: 'read',
            route: ['purchasing-receiving']
        },
        {
            title: __('Complete receipt prices'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M24 20v17M28 23c-2-3-8-3-8 1 0 4 8 2 8 6s-6 4-8 1\"/></svg>", variant: 'amber',
            description: __('Find draft Purchase Receipts with missing item rates and complete them in the native ERP form.'),
            doctype: 'Purchase Receipt',
            permission: 'read',
            route: ['purchase-receipt-pricing']
        },
        {
            title: __('Dispatch materials'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M4 12h25v20H4zM29 20h8l6 7v5H29z\" fill=\"#e3f2e9\"/><circle cx=\"13\" cy=\"35\" r=\"4\" fill=\"#fff\"/><circle cx=\"36\" cy=\"35\" r=\"4\" fill=\"#fff\"/><path d=\"M30 25h10\"/></svg>", variant: 'blue',
            description: __('Review material requests and issue approved items from the dispatch board.'),
            doctype: 'Material Request',
            permission: 'write',
            route: ['List', 'Material Request', 'Kanban']
        },
        {
            title: __('Receive materials'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 24 24 16l17 8v13l-17 7-17-7z\" fill=\"#fff0da\"/><path d=\"m7 24 17 8 17-8M24 32v12M24 4v13m-5-5 5 5 5-5\"/></svg>", variant: 'blue',
            description: __('Review and record goods received against purchase orders.'),
            doctype: 'Purchase Receipt',
            permission: 'create',
            route: ['List', 'Purchase Receipt']
        },
        {
            title: __('Stock entries and transfers'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 14h34v28H7z\" fill=\"#fbeed9\"/><path d=\"M7 21h34M20 14v7\"/><path d=\"M14 32h19m-5-5 5 5-5 5\"/></svg>", variant: 'blue',
            description: __('Review stock movements or start a transfer through the existing Stock Entry controls.'),
            doctype: 'Stock Entry',
            permission: 'create',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Returns and custody'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 14h34v28H7z\" fill=\"#fbeed9\"/><path d=\"M7 21h34M20 14v7\"/><path d=\"M34 32H15m5-5-5 5 5 5\"/></svg>", variant: 'blue',
            description: __('Open the returns queue; declare return, custody, or consumption from the source stock entry.'),
            doctype: 'Stock Entry',
            report: 'SIG Returns Pending',
            route: ['query-report', 'SIG Returns Pending']
        }
    ];

    const queues = [
        {
            title: __('Dispatch queue report'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><circle cx=\"24\" cy=\"29\" r=\"8\"/><path d=\"M24 24v5l4 2\"/></svg>", variant: 'warn',
            description: __('Review pending and partial material requests.'),
            doctype: 'Material Request',
            report: 'SIG Dispatch Queue',
            route: ['query-report', 'SIG Dispatch Queue']
        },
        {
            title: __('Dispatch operations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M4 12h25v20H4zM29 20h8l6 7v5H29z\" fill=\"#e3f2e9\"/><circle cx=\"13\" cy=\"35\" r=\"4\" fill=\"#fff\"/><circle cx=\"36\" cy=\"35\" r=\"4\" fill=\"#fff\"/><path d=\"M9 19h13M9 24h13M30 25h10\"/></svg>", variant: 'navy',
            description: __('Trace recorded dispatch operations.'),
            doctype: 'SIG Dispatch Operation',
            route: ['List', 'SIG Dispatch Operation']
        },
        {
            title: __('As-Built'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"m17 29 5 5 10-12\"/></svg>", variant: 'slate',
            description: __('Review issued, returned, and custody quantities by project/site.'),
            doctype: 'Stock Entry',
            report: 'SIG As-Built',
            route: ['query-report', 'SIG As-Built']
        }
    ];

    const stock = [
        {
            title: __('Item catalog'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"6\" y=\"6\" width=\"36\" height=\"36\" rx=\"4\" fill=\"#e2efff\"/><path d=\"M16 22h5v5h-5zM27 22h5v5h-5zM16 31h5v5h-5zM27 31h5v5h-5z\"/></svg>", variant: 'slate',
            description: __('Find the approved ERP item code, name, and stock unit.'),
            doctype: 'Item',
            route: ['List', 'Item']
        },
        {
            title: __('Warehouses'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M6 18 24 7l18 11v24H6z\" fill=\"#e1f2ee\"/><path d=\"M12 42V21h24v21M17 27h14M17 33h14\"/></svg>", variant: 'slate',
            description: __('Look up warehouse locations and their hierarchy.'),
            doctype: 'Warehouse',
            route: ['List', 'Warehouse']
        },
        {
            title: __('SIG stock balance'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 12 16 7l11 5v12l-11 5-11-5zM21 27l10-5 11 5v11l-11 5-10-5z\" fill=\"#e7f2fb\"/><path d=\"m5 12 11 5 11-5M16 17v12M21 27l10 5 11-5M31 32v11\"/></svg>", variant: 'cyan',
            description: __('Inspect current item and warehouse balances.'),
            doctype: 'Bin',
            report: 'SIG Stock Balance',
            route: ['query-report', 'SIG Stock Balance']
        },
        {
            title: __('Stock value by warehouse'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M6 18 24 7l18 11v24H6z\" fill=\"#e1f2ee\"/><path d=\"M12 42V21h24v21M24 23v15M28 26c-2-2-8-2-8 1 0 4 8 2 8 5s-6 3-8 1\"/></svg>", variant: 'cyan',
            description: __('Review the valuation view by warehouse.'),
            doctype: 'Bin',
            report: 'SIG Stock Value By Warehouse',
            route: ['query-report', 'SIG Stock Value By Warehouse']
        },
        {
            title: __('Custody by custodian'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"24\" cy=\"14\" r=\"7\" fill=\"#f8e5d6\"/><path d=\"M8 40c1-10 7-15 16-15s15 5 16 15z\" fill=\"#dcecff\"/><path d=\"M19 32h10M20 36h8\"/></svg>", variant: 'cyan',
            description: __('Review stock currently recorded in hand.'),
            doctype: 'SIG IH Position',
            report: 'SIG In-Hand Custody By Custodian',
            route: ['query-report', 'SIG In-Hand Custody By Custodian']
        }
    ];

    const movement = [
        {
            title: __('Stock ledger'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M29 17h9M29 22h9M29 27h7\"/></svg>", variant: 'navy',
            description: __('Trace posted stock movements and their accounting impact.'),
            doctype: 'Stock Ledger Entry',
            report: 'Stock Ledger',
            route: ['query-report', 'Stock Ledger']
        },
        {
            title: __('MIR fulfilment'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"30\" height=\"34\" rx=\"4\" fill=\"#e4f3f7\"/><path d=\"M18 9V5h12v4\"/><path d=\"M15 19h3v3h-3zM22 20h11M15 27h3v3h-3zM22 28h11M15 35h3v3h-3zM22 36h8\"/></svg>", variant: 'amber',
            description: __('Compare requested, issued, and remaining quantities per request line.'),
            doctype: 'Material Request',
            report: 'SIG MIR Fulfilment',
            route: ['query-report', 'SIG MIR Fulfilment']
        },
        {
            title: __('Material ledger by project'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 13c-5-4-12-4-19-2v27c7-2 14-2 19 2 5-4 12-4 19-2V11c-7-2-14-2-19 2z\" fill=\"#e7e9fb\"/><path d=\"M24 13v27M9 17h10M9 22h10M9 27h8\"/><path d=\"M28 18h4v4h-4zM35 18h4v4h-4zM28 26h4v4h-4zM35 26h4v4h-4z\"/></svg>", variant: 'slate',
            description: __('Review issued-minus-returned quantities by project and item.'),
            doctype: 'Stock Entry',
            report: 'SIG Material Ledger By Project',
            route: ['query-report', 'SIG Material Ledger By Project']
        },
        {
            title: __('Stock entries'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 14h34v28H7z\" fill=\"#fbeed9\"/><path d=\"M7 21h34M20 14v7\"/><path d=\"M14 28h12M14 33h18M14 37h10\"/></svg>", variant: 'navy',
            description: __('Search posted transfers and issues; goods receipts remain in Purchase Receipts.'),
            doctype: 'Stock Entry',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Purchase receipts'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"m17 29 5 5 10-12\"/></svg>", variant: 'navy',
            description: __('Review posted goods receipts and their purchase-order links.'),
            doctype: 'Purchase Receipt',
            route: ['List', 'Purchase Receipt']
        }
    ];

    const controls = [
        {
            title: __('AI item prompt and key'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"7\" width=\"38\" height=\"28\" rx=\"4\" fill=\"#e2f2f9\"/><path d=\"M17 42h14M24 35v7\"/><circle cx=\"21\" cy=\"20\" r=\"4\"/><path d=\"m24 23 8 7m-3-3 2-2m0 4 2-2\"/></svg>", variant: 'slate',
            description: __('Edit the item extraction prompt and maintain the encrypted OpenAI key.'),
            doctype: 'SIG AI Prompt Settings',
            route: ['Form', 'SIG AI Prompt Settings', 'SIG AI Prompt Settings']
        },
        {
            title: __('Stock reconciliation — controlled'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M24 6v34M9 41h30M11 14h26M13 14 6 27h14zM35 14l-7 13h14z\" fill=\"#fff3d9\"/><path d=\"M5 27c2 6 13 6 16 0M27 27c2 6 13 6 16 0\"/></svg>", variant: 'navy',
            description: __('Use for an approved physical-count correction; this is not a routine adjustment shortcut.'),
            doctype: 'Stock Reconciliation',
            permission: 'create',
            route: ['List', 'Stock Reconciliation']
        },
        {
            title: __('Item groups'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 12h15l4 5h19v22H5z\" fill=\"#e9efff\"/><path d=\"M5 17h38\"/><path d=\"M16 22h5v5h-5zM27 22h5v5h-5zM16 31h5v5h-5zM27 31h5v5h-5z\"/></svg>", variant: 'slate',
            description: __('Reference the approved catalog grouping.'),
            doctype: 'Item Group',
            route: ['List', 'Item Group']
        },
        {
            title: __('Units of measure'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M7 30 30 7l11 11-23 23z\" fill=\"#fff1d9\"/><path d=\"m13 24 4 4m1-9 4 4m1-9 4 4m1-9 4 4\"/></svg>", variant: 'slate',
            description: __('Reference ERPNext stock and purchase units.'),
            doctype: 'UOM',
            route: ['List', 'UOM']
        }
    ];

    const purchasingDocuments = [
        {
            title: __('Supplier RFQs'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M20 25c0-5 8-5 8 0 0 3-4 4-4 6m0 4h.1\"/></svg>", variant: 'amber',
            description: __('Prepare an ERP quotation request and send its letter to selected suppliers by WhatsApp.'),
            doctype: 'Request for Quotation',
            linked_doctypes: ['Supplier'],
            permission: 'create',
            route: ['List', 'Request for Quotation']
        },
        {
            title: __('Purchase Orders'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 8h5l4 22h23l5-16H12\" fill=\"#e6f5ee\"/><circle cx=\"18\" cy=\"37\" r=\"3\"/><circle cx=\"34\" cy=\"37\" r=\"3\"/><path d=\"M18 20h16M19 25h13\"/></svg>", variant: 'slate',
            description: __('Purchasing owns the order; use it as receipt context, not a warehouse approval.'),
            doctype: 'Purchase Order',
            route: ['List', 'Purchase Order']
        },
        {
            title: __('Quotations'), iconSvg: "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"#386c91\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M13 5h20l7 7v32H13z\" fill=\"#e3efff\"/><path d=\"M33 5v8h7\"/><path d=\"M24 20v17M28 23c-2-3-8-3-8 1 0 4 8 2 8 6s-6 4-8 1\"/></svg>", variant: 'slate',
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
