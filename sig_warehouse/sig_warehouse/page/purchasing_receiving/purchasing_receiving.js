frappe.pages['purchasing-receiving'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Purchasing & Receiving'), single_column: true});
    const root = $('<div class="sig-wh-intake"></div>').appendTo(page.main);

    function openIntake() {
        frappe.new_doc('SIG Warehouse Intake');
    }

    function render(rows) {
        const body = rows.map(row => `<tr>
            <td><a href="/app/sig-warehouse-intake/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(row.name)}</a></td>
            <td>${frappe.utils.escape_html(row.intake_type || '')}</td>
            <td>${frappe.utils.escape_html(row.supplier || '')}</td>
            <td>${frappe.utils.escape_html(row.source_reference || '')}</td>
            <td>${frappe.utils.escape_html(row.purchase_order || row.purchase_order_created || row.purchase_receipt || '')}</td>
            <td>${frappe.utils.escape_html(row.status || '')}</td>
            <td>${frappe.datetime.str_to_user(row.modified || '')}</td>
        </tr>`).join('');
        root.html(`<div class="sig-wh-intake-head"><div><h2>${__('Purchasing & Receiving')}</h2>
            <p>${__('Prepare and track native ERP Item, Purchase Order and Purchase Receipt drafts.')}</p></div>
            <div><button class="btn btn-primary" data-new-intake>${__('New intake')}</button>
            <button class="btn btn-default" data-refresh>${__('Refresh')}</button></div></div>
            <div class="sig-wh-intake-note">${__('ERP documents remain authoritative. Intake suggestions never submit or post stock.')}</div>
            <div class="table-responsive"><table class="table table-bordered"><thead><tr>
            <th>${__('Intake')}</th><th>${__('Action')}</th><th>${__('Supplier')}</th><th>${__('Source reference')}</th>
            <th>${__('ERP document')}</th><th>${__('Status')}</th><th>${__('Updated')}</th></tr></thead>
            <tbody>${body || `<tr><td colspan="7" class="text-muted">${__('No intakes yet.')}</td></tr>`}</tbody></table></div>`);
        root.find('[data-new-intake]').on('click', openIntake);
        root.find('[data-refresh]').on('click', load);
    }

    function load() {
        root.html(`<div class="text-muted">${__('Loading purchasing and receiving intakes…')}</div>`);
        frappe.call({method: 'sig_warehouse.sig_warehouse.warehouse_intake.list_intakes'})
            .then(r => render(r.message || []))
            .catch(() => root.html(`<div class="alert alert-danger">${__('Could not load intakes. Check your access and try Refresh.')}</div><button class="btn btn-default" data-retry>${__('Refresh')}</button>`))
            .finally(() => root.find('[data-retry]').on('click', load));
    }
    page.set_primary_action(__('New intake'), openIntake, 'add');
    load();
};
