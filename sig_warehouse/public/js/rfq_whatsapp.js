frappe.ui.form.on('Request for Quotation', {
    refresh(frm) {
        if (frm.is_new() || frm.doc.docstatus !== 1 || !frm.doc.suppliers?.length) return;
        frm.add_custom_button(__('Send RFQ via WhatsApp'), async () => {
            if (frm.is_dirty()) {
                await frm.save();
                await frm.reload_doc();
            }
            const response = await frappe.call({
                method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.supplier_numbers',
                args: {name: frm.doc.name}
            });
            const suppliers = response.message?.suppliers || [];
            if (!suppliers.length) {
                frappe.msgprint(__('Add suppliers to the RFQ first.'));
                return;
            }
            if (response.message.test_mode) {
                frappe.msgprint(__('Maytapi test mode is enabled. Sending will go to the configured test number, not the selected suppliers.'));
            }

            const fields = [{
                fieldtype: 'HTML',
                fieldname: 'entry_hint',
                options: `<div class="text-muted">${__('Numbers are entered in the supplier rows on this RFQ. Saving creates a native Supplier Contact. Missing numbers are shown below.')}</div>`
            }];
            suppliers.forEach((row, i) => fields.push({
                fieldtype: 'Check',
                fieldname: 'send_' + i,
                label: row.supplier,
                description: row.phone ? __('WhatsApp: {0}', [frappe.utils.escape_html(row.phone)]) : __('WhatsApp number missing — enter it in the supplier row first.'),
                default: row.phone ? 1 : 0
            }));

            const dialog = new frappe.ui.Dialog({
                title: __('Send RFQ via WhatsApp'),
                fields,
                primary_action_label: __('Send selected RFQs'),
                primary_action: async values => {
                    const selected = suppliers.filter((row, i) => values['send_' + i]);
                    if (!selected.length) {
                        frappe.msgprint(__('Select at least one supplier.'));
                        return;
                    }
                    const missing = selected.filter(row => !row.phone);
                    if (missing.length) {
                        frappe.msgprint(__('Enter a WhatsApp number for: {0}', [missing.map(row => row.supplier).join(', ')]));
                        return;
                    }
                    frappe.confirm(__('Send an individual RFQ PDF to {0} selected supplier(s)?', [selected.length]), async () => {
                        const results = [];
                        for (const row of selected) {
                            try {
                                const args = {name: frm.doc.name, supplier: row.supplier};
                                let result = await frappe.call({
                                    method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.send_supplier',
                                    args,
                                    freeze: true
                                });
                                if (result.message.retry_confirmation_required) {
                                    const retry = await new Promise(resolve => frappe.confirm(
                                        __('The previous delivery status is failed or uncertain. Check Maytapi before retrying to avoid duplicate messages. Retry this supplier now?'),
                                        () => resolve(true), () => resolve(false)
                                    ));
                                    if (retry) {
                                        result = await frappe.call({
                                            method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.send_supplier',
                                            args: {...args, retry_failed: 1},
                                            freeze: true
                                        });
                                    } else {
                                        results.push(row.supplier + ': ' + __('Retry skipped'));
                                        continue;
                                    }
                                }
                                const status = result.message.status || 'Unknown';
                                results.push(row.supplier + ': ' + (status === 'Sending' ? __('Queued in ERP') : status));
                            } catch (err) {
                                results.push(row.supplier + ': ' + __('Error'));
                            }
                        }
                        dialog.hide();
                        await frm.reload_doc();
                        const queued = results.some(x => x.endsWith(__('Queued in ERP')));
                        frappe.msgprint({
                            title: __('RFQ delivery results'),
                            message: (queued ? __('Delivery is running in the background. Refresh the RFQ later to see Maytapi status.') + '<br><br>' : '') +
                                results.map(x => frappe.utils.escape_html(x)).join('<br>')
                        });
                    });
                }
            });
            dialog.show();
        });
    }
});

frappe.ui.form.on('Request for Quotation Supplier', {
    supplier(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.supplier || row.custom_whatsapp_number) return;
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.supplier_phone',
            args: {supplier: row.supplier}
        }).then(response => {
            const number = response.message?.phone;
            if (number && !row.custom_whatsapp_number) {
                frappe.model.set_value(cdt, cdn, 'custom_whatsapp_number', number);
            }
        });
    }
});
