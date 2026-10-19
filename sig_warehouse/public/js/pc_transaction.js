/* Native receipt form uses the same atomic confirmation as the PC review page. */
frappe.ui.form.on('SIG PC Transaction', {
    refresh(frm) {
        const esc = frappe.utils.escape_html;
        const preview = frm.fields_dict.receipt_preview?.$wrapper;
        if (preview) {
            preview.empty();
            if (frm.doc.source_media_url) {
                const src = esc(frm.doc.source_media_url);
                preview.html(`<a href="${src}" target="_blank" rel="noopener"><img src="${src}" alt="${esc(__('Original receipt'))}" style="max-width:100%;max-height:75vh"></a>`);
            }
        }
        const reviewer = ['System Manager', 'Accounts User', 'Accounts Manager', 'Operations User', 'Operations Manager', 'SIG PC Clearance'].some(role => frappe.user.has_role(role));
        if (!reviewer || frm.is_new() || !['Draft', 'Needs Review'].includes(frm.doc.closure_status)) return;
        frm.add_custom_button(__('Confirm — draft journal'), async () => {
            if (frm.is_dirty()) {
                frappe.msgprint(__('Save or reload the form before confirming.'));
                return;
            }
            await frappe.call({
                method: 'sig_warehouse.sig_warehouse.pc_journal.confirm_receipt',
                args: {transaction_id: frm.doc.name, expected_modified: frm.doc.modified},
                freeze: true,
            });
            await frm.reload_doc();
        }, __('Review'));
        frm.add_custom_button(__('Reject'), () => {
            if (frm.is_dirty()) {
                frappe.msgprint(__('Save or reload the form before rejecting.'));
                return;
            }
            frappe.prompt({fieldname: 'notes', fieldtype: 'Small Text', label: __('Reason'), reqd: 1}, async v => {
                await frappe.call({method: 'sig_warehouse.sig_warehouse.pc_journal.reject_receipt',
                    args: {transaction_id: frm.doc.name, expected_modified: frm.doc.modified, notes: v.notes}, freeze: true});
                await frm.reload_doc();
            }, __('Reject receipt'), __('Reject'));
        }, __('Review'));
    },
});
