frappe.ui.form.on('Material Request', {
    refresh(frm) {
        if (frm.doc.material_request_type !== 'Material Issue') return;
        if (frm.doc.docstatus !== 1) return;
        if (!['PENDING', 'PARTIAL'].includes(frm.doc.custom_dispatch_stage)) return;
        if (frm.__sig_dispatch_button_added) return;
        frm.__sig_dispatch_button_added = true;
        // Standalone primary button (not nested under "Actions") so it is
        // immediately visible on the page - a separate Client Script
        // ("SIG MR Issue Button") tried to add this as a shortcut by
        // simulating a click on the old dropdown item via a data-label
        // selector that Frappe's dropdown markup doesn't actually expose,
        // so it silently did nothing. Consolidated into this one real
        // button instead of maintaining two.
        const $btn = frm.add_custom_button(__('Issue'), () => sig_open_dispatch_dialog(frm));
        $btn.removeClass('btn-default').addClass('btn-primary');

        // ERPNext's own core script adds a native "Create > Stock Entry" /
        // "Issue Material" shortcut for a submitted Material Issue MR - it
        // bypasses this app's whole flow (DN voucher allocation, remaining-
        // qty caps, the dispatch rollup, SIG Dispatch Operation audit trail),
        // so having both next to each other is confusing and the native one
        // is actively wrong to use here. Core's refresh handler runs before
        // this one (this app's JS bundle loads after erpnext's), so the
        // button already exists in the DOM by the time we get here - find it
        // by text under the "Create" dropdown rather than guessing its exact
        // label/version, and drop it silently if the version in use doesn't
        // add one at all.
        (frm.page.wrapper.find('.menu-btn-group, .custom-actions').find('.dropdown-menu a.dropdown-item') || [])
            .each(function () {
                const $item = $(this);
                if (/stock entry|issue material/i.test($item.text().trim())) {
                    $item.closest('li').remove();
                }
            });
    }
});

// Dispatch dialog builder - used by the form "Issue" button above. Also
// duplicated (not imported) in material_request_list.js for the Kanban
// board's per-card "Issue" action: doctype_js (this file) and
// doctype_list_js (that file) are two independently-loaded bundles in
// Frappe - a Form page never loads the list bundle and a List/Kanban page
// never loads this one, so sharing a function between them by reference
// is not reliable. Keep both copies in sync if this logic changes.
function sig_gen_operation_id(warehouse) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const safeWh = (warehouse || 'WH').replace(/[^A-Za-z0-9]/g, '').slice(0, 12) || 'WH';
    return `SIG-DISPOP-${safeWh}-${stamp}-${Math.floor(Math.random() * 900 + 100)}`;
}

function sig_open_dispatch_dialog(frm) {
    const openLines = (frm.doc.items || []).filter(it => (it.custom_qty_remaining || 0) > 0.000001);
    if (!openLines.length) {
        frappe.msgprint(__('No open lines to dispatch on this request.'));
        return;
    }
    const fromWarehouse = openLines[0].warehouse;

    frappe.call({
        method: 'check_dn_availability',
        args: {
            from_wh: fromWarehouse,
            line_count: openLines.length,
            ...Object.fromEntries(openLines.flatMap((it, i) => [
                [`code_${i + 1}`, it.item_code],
                [`qty_${i + 1}`, it.custom_qty_remaining],
                [`uom_${i + 1}`, it.uom],
            ])),
        },
        freeze: true,
        freeze_message: __('Checking availability...'),
        callback: (r) => sig_render_dispatch_dialog(frm, openLines, fromWarehouse, r.message),
    });
}

function sig_render_dispatch_dialog(frm, openLines, fromWarehouse, availability) {
    const avByLine = {};
    if (availability && availability.result === 'ok') {
        availability.lines.forEach((l) => { avByLine[l.line] = l; });
    }

    const rowsHtml = openLines.map((it, i) => {
        const av = avByLine[i + 1];
        const available = av ? av.available : '?';
        const defaultQty = av ? Math.min(it.custom_qty_remaining, av.available) : it.custom_qty_remaining;
        const shortFlag = av && !av.sufficient ? ' <span class="text-danger">(short)</span>' : '';
        return `
            <tr data-mri="${it.name}" data-item="${it.item_code}" data-uom="${it.uom}">
                <td>${frappe.utils.escape_html(it.item_code)}</td>
                <td class="text-right">${it.qty}</td>
                <td class="text-right">${(it.custom_qty_issued || 0)}</td>
                <td class="text-right">${it.custom_qty_remaining}</td>
                <td class="text-right">${available}${shortFlag}</td>
                <td><input type="number" class="form-control input-sm sig-qty" step="any" min="0"
                    max="${it.custom_qty_remaining}" value="${defaultQty}"></td>
                <td>
                    <select class="form-control input-sm sig-outcome">
                        <option value="DISPATCH" selected>${__('Dispatch')}</option>
                        <option value="PENDING">${__('Leave pending')}</option>
                    </select>
                </td>
                <td></td>
            </tr>`;
    }).join('');

    const d = new frappe.ui.Dialog({
        title: __('Dispatch {0}', [frm.doc.name]),
        size: 'large',
        fields: [
            { fieldtype: 'Data', fieldname: 'from_wh', label: __('From Warehouse'), default: fromWarehouse, read_only: 1 },
            { fieldtype: 'Date', fieldname: 'posting_date', label: __('Posting Date'), default: frappe.datetime.get_today() },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Link', fieldname: 'dispatched_to', label: __('Dispatched To'), options: 'Employee' },
            { fieldtype: 'Small Text', fieldname: 'remarks', label: __('Remarks') },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'lines_html',
                options: `<div class="table-responsive"><table class="table table-bordered sig-dispatch-lines">
                    <thead><tr>
                        <th>${__('Item')}</th><th class="text-right">${__('Requested')}</th>
                        <th class="text-right">${__('Issued')}</th><th class="text-right">${__('Remaining')}</th>
                        <th class="text-right">${__('Available')}</th><th>${__('Qty to Dispatch')}</th>
                        <th>${__('Outcome')}</th><th></th>
                    </tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table></div>`,
            },
            { fieldtype: 'Section Break', label: __('Add an item not on this request') },
            { fieldtype: 'Link', fieldname: 'new_item_code', label: __('Item'), options: 'Item',
              get_query: () => ({ filters: { disabled: 0 } }) },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Float', fieldname: 'new_item_qty', label: __('Qty'), default: 1 },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Button', fieldname: 'add_item_btn', label: __('+ Add to list'),
              click: () => sig_add_line_to_dispatch_dialog(d) },
        ],
        primary_action_label: __('Confirm Dispatch'),
        async primary_action() {
            const rows = [...d.$wrapper.find('.sig-dispatch-lines tbody tr')];
            const existingLines = rows.filter((row) => !$(row).data('new')).map((row) => {
                const $row = $(row);
                return {
                    mri: $row.data('mri'),
                    qty: parseFloat($row.find('.sig-qty').val() || '0'),
                    outcome: $row.find('.sig-outcome').val(),
                };
            }).filter((l) => l.outcome === 'DISPATCH' && l.qty > 0);
            const newRows = rows.filter((row) => $(row).data('new'));

            // New items chosen via "Add an item not on this request" only
            // become real Material Request lines now, at Confirm - not when
            // added to this table. Anything removed from the table before
            // this point (the x button) never touches the server, so there
            // is nothing to undo for a plain change of mind.
            const addedLines = [];
            for (const row of newRows) {
                const $row = $(row);
                const qty = parseFloat($row.find('.sig-qty').val() || '0');
                if (!(qty > 0)) continue;
                let res;
                try {
                    res = (await frappe.call({
                        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_add_mr_line',
                        args: { mr: frm.doc.name, item_code: $row.data('item'), qty, uom: $row.data('uom') },
                        freeze: true, freeze_message: __('Adding {0}...', [$row.data('item')]),
                    })).message || {};
                } catch (e) {
                    res = { result: 'exception', reason: String(e) };
                }
                if (res.result !== 'created') {
                    frappe.msgprint({
                        title: __('Could not add {0}', [$row.data('item')]),
                        indicator: 'red',
                        message: __('{0}', [JSON.stringify(res)]),
                    });
                    return; // stop before dispatching anything on a partial failure
                }
                addedLines.push({ mri: res.mri, qty, outcome: 'DISPATCH' });
            }

            const lines = existingLines.concat(addedLines);
            if (!lines.length) {
                frappe.msgprint(__('No lines selected to dispatch.'));
                return;
            }
            const totalQty = lines.reduce((s, l) => s + l.qty, 0);
            const values = d.get_values();
            const operationId = sig_gen_operation_id(fromWarehouse);

            frappe.confirm(
                __('Dispatch {0} line(s), total qty {1}, from {2}?<br><br>This creates and <b>submits</b> a Stock Entry immediately - it cannot be un-submitted from here.',
                    [lines.length, totalQty, fromWarehouse]),
                () => {
                    const args = {
                        operation_id: operationId, mr: frm.doc.name, from_wh: fromWarehouse,
                        posting_date: values.posting_date, dispatched_to: values.dispatched_to,
                        remarks: values.remarks, line_count: lines.length,
                    };
                    lines.forEach((l, i) => {
                        args[`mri_${i + 1}`] = l.mri;
                        args[`qty_${i + 1}`] = l.qty;
                        args[`outcome_${i + 1}`] = l.outcome;
                    });
                    frappe.call({
                        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_dispatch_mr',
                        args,
                        freeze: true,
                        freeze_message: __('Dispatching...'),
                        callback: (r) => {
                            const res = r.message || {};
                            if (res.result === 'created' || res.result === 'duplicate') {
                                frappe.msgprint({
                                    title: __('Dispatched'),
                                    indicator: 'green',
                                    message: __('Stock Entry {0} created and submitted.', [
                                        `<a href="/app/stock-entry/${res.stock_entry}">${res.stock_entry}</a>`]),
                                });
                                d.hide();
                                frm.reload_doc();
                            } else if (res.result === 'exception' && res.reason === 'CAP_EXCEEDED') {
                                frappe.msgprint({
                                    title: __('Cannot dispatch'),
                                    indicator: 'red',
                                    message: __('Line {0}: requested {1} exceeds remaining {2}. Reload and try again.',
                                        [res.line, res.requested, res.remaining]),
                                });
                            } else if (res.result === 'conflict') {
                                frappe.msgprint({
                                    title: __('Conflict'),
                                    indicator: 'red',
                                    message: __('This dispatch attempt changed after the operation ID was generated. Close this dialog and retry.'),
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('Dispatch failed'),
                                    indicator: 'red',
                                    message: __('{0}', [JSON.stringify(res)]),
                                });
                            }
                        },
                    });
                }
            );
        },
    });
    d.show();
}

function sig_add_line_to_dispatch_dialog(d) {
    const itemCode = d.get_value('new_item_code');
    const qty = parseFloat(d.get_value('new_item_qty') || '0');
    if (!itemCode) {
        frappe.msgprint(__('Pick an item first.'));
        return;
    }
    if (!(qty > 0)) {
        frappe.msgprint(__('Qty must be greater than 0.'));
        return;
    }
    frappe.db.get_value('Item', itemCode, 'stock_uom').then((r) => {
        const uom = (r.message && r.message.stock_uom) || '';
        const $row = $(`
            <tr data-new="1" data-item="${itemCode}" data-uom="${uom}">
                <td>${frappe.utils.escape_html(itemCode)} <span class="text-muted">(${__('new')})</span></td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td><input type="number" class="form-control input-sm sig-qty" step="any" min="0" value="${qty}"></td>
                <td><select class="form-control input-sm sig-outcome">
                        <option value="DISPATCH" selected>${__('Dispatch')}</option>
                    </select></td>
                <td><span class="sig-remove-new-row text-danger" style="cursor:pointer;" title="${__('Remove')}">&times;</span></td>
            </tr>`);
        $row.find('.sig-remove-new-row').on('click', () => $row.remove());
        d.$wrapper.find('.sig-dispatch-lines tbody').append($row);
        d.set_value('new_item_code', '');
        d.set_value('new_item_qty', 1);
    });
}
