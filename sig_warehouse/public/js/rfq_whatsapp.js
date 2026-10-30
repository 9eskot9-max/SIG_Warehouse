frappe.ui.form.on('Request for Quotation', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Supplier WhatsApp numbers'), async () => {
            const response = await frappe.call({method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.supplier_numbers', args: {name: frm.doc.name}});
            const rows = response.message?.suppliers || [];
            if (!rows.length) { frappe.msgprint(__('Add suppliers to the RFQ first.')); return; }
            if (response.message.test_mode) {
                frappe.msgprint(__('Maytapi test mode is enabled. Sending will go to the configured test number, not the selected suppliers.'));
            }
            const fields = rows.flatMap((row, i) => [
                {fieldtype: 'Check', fieldname: 'send_' + i, label: __('Select {0}', [row.supplier]), default: 1},
                {fieldtype: 'Data', fieldname: 'phone_' + i, label: row.supplier, default: row.phone, description: __('Include country code')}
            ]);
            const saveNumbers = async values => {
                for (let i = 0; i < rows.length; i++) {
                    if (values['phone_' + i] && values['phone_' + i] !== rows[i].phone) {
                        await frappe.call({method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.save_supplier_number', args: {name: frm.doc.name, supplier: rows[i].supplier, phone: values['phone_' + i]}});
                        rows[i].phone = values['phone_' + i];
                    }
                }
            };
            const dialog = new frappe.ui.Dialog({title: __('Supplier WhatsApp numbers'), fields,
                primary_action_label: __('Save numbers'), primary_action: async values => {
                    await saveNumbers(values);
                    dialog.hide(); frappe.show_alert(__('Supplier numbers saved'));
                }});
            if (frm.doc.docstatus === 1) {
                dialog.set_secondary_action(() => {
                    const values = dialog.get_values();
                    if (!values) return;
                    const selected = rows.filter((row, i) => values['send_' + i]);
                    if (!selected.length) { frappe.msgprint(__('Select at least one supplier.')); return; }
                    if (selected.some(row => !values['phone_' + rows.indexOf(row)])) { frappe.msgprint(__('Enter a phone number for each selected supplier.')); return; }
                    frappe.confirm(__('Send the RFQ letter to {0} selected supplier(s)?', [selected.length]), async () => {
                        await saveNumbers(values);
                        const results = [];
                        for (const row of selected) {
                            try {
                                const args = {name: frm.doc.name, supplier: row.supplier};
                                let result = await frappe.call({method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.send_supplier', args, freeze: true});
                                if (result.message.retry_confirmation_required) {
                                    const retry = await new Promise(resolve => frappe.confirm(
                                        __('The previous delivery status is failed or uncertain. Check Maytapi before retrying to avoid duplicate messages. Retry this supplier now?'),
                                        () => resolve(true), () => resolve(false)
                                    ));
                                    if (retry) result = await frappe.call({
                                        method: 'sig_warehouse.sig_warehouse.rfq_whatsapp.send_supplier',
                                        args: {...args, retry_failed: 1}, freeze: true
                                    });
                                    else { results.push(row.supplier + ': ' + __('Retry skipped')); continue; }
                                }
                                const status = result.message.status || 'Unknown';
                                results.push(row.supplier + ': ' + (status === 'Sending' ? __('Queued in ERP') : status));
                            } catch (err) { results.push(row.supplier + ': ' + __('Error')); }
                        }
                        dialog.hide(); await frm.reload_doc();
                        const queued = results.some(x => x.endsWith(__('Queued in ERP')));
                        frappe.msgprint({title: __('RFQ delivery results'),
                            message: (queued ? __('Delivery is running in the background. Refresh the RFQ later to see Maytapi status.') + '<br><br>' : '') +
                                results.map(x => frappe.utils.escape_html(x)).join('<br>')});
                    });
                }, __('Send RFQ via WhatsApp'));
            }
            dialog.show();
        });
    }
});
