frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;
        if (frm.doc.is_return) return;
        if (!['Material Issue', 'Material Transfer'].includes(frm.doc.purpose)) return;
        if (frm.__sig_declare_buttons_added) return;
        frm.__sig_declare_buttons_added = true;

        if (frm.doc.custom_return_state === 'DECLARED') {
            frm.add_custom_button(__('Reopen for correction'), () => sig_open_disposition_dialog(frm, 'REOPEN'), __('Declare'));
            return;
        }

        frm.add_custom_button(__('Declare Return'), () => sig_open_disposition_dialog(frm, 'RETURN'), __('Declare'));
        frm.add_custom_button(__('Declare Custody'), () => sig_open_disposition_dialog(frm, 'CUSTODY'), __('Declare'));
        frm.add_custom_button(__('Close as Consumed'), () => sig_open_disposition_dialog(frm, 'CLOSE'), __('Declare'));
    }
});

function sig_gen_operation_id(prefix) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `SIG-DISPOP-${prefix}-${stamp}-${Math.floor(Math.random() * 900 + 100)}`;
}

function sig_open_disposition_dialog(frm, action) {
    const openLines = (frm.doc.items || []).filter((it) => {
        if (action === 'REOPEN') return !!it.custom_return_closed;
        const returned = it.custom_qty_returned || 0;
        const custody = it.custom_qty_custody || 0;
        const undeclared = it.qty - returned - custody;
        return !it.custom_return_closed && undeclared > 0.000001;
    });
    if (!openLines.length) {
        frappe.msgprint(__('No undeclared lines on this DN.'));
        return;
    }

    const needsQty = action === 'RETURN' || action === 'CUSTODY';
    const rowsHtml = openLines.map((it) => {
        const returned = it.custom_qty_returned || 0;
        const custody = it.custom_qty_custody || 0;
        const undeclared = it.qty - returned - custody;
        return `
            <tr data-sed="${it.name}">
                <td>${frappe.utils.escape_html(it.item_code)}</td>
                <td class="text-right">${it.qty}</td>
                <td class="text-right">${returned}</td>
                <td class="text-right">${custody}</td>
                <td class="text-right">${undeclared}</td>
                ${needsQty ? `<td><input type="number" class="form-control input-sm sig-qty" step="any" min="0" max="${undeclared}" value="${undeclared}"></td>` : '<td><input type="checkbox" class="sig-include" checked></td>'}
            </tr>`;
    }).join('');

    const titleByAction = {
        RETURN: __('Declare Return'), CUSTODY: __('Declare Custody'), CLOSE: __('Close as Consumed'),
        REOPEN: __('Reopen for Correction'),
    };
    const extraFields = [];
    if (action === 'RETURN') {
        extraFields.push({ fieldtype: 'Data', fieldname: 'to_wh', label: __('To Warehouse'),
            default: openLines[0].s_warehouse, reqd: 1 });
        extraFields.push({ fieldtype: 'Date', fieldname: 'posting_date', label: __('Posting Date'),
            default: frappe.datetime.get_today() });
    } else if (action === 'CUSTODY') {
        extraFields.push({ fieldtype: 'Link', fieldname: 'custodian', label: __('Custodian'),
            options: 'Employee', reqd: 1 });
    }
    extraFields.push({ fieldtype: 'Small Text', fieldname: 'reason', label: __('Reason / Remarks'),
        reqd: action === 'REOPEN' });

    const d = new frappe.ui.Dialog({
        title: `${titleByAction[action]} - ${frm.doc.name}`,
        size: 'large',
        fields: [
            ...extraFields,
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'lines_html',
                options: `<div class="table-responsive"><table class="table table-bordered sig-disposition-lines">
                    <thead><tr>
                        <th>${__('Item')}</th><th class="text-right">${__('Issued')}</th>
                        <th class="text-right">${__('Returned')}</th><th class="text-right">${__('In Custody')}</th>
                        <th class="text-right">${__('Undeclared')}</th>
                        <th>${needsQty ? __('Qty') : __('Include')}</th>
                    </tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table></div>`,
            },
        ],
        primary_action_label: __('Confirm'),
        primary_action() {
            const rows = [...d.$wrapper.find('.sig-disposition-lines tbody tr')];
            const lines = rows.map((row) => {
                const $row = $(row);
                const sed = $row.data('sed');
                if (needsQty) {
                    const qty = parseFloat($row.find('.sig-qty').val() || '0');
                    return { sed, qty };
                }
                const included = $row.find('.sig-include').is(':checked');
                return included ? { sed, qty: null } : null;
            }).filter(Boolean).filter((l) => !needsQty || l.qty > 0);

            if (!lines.length) {
                frappe.msgprint(__('No lines selected.'));
                return;
            }
            const values = d.get_values();
            const operationId = sig_gen_operation_id(action);

            const confirmMsg = action === 'CLOSE'
                ? __('Close {0} line(s) as consumed? No stock movement, cannot be undone from here.', [lines.length])
                : action === 'REOPEN'
                    ? __('Reopen {0} line(s) for correction? This changes no stock; it only permits a later declared return or custody action.', [lines.length])
                : __('Declare {0} on {1} line(s)? This {2} immediately and cannot be undone from here.',
                    [titleByAction[action], lines.length, action === 'RETURN' ? __('submits a Stock Entry') : __('records custody')]);

            frappe.confirm(confirmMsg, () => {
                const args = {
                    operation_id: operationId, action, source_se: frm.doc.name, line_count: lines.length,
                    reason: values.reason,
                };
                if (action === 'RETURN') { args.to_wh = values.to_wh; args.posting_date = values.posting_date; }
                if (action === 'CUSTODY') { args.custodian = values.custodian; }
                lines.forEach((l, i) => {
                    args[`sed_${i + 1}`] = l.sed;
                    if (l.qty !== null && l.qty !== undefined) args[`qty_${i + 1}`] = l.qty;
                });
                frappe.call({
                    method: 'sig_warehouse.sig_warehouse.disposition.sig_declare_disposition',
                    args, freeze: true, freeze_message: __('Processing...'),
                    callback: (r) => {
                        const res = r.message || {};
                        if (res.result === 'created' || res.result === 'duplicate') {
                            frappe.msgprint({
                                title: __('Done'), indicator: 'green',
                                message: res.stock_entry
                                    ? __('Stock Entry {0} created and submitted.', [`<a href="/app/stock-entry/${res.stock_entry}">${res.stock_entry}</a>`])
                                    : __('Recorded.'),
                            });
                            d.hide();
                            frm.reload_doc();
                        } else if (res.result === 'exception' && res.reason === 'CAP_EXCEEDED') {
                            frappe.msgprint({ title: __('Cannot declare'), indicator: 'red',
                                message: __('Line {0}: requested {1} exceeds undeclared {2}. Reload and try again.',
                                    [res.line, res.requested, res.remaining]) });
                        } else if (res.result === 'conflict') {
                            frappe.msgprint({ title: __('Conflict'), indicator: 'red',
                                message: __('This attempt changed after the operation ID was generated. Close and retry.') });
                        } else {
                            frappe.msgprint({ title: __('Failed'), indicator: 'red', message: __('{0}', [JSON.stringify(res)]) });
                        }
                    },
                });
            });
        },
    });
    d.show();
}
