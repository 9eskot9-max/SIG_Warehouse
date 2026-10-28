/* Client reminder delivery stays a deliberate action on the saved ERP record. */
function sig_send_client_reminder(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__('Save your reminder edits before sending.'));
        return;
    }

    const channels = frm.doc.channel || 'WhatsApp';
    const recipients = [];
    if (['WhatsApp', 'WhatsApp + Email'].includes(channels)) {
        if (!frm.doc.recipient_whatsapp) {
            frappe.msgprint(__('Enter the client WhatsApp number in Send To Number before sending.'));
            return;
        }
        recipients.push(__('WhatsApp: {0}', [frm.doc.recipient_whatsapp]));
    }
    if (['Email', 'WhatsApp + Email'].includes(channels)) {
        if (!frm.doc.recipient_email) {
            frappe.msgprint(__('Enter the client email in Send To Email before sending.'));
            return;
        }
        recipients.push(__('Email: {0}', [frm.doc.recipient_email]));
    }

    const target = frappe.utils.escape_html(recipients.join(' / '));
    frappe.confirm(
        __('Send this reminder and invoice PDF copies to {0}?', [target]),
        async () => {
            const response = await frappe.call({
                method: 'sig_warehouse.client_collections.send_draft',
                args: {name: frm.doc.name},
                freeze: true,
                freeze_message: __('Sending reminder and invoice copies…'),
            });
            const result = response.message || {};
            await frm.reload_doc();
            frappe.msgprint({
                title: __('Reminder delivery status'),
                message: __('Status: {0}. Accepted components: {1}; failed components: {2}.', [
                    frappe.utils.escape_html(result.status || __('Unknown')),
                    Number(result.accepted || 0),
                    Number(result.failed || 0),
                ]),
            });
        }
    );
}

frappe.ui.form.on('SIG Client Collection Draft', {
    refresh(frm) {
        // Invoice membership and balance snapshots are created from Sales Invoices;
        // never let a user hand-edit the immutable source list.
        frm.set_df_property('invoices', 'read_only', 1);

        const editableStatuses = ['Draft'];
        const sendableStatuses = ['Draft', 'Partially Sent', 'Failed'];
        const locked = !editableStatuses.includes(frm.doc.status);
        [
            'customer', 'company', 'letter_date', 'letter_type', 'language', 'channel',
            'recipient_whatsapp', 'recipient_email', 'subject', 'greeting',
            'letter_body', 'whatsapp_message', 'closing',
        ].forEach((field) => frm.set_df_property(field, 'read_only', locked ? 1 : 0));

        const can_send = !frm.is_new() && sendableStatuses.includes(frm.doc.status);
        frm.set_df_property('send_reminder_button', 'hidden', !can_send);
        const button = frm.fields_dict.send_reminder_button?.$input;
        if (button) {
            button.addClass('btn-primary').off('click.sigClientCollections')
                .on('click.sigClientCollections', () => sig_send_client_reminder(frm));
        }
    },
});
