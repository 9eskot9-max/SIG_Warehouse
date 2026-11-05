function sig_intake_find_items(frm) {
            const dialog = new frappe.ui.Dialog({title: __('Find ERP Items'), fields:[
                {fieldtype:'Data',fieldname:'query',label:__('Search by item code or name'),reqd:1},
                {fieldtype:'HTML',fieldname:'results'}
            ], primary_action_label:__('Search'), primary_action(values) {
                frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.find_items',args:{text:values.query}})
                    .then(r => {
                        const items = r.message || [];
                        const html = items.map(item => `<button type="button" class="btn btn-default btn-xs" data-code="${frappe.utils.escape_html(item.name)}" data-name="${frappe.utils.escape_html(item.item_name || '')}" data-uom="${frappe.utils.escape_html(item.stock_uom || '')}">${frappe.utils.escape_html(item.name)} · ${frappe.utils.escape_html(item.item_name || '')} · ${frappe.utils.escape_html(item.stock_uom || '')}</button>`).join('<br>') || __('No Items found.');
                        dialog.fields_dict.results.$wrapper.html(html);
                        dialog.fields_dict.results.$wrapper.find('[data-code]').on('click', function() {
                            const row = frm.add_child('lines'); row.item_code = $(this).data('code'); row.item_name = $(this).data('name'); row.description = row.item_name || row.item_code;
                            row.uom = $(this).data('uom'); row.qty = 1; row.match_status = 'Matched'; frm.refresh_field('lines'); dialog.hide();
                        });
                    });
            }});
            dialog.show();
}

async function sig_intake_similar(frm) {
    if (frm.is_new() || frm.is_dirty()) await frm.save();
    const result = await frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.similar_items_for_rows',
        args:{intake_name:frm.doc.name}, freeze:true, freeze_message:__('Checking existing items…')});
    const groups = result.message || [];
    if (!groups.length) { frappe.msgprint(__('No similar items were found. Review the proposed codes before creating items.')); return; }
    const esc = frappe.utils.escape_html;
    const dialog = new frappe.ui.Dialog({title:__('Possible existing items'), fields:[{fieldtype:'HTML',fieldname:'matches'}]});
    dialog.fields_dict.matches.$wrapper.html(groups.map((group, gi) =>
        `<div style="margin-bottom:16px"><strong>${esc(group.description || '')}</strong><br>` +
        group.items.map((item, ii) => `<button type="button" class="btn btn-default btn-sm" style="margin:4px" data-group="${gi}" data-item="${ii}">${esc(item.name)} · ${esc(item.item_name || '')} · ${esc(item.stock_uom || '')}</button>`).join('') + '</div>').join('') +
        `<p class="text-muted">${__('Select an existing item if it matches; otherwise close this window and review the proposed code.')}</p>`);
    dialog.fields_dict.matches.$wrapper.find('[data-group]').on('click', async function() {
        const group = groups[Number(this.dataset.group)], item = group.items[Number(this.dataset.item)];
        const row = (frm.doc.lines || []).find(r => r.name === group.row);
        if (!row) return;
        await frappe.model.set_value(row.doctype, row.name, {item_code:item.name, item_name:item.item_name,
            uom:item.stock_uom, match_status:'Matched', item_family_key:'', proposed_item_code:'', proposal_basis:''});
        groups.splice(Number(this.dataset.group), 1);
        dialog.hide();
        frappe.show_alert({message:__('Existing item selected. Save the intake.'), indicator:'green'});
    });
    dialog.show();
}

function sig_intake_guide(frm) {
    const field = frm.fields_dict.lines;
    if (!field || !field.$wrapper) return;
    $(frm.wrapper).find('.sig-intake-guide').remove();
    const guide = $('<div class="sig-intake-guide" style="border:1px solid var(--border-color);border-radius:8px;padding:16px;margin:16px 0;background:var(--card-bg)">' +
        '<div style="font-weight:600;font-size:15px">' + __('Add items') + '</div>' +
        '<p class="text-muted" style="margin:6px 0 12px">' + __('Enter descriptions and units, suggest item codes, edit a code if needed, then create the items.') + '</p>' +
        '<button type="button" class="btn btn-default btn-sm" data-find-item>' + __('Find existing item') + '</button> ' +
        '<button type="button" class="btn btn-default btn-sm" data-suggest-items>' + __('Suggest item codes') + '</button> ' +
        '<button type="button" class="btn btn-default btn-sm" data-similar>' + __('Review similar items') + '</button> ' +
        '<button type="button" class="btn btn-primary btn-sm" data-create-item>' + __('Create items from rows') + '</button></div>');
    field.$wrapper.before(guide);
    guide.find('[data-find-item]').on('click', () => {
        if (frm.doc.docstatus !== 0 || frm.doc.purchase_order_created || frm.doc.purchase_receipt) { frappe.msgprint(__('Create a new intake to add more items.')); return; }
        sig_intake_find_items(frm);
    });
    guide.find('[data-suggest-items]').on('click', async () => {
        if (frm.doc.docstatus !== 0 || frm.doc.purchase_order_created || frm.doc.purchase_receipt) { frappe.msgprint(__('Create a new intake to add more items.')); return; }
        if (frm.is_new() || frm.is_dirty()) await frm.save();
        await frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.suggest_items_from_rows',
            args:{intake_name:frm.doc.name}, freeze:true, freeze_message:__('Suggesting item codes…')});
        await frm.reload_doc();
        await sig_intake_similar(frm);
    });
    guide.find('[data-similar]').on('click', () => sig_intake_similar(frm));
    guide.find('[data-create-item]').on('click', async () => {
        if (frm.doc.docstatus !== 0 || frm.doc.purchase_order_created || frm.doc.purchase_receipt) {
            frappe.msgprint(__('Create a new intake to add more items.')); return;
        }
        if (!frm.doc.item_creation_group) { frappe.msgprint(__('Choose the item group for new items.')); return; }
        if (!(frm.doc.lines || []).some(row => !row.item_code)) { frappe.msgprint(__('There are no rows without an Item.')); return; }
        if (frm.is_new() || frm.is_dirty()) await frm.save();
        const missingCode = (frm.doc.lines || []).find(row => !row.item_code && !(row.proposed_item_code || '').trim());
        if (missingCode) {
            frappe.msgprint({
                title: __('Item code needed'),
                message: __('Line {0}: select “Suggest item codes”, review the proposed code, then choose “Create items from rows” again. You can also enter an approved item code manually.', [missingCode.idx]),
                indicator: 'orange'
            });
            return;
        }
        const result = await frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.create_items_from_rows',
            args:{intake_name:frm.doc.name}, freeze:true, freeze_message:__('Creating items…')});
        await frm.reload_doc();
        frappe.show_alert({message: __('Created {0} item(s).', [result.message.created]), indicator:'green'});
    });
}

function sig_intake_add_item(frm) {
            const dialog = new frappe.ui.Dialog({title:__('Create item'), fields:[
                {fieldname:'item_help', fieldtype:'HTML', options:'<p class="text-muted">' + __('Creating an item adds it to the ERP item catalogue. Review the suggested details first.') + '</p>'},
                {fieldname:'source_text', fieldtype:'Small Text', label:__('Item description from supplier'), description:__('Paste the description or specifications, then select Suggest with AI. Review the result before creating the item.')},
                {fieldname:'suggest', fieldtype:'Button', label:__('Suggest with AI'), click:() => {
                    frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.suggest_item',
                        args:{intake_name:frm.doc.name, source_text:dialog.get_value('source_text')}, freeze:true})
                        .then(r => { const v=r.message || {}; dialog.set_value('item_name',v.item_name || ''); dialog.set_value('description',v.description || ''); const esc=frappe.utils.escape_html; dialog.fields_dict.ai_details.$wrapper.html('<p class="text-muted">' + __('Supplier code') + ': ' + esc(v.source_code || '—') + ' · ' + __('Suggested unit') + ': ' + esc(v.uom || '—') + '</p>'); });
                }},
                {fieldname:'ai_details', fieldtype:'HTML'},
                {fieldname:'item_code', fieldtype:'Data', label:__('Item code'), reqd:1},
                {fieldname:'item_name', fieldtype:'Data', label:__('Item name'), reqd:1},
                {fieldname:'description', fieldtype:'Small Text', label:__('Description'), reqd:1},
                {fieldname:'item_group', fieldtype:'Link', options:'Item Group', label:__('Item group'), reqd:1},
                {fieldname:'stock_uom', fieldtype:'Link', options:'UOM', label:__('Stock unit'), reqd:1}
            ], primary_action_label:__('Create item'), primary_action(values) {
                frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.create_item',
                    freeze:true, freeze_message:__('Creating item…'), args:{intake_name:frm.doc.name, item_code:values.item_code, item_name:values.item_name,
                        description:values.description, item_group:values.item_group, stock_uom:values.stock_uom}})
                    .then(r => { const item=r.message; const row=frm.add_child('lines');
                        row.item_code=item.name; row.item_name=item.item_name; row.description=item.description;
                        row.uom=item.stock_uom; row.qty=1; row.source_text=values.source_text || ''; row.match_status='Matched'; frm.refresh_field('lines'); dialog.hide(); frappe.show_alert({message:__('Item created. Complete the line and save the intake.'), indicator:'green'}); });
            }});
            dialog.show();
}

function sig_intake_submit(frm) {
    frappe.call({method: 'sig_warehouse.sig_warehouse.warehouse_intake.submit_linked_draft',
        args: {intake_name: frm.doc.name}, freeze: true, freeze_message: __('Submitting through ERP controls…')
    }).then(r => {
        if (r.message && r.message.name) frappe.show_alert({message: __('Submitted {0}', [r.message.name]), indicator:'green'});
        frm.reload_doc();
    }).catch(() => {
        frappe.msgprint(__('The ERP document remains a draft. Review the validation message and open the draft to correct it.'));
        frm.reload_doc();
    });
}

function sig_intake_review(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__('Save the intake changes before creating an ERP document.'));
        return;
    }
    const esc = v => frappe.utils.escape_html(v == null ? '' : String(v));
    const rows = (frm.doc.lines || []).map(row => `<tr><td>${esc(row.item_code || row.description)}</td><td>${esc(row.qty)}</td><td>${esc(row.uom)}</td><td>${esc(row.warehouse)}</td><td>${esc(row.rate)}</td></tr>`).join('');
    const html = `<p><b>${__('Supplier')}:</b> ${esc(frm.doc.supplier)} &nbsp; <b>${__('Company')}:</b> ${esc(frm.doc.company)}</p>
        <p><b>${__('Action')}:</b> ${esc(frm.doc.intake_type)} &nbsp; <b>${__('Purchase Order')}:</b> ${esc(frm.doc.purchase_order || '—')}</p>
        <div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__('Item')}</th><th>${__('Quantity')}</th><th>${__('UOM')}</th><th>${__('Warehouse')}</th><th>${__('Rate')}</th></tr></thead><tbody>${rows}</tbody></table></div>
        <p class="text-muted">${__('Review the lines on the intake before continuing. ERP checks the current user, PO balances and posting rules.')}</p>`;
    const dialog = new frappe.ui.Dialog({title: __('Review purchasing / receiving'), size:'large',
        fields:[{fieldtype:'HTML',fieldname:'summary',options:html}],
        primary_action_label: __('Save ERP draft'),
        primary_action() { create(false); }
    });
    function create(submit) {
        dialog.hide();
        frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.create_native_draft',
            args:{intake_name:frm.doc.name}, freeze:true, freeze_message:__('Creating ERP draft…')
        }).then(() => {
            if (submit) sig_intake_submit(frm);
            else { frappe.show_alert({message:__('ERP draft created'), indicator:'green'}); frm.reload_doc(); }
        });
    }
    const doctype = frm.doc.intake_type === 'Purchase Order' ? 'Purchase Order' : 'Purchase Receipt';
    if (frappe.model.can_submit(doctype)) dialog.set_secondary_action(() => create(true), __('Create draft and submit'));
    dialog.show();
}

frappe.ui.form.on('SIG Warehouse Intake', {
    onload(frm) {
        if (frm.is_new() && !(frm.doc.lines || []).length) {
            const row = frm.add_child('lines');
            row.qty = 1;
            row.conversion_factor = 1;
            row.match_status = 'Needs Review';
            frm.refresh_field('lines');
        }
        if (frm.is_new() && !frm.doc.company) frm.set_value('company', frappe.defaults.get_user_default('Company'));
        if (!frm.doc.item_creation_group && frm.doc.docstatus === 0 && !frm.doc.purchase_order_created && !frm.doc.purchase_receipt) frm.set_value('item_creation_group', 'Products');
    },
    refresh(frm) {
        sig_intake_guide(frm);
        if (frm.is_new() || frm.doc.docstatus !== 0) return;
        if (frm.doc.purchase_order_created || frm.doc.purchase_receipt) {
            frm.add_custom_button(__('Open ERP draft'), () => {
                const doctype = frm.doc.purchase_order_created ? 'Purchase Order' : 'Purchase Receipt';
                const name = frm.doc.purchase_order_created || frm.doc.purchase_receipt;
                frappe.set_route('Form', doctype, name);
            });
            const nativeType = frm.doc.purchase_order_created ? 'Purchase Order' : 'Purchase Receipt';
            if (frm.doc.status !== 'Submitted' && frappe.model.can_submit(nativeType)) {
                frm.add_custom_button(__('Submit linked draft'), () => sig_intake_submit(frm));
            }
            return;
        }
        frm.add_custom_button(__('Add supplier'), () => {
            frappe.prompt([
                {fieldname:'supplier_name', fieldtype:'Data', label:__('Supplier name'), reqd:1},
                {fieldname:'supplier_group', fieldtype:'Link', options:'Supplier Group', label:__('Supplier group'), default:'Local', reqd:1},
                {fieldname:'supplier_type', fieldtype:'Select', options:'Company\nIndividual', label:__('Supplier type'), default:'Company', reqd:1},
                {fieldname:'tax_id', fieldtype:'Data', label:__('VAT number')}
            ], values => frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.create_supplier',
                args:{intake_name:frm.doc.name, ...values}}).then(() => frm.reload_doc()), __('Create supplier'), __('Create'));
        }, __('Actions'));
        if (frm.doc.intake_type === 'Item Request') {
            frm.add_custom_button(__('Open native Item form'), () => frappe.new_doc('Item'));
            return;
        }
        if (!['Purchase Order', 'Receipt Against PO', 'Receipt Without PO'].includes(frm.doc.intake_type)) return;
        frm.add_custom_button(__('Review and create'), () => sig_intake_review(frm));
        if (frm.doc.intake_type === 'Receipt Against PO') {
            frm.add_custom_button(__('Add PO receipt line'), () => {
                const dialog = new frappe.ui.Dialog({title: __('Select open Purchase Order line'), fields:[
                    {fieldtype:'Link',fieldname:'purchase_order',label:__('Purchase Order'),options:'Purchase Order',reqd:1},
                    {fieldtype:'HTML',fieldname:'lines'}
                ], primary_action_label:__('Load open lines'), primary_action(values) {
                    frappe.call({method:'sig_warehouse.sig_warehouse.warehouse_intake.open_purchase_order_lines',
                        args:{supplier:frm.doc.supplier,purchase_order:values.purchase_order}
                    }).then(r => {
                        const candidates = r.message || [];
                        const html = candidates.map((line,index) => `<button type="button" class="btn btn-default btn-xs" data-line="${index}">${frappe.utils.escape_html(line.purchase_order)} · ${frappe.utils.escape_html(line.item_code)} · ${frappe.utils.escape_html(String(line.remaining_qty))} ${frappe.utils.escape_html(line.uom || '')}</button>`).join('<br>') || __('No open lines are available to this user.');
                        dialog.fields_dict.lines.$wrapper.html(html);
                        dialog.fields_dict.lines.$wrapper.find('[data-line]').on('click', function() {
                            const line = candidates[Number($(this).data('line'))];
                            frm.set_value('purchase_order', line.purchase_order);
                            frm.set_value('supplier', line.supplier);
                            frm.set_value('company', line.company);
                            const row = frm.add_child('lines');
                            row.source_line_no = frm.doc.lines.length;
                            row.item_code = line.item_code; row.item_name = line.item_name;
                            row.description = line.item_name; row.source_text = line.purchase_order;
                            row.uom = line.uom; row.rate = line.rate; row.warehouse = line.warehouse;
                            row.purchase_order_item = line.purchase_order_item; row.qty = line.remaining_qty;
                            row.match_status = 'Matched';
                            frm.refresh_field('lines'); dialog.hide();
                        });
                    });
                }});
                dialog.show();
            }, __('Actions'));
        }
        frm.add_custom_button(__('Find existing items'), () => sig_intake_find_items(frm));
    }
});
