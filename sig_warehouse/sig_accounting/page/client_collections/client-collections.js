frappe.pages['client-collections'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __('Client Collections'), single_column: true});
  page.cc_start = 0;
  page.cc_limit = 100;
  $('<div class="container-fluid"><div class="row"><div class="col-sm-8"><p class="text-muted">Submitted customer invoices with balances from ERP. Use the invoice selection to prepare a manually addressed reminder.</p></div><div class="col-sm-4"><input class="form-control" id="cc-search" placeholder="Search customer or invoice"></div></div><div id="cc-table" class="margin-top"></div></div>').appendTo(page.main);
  function render(rows) {
    const body = rows.map(r => `<tr><td><input type="checkbox" class="cc-select" value="${frappe.utils.escape_html(r.name)}"></td><td><a href="/app/sales-invoice/${encodeURIComponent(r.name)}">${frappe.utils.escape_html(r.customer_name || r.customer)}</a><small class="text-muted"><br>${frappe.utils.escape_html(r.name)}</small></td><td>${frappe.utils.escape_html(r.due_date || '—')}</td><td>${r.age_days === null ? '—' : (r.age_days > 0 ? r.age_days + ' days overdue' : 'Not due')}</td><td class="text-right">${format_currency(r.outstanding_amount, r.currency)}</td><td>${frappe.utils.escape_html(r.collection_status)}</td></tr>`).join('');
    $('#cc-table').html(`<div class="table-responsive"><table class="table table-bordered"><thead><tr><th></th><th>Customer / Invoice</th><th>Due date</th><th>Age</th><th class="text-right">Outstanding</th><th>Status</th></tr></thead><tbody>${body || '<tr><td colspan="6">No open submitted invoices on this page.</td></tr>'}</tbody></table></div><button class="btn btn-primary" id="cc-preview">Prepare WhatsApp reminder</button> <span class="pull-right"><button class="btn btn-default" id="cc-prev" ${page.cc_start ? '' : 'disabled'}>Previous</button> <button class="btn btn-default" id="cc-next" ${page.cc_has_more ? '' : 'disabled'}>Next</button></span><p class="text-muted">${__('Rows')} ${page.cc_start + 1}–${page.cc_start + rows.length} · ${__('100 per page')}</p>`);
    $('#cc-preview').on('click', () => preview(rows));
    $('#cc-prev').on('click', () => { page.cc_start = Math.max(0, page.cc_start - page.cc_limit); refresh(); });
    $('#cc-next').on('click', () => { page.cc_start += page.cc_limit; refresh(); });
  }
  function refresh() { frappe.call('sig_warehouse.client_collections.get_open_invoices', {start: page.cc_start, limit: page.cc_limit}).then(r => { const data = r.message || {}; page.rows = data.rows || []; page.cc_has_more = data.has_more; render(page.rows); }); }
  function preview(rows) {
    const names = $('.cc-select:checked').map((_, e) => e.value).get();
    if (!names.length) return frappe.msgprint(__('Select at least one invoice.'));
    const d = new frappe.ui.Dialog({title: __('Prepare client reminder'), fields:[
      {fieldtype:'Data',fieldname:'send_to',label:__('Send To number (include country code)'),reqd:1},
      {fieldtype:'Select',fieldname:'letter_type',label:__('Letter type'),options:'Invoice Delivery\nFriendly Reminder\nOverdue Reminder',default:'Overdue Reminder'},
      {fieldtype:'Select',fieldname:'language',label:__('Language'),options:'English\nArabic\nBilingual',default:'English'}
    ], primary_action_label:__('Preview'), primary_action:async values=>{
      const p=await frappe.call('sig_warehouse.client_collections.prepare_whatsapp',{invoice_names:JSON.stringify(names),send_to:values.send_to,letter_type:values.letter_type,language:values.language});
      d.hide(); frappe.msgprint({title:__('Reminder preview'),message:`<p>${__('Customer')}: ${frappe.utils.escape_html(p.message.customer)}</p><p>${__('Send To')}: ${frappe.utils.escape_html(p.message.recipient)}</p><pre>${frappe.utils.escape_html(p.message.message)}</pre><p class="text-muted">${frappe.utils.escape_html(p.message.note)}</p>`});
    }}); d.show();
  }
  $('#cc-search').on('input', function(){const q=this.value.toLowerCase();render((page.rows||[]).filter(r=>(r.customer_name+' '+r.customer+' '+r.name).toLowerCase().includes(q)));});
  refresh();
};
