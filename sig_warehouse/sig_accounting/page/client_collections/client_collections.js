frappe.pages['client-collections'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __('Client Collections'), single_column: true});
  page.cc_start = 0;
  page.cc_limit = 100;
  page.main.html(`
    <div class="container-fluid">
      <div class="row">
        <div class="col-sm-8"><p class="text-muted">${__('Outstanding balances come from submitted Sales Invoices. Save a reminder draft, review it, then send it explicitly.')}</p></div>
        <div class="col-sm-4"><input class="form-control" id="cc-search" placeholder="${__('Search customer or invoice')}"></div>
      </div>
      <h4>${__('Open Invoices')}</h4><div id="cc-table" class="margin-top"></div>
      <hr><div class="row"><div class="col-sm-9"><h4>${__('Saved Reminder Drafts')}</h4></div><div class="col-sm-3 text-right"><button class="btn btn-default" id="cc-refresh-drafts">${__('Refresh drafts')}</button></div></div>
      <div id="cc-drafts" class="margin-top"></div>
    </div>`);

  function invoice_table(rows) {
    const body = rows.map(r => `<tr>
      <td><input type="checkbox" class="cc-select" value="${frappe.utils.escape_html(r.name)}"></td>
      <td><a href="/app/sales-invoice/${encodeURIComponent(r.name)}">${frappe.utils.escape_html(r.customer_name || r.customer)}</a><small class="text-muted"><br>${frappe.utils.escape_html(r.name)}</small></td>
      <td>${frappe.utils.escape_html(r.due_date || '—')}</td>
      <td>${r.age_days === null ? '—' : (r.age_days > 0 ? `${r.age_days} ${__('days overdue')}` : __('Not due'))}</td>
      <td class="text-right">${format_currency(r.outstanding_amount, r.currency)}</td>
      <td>${frappe.utils.escape_html(r.collection_status)}</td>
    </tr>`).join('');
    $('#cc-table').html(`<div class="table-responsive"><table class="table table-bordered">
      <thead><tr><th></th><th>${__('Customer / Invoice')}</th><th>${__('Due date')}</th><th>${__('Age')}</th><th class="text-right">${__('Outstanding')}</th><th>${__('Status')}</th></tr></thead>
      <tbody>${body || `<tr><td colspan="6">${__('No open submitted invoices on this page.')}</td></tr>`}</tbody>
    </table></div>
    <button class="btn btn-primary" id="cc-create-draft">${__('Create reminder draft')}</button>
    <span class="pull-right"><button class="btn btn-default" id="cc-prev" ${page.cc_start ? '' : 'disabled'}>${__('Previous')}</button> <button class="btn btn-default" id="cc-next" ${page.cc_has_more ? '' : 'disabled'}>${__('Next')}</button></span>
    <p class="text-muted">${__('Rows')} ${page.cc_start + 1}–${page.cc_start + rows.length} · ${__('100 per page')}</p>`);
    $('#cc-create-draft').on('click', create_draft);
    $('#cc-prev').on('click', () => { page.cc_start = Math.max(0, page.cc_start - page.cc_limit); refresh_invoices(); });
    $('#cc-next').on('click', () => { page.cc_start += page.cc_limit; refresh_invoices(); });
  }

  function open_draft(name) {
    frappe.set_route('Form', 'SIG Client Collection Draft', name);
  }

  function refresh_drafts() {
    frappe.call('sig_warehouse.client_collections.get_drafts', {start: 0, limit: 100}).then(r => {
      const rows = (r.message || {}).rows || [];
      const body = rows.map(d => {
        const can_send = ['Draft', 'Partially Sent', 'Failed'].includes(d.status);
        return `<tr>
          <td><a href="#" class="cc-open" data-name="${frappe.utils.escape_html(d.name)}">${frappe.utils.escape_html(d.name)}</a></td>
          <td>${frappe.utils.escape_html(d.customer)}</td>
          <td>${frappe.utils.escape_html(d.recipient_whatsapp || d.recipient_email || '—')}</td>
          <td>${frappe.utils.escape_html(d.channel)}</td>
          <td class="text-right">${format_currency(d.total_outstanding, d.currency)}</td>
          <td>${frappe.utils.escape_html(d.status)}</td>
          <td><button class="btn btn-xs btn-default cc-open" data-name="${frappe.utils.escape_html(d.name)}">${__('Open')}</button> ${can_send ? `<button class="btn btn-xs btn-primary cc-send" data-name="${frappe.utils.escape_html(d.name)}">${__('Send')}</button>` : ''}</td>
        </tr>`;
      }).join('');
      $('#cc-drafts').html(`<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>${__('Draft')}</th><th>${__('Customer')}</th><th>${__('Recipient')}</th><th>${__('Channel')}</th><th class="text-right">${__('Outstanding')}</th><th>${__('Status')}</th><th></th></tr></thead><tbody>${body || `<tr><td colspan="7">${__('No saved reminder drafts yet.')}</td></tr>`}</tbody></table></div>`);
      $('.cc-open').on('click', function(e) { e.preventDefault(); open_draft($(this).data('name')); });
      $('.cc-send').on('click', function() { confirm_send($(this).data('name')); });
    });
  }

  function confirm_send(name) {
    frappe.call('frappe.client.get', {doctype: 'SIG Client Collection Draft', name}).then(r => {
      const d = r.message || {};
      const to = d.channel === 'Email' ? d.recipient_email : (d.channel === 'WhatsApp + Email' ? `${d.recipient_whatsapp} / ${d.recipient_email}` : d.recipient_whatsapp);
      frappe.confirm(
        __('Send this reminder and invoice PDF copies to {0} using {1}?', [frappe.utils.escape_html(to), frappe.utils.escape_html(d.channel)]),
        () => frappe.call('sig_warehouse.client_collections.send_draft', {name}).then(result => {
          const status = (result.message || {}).status || __('Unknown');
          frappe.msgprint({title: __('Delivery status'), message: __('Provider status: {0}. See the draft delivery history for each message and attachment.', [frappe.utils.escape_html(status)])});
          refresh_drafts();
        })
      );
    });
  }

  function create_draft() {
    const names = $('.cc-select:checked').map((_, el) => el.value).get();
    if (!names.length) return frappe.msgprint(__('Select at least one invoice.'));
    const d = new frappe.ui.Dialog({
      title: __('Create client payment reminder draft'),
      fields: [
        {fieldtype: 'Select', fieldname: 'channel', label: __('Delivery channel'), options: 'WhatsApp\nEmail\nWhatsApp + Email', default: 'WhatsApp', reqd: 1},
        {fieldtype: 'Data', fieldname: 'send_to', label: __('Send To number (country code required)'), description: __('Enter the destination manually; no number is selected from the customer record.')},
        {fieldtype: 'Data', fieldname: 'send_to_email', label: __('Send To email')},
        {fieldtype: 'Select', fieldname: 'letter_type', label: __('Letter type'), options: 'Invoice Delivery\nFriendly Reminder\nOverdue Reminder', default: 'Overdue Reminder', reqd: 1},
        {fieldtype: 'Select', fieldname: 'language', label: __('Language'), options: 'English\nArabic\nBilingual', default: 'English', reqd: 1}
      ],
      primary_action_label: __('Save draft'),
      primary_action: values => {
        frappe.call('sig_warehouse.client_collections.create_draft', {
          invoice_names: JSON.stringify(names), send_to: values.send_to, send_to_email: values.send_to_email,
          channel: values.channel, letter_type: values.letter_type, language: values.language
        }).then(r => {
          d.hide();
          const draft = r.message || {};
          frappe.show_alert({message: __('Saved reminder draft {0}', [draft.name]), indicator: 'green'});
          refresh_drafts();
          open_draft(draft.name);
        });
      }
    });
    d.show();
  }

  function refresh_invoices() {
    frappe.call('sig_warehouse.client_collections.get_open_invoices', {start: page.cc_start, limit: page.cc_limit}).then(r => {
      const data = r.message || {};
      page.rows = data.rows || [];
      page.cc_has_more = data.has_more;
      invoice_table(page.rows);
    });
  }

  $('#cc-search').on('input', function() {
    const q = this.value.toLowerCase();
    invoice_table((page.rows || []).filter(r => `${r.customer_name || ''} ${r.customer || ''} ${r.name || ''}`.toLowerCase().includes(q)));
  });
  $('#cc-refresh-drafts').on('click', refresh_drafts);
  refresh_invoices();
  refresh_drafts();
};
