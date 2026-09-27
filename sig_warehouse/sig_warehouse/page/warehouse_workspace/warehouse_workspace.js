// Read-only navigation front door for the SIG Warehouse Workspace.
// Existing ERPNext forms, boards, reports, and permission checks remain authoritative.
frappe.pages['warehouse-workspace'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Warehouse'),
        single_column: true
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
            title: __('Transfer stock'),
            description: __('Move items between warehouses using the standard Stock Entry flow.'),
            icon: 'exchange',
            doctype: 'Stock Entry',
            permission: 'create',
            route: ['List', 'Stock Entry']
        },
        {
            title: __('Returns and custody'),
            description: __('Review in-hand positions and follow the existing return declaration process.'),
            icon: 'undo',
            doctype: 'SIG IH Position',
            route: ['List', 'SIG IH Position']
        }
    ];

    const reference = [
        {
            title: __('Returns awaiting declaration'),
            description: __('Review the existing returns queue.'),
            doctype: 'Stock Entry',
            route: ['query-report', 'SIG Returns Pending']
        },
        {
            title: __('SIG stock balance'),
            description: __('Inspect the current item and warehouse position.'),
            doctype: 'Bin',
            route: ['query-report', 'SIG Stock Balance']
        },
        {
            title: __('Stock ledger'),
            description: __('Trace posted stock movements.'),
            doctype: 'Stock Ledger Entry',
            route: ['query-report', 'Stock Ledger']
        },
        {
            title: __('Material requests'),
            description: __('Search and review requests beyond the dispatch board.'),
            doctype: 'Material Request',
            route: ['List', 'Material Request']
        }
    ];

    function card(item, compact) {
        const icon = item.icon
            ? `<span class="sig-wh-icon" aria-hidden="true"><i class="fa fa-${item.icon}"></i></span>`
            : '';
        const description = compact ? '' : `<span class="sig-wh-description">${frappe.utils.escape_html(item.description)}</span>`;
        return `<button type="button" class="sig-wh-card ${compact ? 'sig-wh-card-compact' : ''}"
                    data-route="${frappe.utils.escape_html(JSON.stringify(item.route))}">
            <span class="sig-wh-card-top">${icon}<i class="fa fa-external-link sig-wh-open-icon" aria-hidden="true"></i></span>
            <span class="sig-wh-card-title">${frappe.utils.escape_html(item.title)}</span>
            ${description}
        </button>`;
    }

    function render() {
        const allowed = (item) => {
            if (!frappe.model.can_read(item.doctype)) return false;
            if (item.permission === 'write') return frappe.model.can_write(item.doctype);
            if (item.permission === 'create') return frappe.model.can_create(item.doctype);
            return true;
        };
        const availablePrimary = primary.filter(allowed);
        const availableReference = reference.filter((item) => frappe.model.can_read(item.doctype));
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
            ${availableReference.length ? `<section class="sig-wh-section sig-wh-reference" aria-labelledby="sig-wh-reference-title">
                <div class="sig-wh-section-heading"><div><h2 id="sig-wh-reference-title">${__('Review and trace')}</h2>
                    <p>${__('Supporting queues and stock reference views.')}</p></div></div>
                <div class="sig-wh-reference-grid">${availableReference.map((item) => card(item, true)).join('')}</div>
            </section>` : ''}
            <p class="sig-wh-footnote">${__('Tiles open existing ERPNext records and reports. Your current role permissions still control what you can view or do.')}</p>`);

        root.find('.sig-wh-card').on('click', function () {
            let route;
            try { route = JSON.parse($(this).attr('data-route')); }
            catch (e) { return; }
            if (Array.isArray(route) && route.length) frappe.set_route(...route);
        });
    }

    render();
};
