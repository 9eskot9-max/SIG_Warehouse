// Read-only navigation front door for the SIG Warehouse Workspace.
// Existing ERPNext forms, boards, reports, and permission checks remain authoritative.
frappe.pages['warehouse-workspace'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Warehouse'),
        single_column: true
    });
    page.add_inner_button(__('Original Warehouse Workspace'), () => {
        window.sessionStorage.setItem('sig_warehouse_allow_native_workspace_once', '1');
        frappe.set_route('Workspaces', 'SIG Warehouse');
    });
    const root = $('<main class="sig-wh-home"></main>').appendTo(page.main);

    const primary = [
        {
            title: __('Dispatch materials'),
            description: __('Review material requests and issue approved items from the dispatch board.'),
            icon: 'truck',
            doctype: 'Material Request',
            permission: 'write',
            route: ['List', 'Material Request', 'Kanban']
        },
        {
            title: __('Receive materials'),
            description: __('Review and record goods received against purchase orders.'),
            icon: 'inbox',
            doctype: 'Purchase Receipt',
            permission: 'create',
            route: ['List', 'Purchase Receipt']
        },
        {
            title: __('Stock entries and transfers'),
            description: __('Review stock movements or start a transfer through the existing Stock Entry controls.'),
            icon: 'exchange',
            doctype: 'Stock Entry',
            permission: 'create',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Returns and custody'),
            description: __('Open the returns queue; declare return, custody, or consumption from the source stock entry.'),
            icon: 'undo',
            doctype: 'Stock Entry',
            report: 'SIG Returns Pending',
            route: ['query-report', 'SIG Returns Pending']
        }
    ];

    const queues = [
        {
            title: __('Dispatch queue report'),
            description: __('Review pending and partial material requests.'),
            doctype: 'Material Request',
            report: 'SIG Dispatch Queue',
            route: ['query-report', 'SIG Dispatch Queue']
        },
        {
            title: __('Dispatch operations'),
            description: __('Trace recorded dispatch operations.'),
            doctype: 'SIG Dispatch Operation',
            route: ['List', 'SIG Dispatch Operation']
        },
        {
            title: __('As-Built'),
            description: __('Review issued, returned, and custody quantities by project/site.'),
            doctype: 'Stock Entry',
            report: 'SIG As-Built',
            route: ['query-report', 'SIG As-Built']
        }
    ];

    const stock = [
        {
            title: __('Item catalog'),
            description: __('Find the approved ERP item code, name, and stock unit.'),
            doctype: 'Item',
            route: ['List', 'Item']
        },
        {
            title: __('Warehouses'),
            description: __('Look up warehouse locations and their hierarchy.'),
            doctype: 'Warehouse',
            route: ['List', 'Warehouse']
        },
        {
            title: __('SIG stock balance'),
            description: __('Inspect current item and warehouse balances.'),
            doctype: 'Bin',
            report: 'SIG Stock Balance',
            route: ['query-report', 'SIG Stock Balance']
        },
        {
            title: __('Stock value by warehouse'),
            description: __('Review the valuation view by warehouse.'),
            doctype: 'Bin',
            report: 'SIG Stock Value By Warehouse',
            route: ['query-report', 'SIG Stock Value By Warehouse']
        },
        {
            title: __('Custody by custodian'),
            description: __('Review stock currently recorded in hand.'),
            doctype: 'SIG IH Position',
            report: 'SIG In-Hand Custody By Custodian',
            route: ['query-report', 'SIG In-Hand Custody By Custodian']
        }
    ];

    const movement = [
        {
            title: __('Stock ledger'),
            description: __('Trace posted stock movements and their accounting impact.'),
            doctype: 'Stock Ledger Entry',
            report: 'Stock Ledger',
            route: ['query-report', 'Stock Ledger']
        },
        {
            title: __('MIR fulfilment'),
            description: __('Compare requested, issued, and remaining quantities per request line.'),
            doctype: 'Material Request',
            report: 'SIG MIR Fulfilment',
            route: ['query-report', 'SIG MIR Fulfilment']
        },
        {
            title: __('Material ledger by project'),
            description: __('Review issued-minus-returned quantities by project and item.'),
            doctype: 'Stock Entry',
            report: 'SIG Material Ledger By Project',
            route: ['query-report', 'SIG Material Ledger By Project']
        },
        {
            title: __('Stock entries'),
            description: __('Search posted transfers and issues; goods receipts remain in Purchase Receipts.'),
            doctype: 'Stock Entry',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Purchase receipts'),
            description: __('Review posted goods receipts and their purchase-order links.'),
            doctype: 'Purchase Receipt',
            route: ['List', 'Purchase Receipt']
        }
    ];

    const controls = [
        {
            title: __('Stock reconciliation — controlled'),
            description: __('Use for an approved physical-count correction; this is not a routine adjustment shortcut.'),
            doctype: 'Stock Reconciliation',
            permission: 'create',
            route: ['List', 'Stock Reconciliation']
        },
        {
            title: __('Item groups'),
            description: __('Reference the approved catalog grouping.'),
            doctype: 'Item Group',
            route: ['List', 'Item Group']
        },
        {
            title: __('Units of measure'),
            description: __('Reference ERPNext stock and purchase units.'),
            doctype: 'UOM',
            route: ['List', 'UOM']
        },
        {
            title: __('Purchase orders — handoff'),
            description: __('Purchasing owns the order; use it as receipt context, not a warehouse approval.'),
            doctype: 'Purchase Order',
            route: ['List', 'Purchase Order']
        }
    ];

    function card(item, compact) {
        const icon = item.icon
            ? `<span class="sig-wh-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>`
            : '';
        const description = item.description
            ? `<span class="sig-wh-description">${frappe.utils.escape_html(item.description)}</span>`
            : '';
        return `<button type="button" class="sig-wh-card ${compact ? 'sig-wh-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}">
            <span class="sig-wh-card-top">${icon}<i class="fa fa-external-link sig-wh-open-icon" aria-hidden="true"></i></span>
            <span class="sig-wh-card-title">${frappe.utils.escape_html(item.title)}</span>
            ${description}
        </button>`;
    }

    function allowed(item) {
        if (!frappe.model.can_read(item.doctype)) return false;
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
                <span class="sig-wh-header-mark" aria-hidden="true"><i class="fa fa-cubes"></i></span>
            </header>
            ${availablePrimary.length ? `<section class="sig-wh-section" aria-labelledby="sig-wh-primary-title">
                <div class="sig-wh-section-heading"><div><h2 id="sig-wh-primary-title">${__('Start work')}</h2>
                    <p>${__('Choose the task you need to complete.')}</p></div></div>
                <div class="sig-wh-primary-grid">${availablePrimary.map((item) => card(item, false)).join('')}</div>
            </section>` : ''}
            ${section(__('Open queues'), __('Work waiting for review or follow-up.'), queues)}
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
    }

    render();
};
