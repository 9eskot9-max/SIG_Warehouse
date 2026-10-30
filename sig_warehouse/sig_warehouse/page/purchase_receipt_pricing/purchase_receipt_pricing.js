frappe.pages['purchase-receipt-pricing'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Complete receipt prices'), single_column: true});
    const root = $('<div class="sig-wh-pricing"></div>').appendTo(page.main);

    function render(rows) {
        const body = rows.map(row => `<tr>
            <td><a href="/app/purchase-receipt/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(row.name)}</a></td>
            <td>${frappe.utils.escape_html(row.supplier || '')}</td>
            <td>${frappe.utils.escape_html(row.item_code || '')}<br><span class="text-muted">${frappe.utils.escape_html(row.description || '')}</span></td>
            <td class="text-right">${frappe.utils.escape_html(String(row.qty || 0))} ${frappe.utils.escape_html(row.uom || '')}</td>
            <td>${__('Missing')}</td>
            <td><button class="btn btn-default btn-xs" data-open="${frappe.utils.escape_html(row.name)}">${__('Complete in ERP')}</button></td>
        </tr>`).join('');
        root.html(`<div class="page-header"><div><h3>${__('Purchase Receipts with missing prices')}</h3>
            <p class="text-muted">${__('Open a receipt and enter its rate in the native ERP form. Drafts only.')}</p></div>
            <button class="btn btn-default" data-refresh>${__('Refresh')}</button></div>
            <div class="alert alert-warning">${__('This queue shows draft receipts with a zero or missing rate. Submitted receipts require ERP amendment or an approved accounting correction.')}</div>
            <div class="table-responsive"><table class="table table-bordered"><thead><tr>
            <th>${__('Purchase Receipt')}</th><th>${__('Supplier')}</th><th>${__('Item')}</th><th>${__('Received')}</th><th>${__('Rate')}</th><th></th></tr></thead>
            <tbody>${body || `<tr><td colspan="6" class="text-muted">${__('No draft receipt lines have a missing rate.')}</td></tr>`}</tbody></table></div>`);
        root.find('[data-refresh]').on('click', load);
        root.find('[data-open]').on('click', function () { frappe.set_route('Form', 'Purchase Receipt', $(this).attr('data-open')); });
    }

    function load() {
        root.html(`<div class="text-muted">${__('Loading draft receipts…')}</div>`);
        frappe.call({method: 'sig_warehouse.sig_warehouse.warehouse_intake.list_purchase_receipts_missing_rates'})
            .then(r => render(r.message || []))
            .catch(() => root.html(`<div class="alert alert-danger">${__('Could not load the queue. Check Purchase Receipt read access and refresh.')}</div><button class="btn btn-default" data-refresh>${__('Refresh')}</button>`))
            .finally(() => root.find('[data-refresh]').on('click', load));
    }

    // The page already provides its own navigation. Do not let an optional
    // toolbar action prevent the receipt queue from rendering.
    if (typeof page.set_primary_action === 'function') {
        page.set_primary_action(__('New intake'), () => frappe.new_doc('SIG Warehouse Intake'));
    }
    load();
};
