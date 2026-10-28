frappe.pages['hr-attendance'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Attendance'), single_column: true});
    const root = $('<div class="sig-att"></div>').appendTo(page.main);
    const esc = frappe.utils.escape_html;
    let rows = [], chosen = null, filter = '';
    root.html(`<div class="sig-att-hero"><small>SIG HR</small><h2>${__('Attendance')}</h2><p>${__('Daily sign-ins, sign-outs and attendance history')}</p><button class="btn btn-default sig-att-export">${__('Export CSV')}</button></div>
      <div class="sig-att-controls"><label>${__('Date')}<input class="form-control sig-att-date" type="date"></label><button class="btn btn-default sig-att-today">${__('Today')}</button><button class="btn btn-default sig-att-yesterday">${__('Yesterday')}</button><label>${__('Employee')}<input class="form-control sig-att-search" placeholder="${__('Search employee')}"></label></div>
      <div class="sig-att-tiles"></div><div class="sig-att-layout"><div class="sig-att-card"><div class="sig-att-head"><b>${__('Attendance')}</b><span class="sig-att-count"></span></div><div class="sig-att-table"></div></div><aside class="sig-att-card sig-att-detail"></aside></div>`);
    const date = root.find('.sig-att-date').val(frappe.datetime.get_today());
    const time = v => v ? esc(String(v).slice(11,16)) : '—';
    function render() {
        const q = root.find('.sig-att-search').val().toLowerCase();
        const visible = rows.filter(r => (!filter || r.status === filter) && (r.employee_name || '').toLowerCase().includes(q));
        const items = [['', __('All'), rows.length], ['Signed in', __('Signed in'), rows.filter(r=>r.status==='Signed in').length], ['Signed out', __('Signed out'), rows.filter(r=>r.status==='Signed out').length], ['No sign-in', __('No sign-in'), rows.filter(r=>r.status==='No sign-in').length], ['Needs review', __('Needs review'), rows.filter(r=>r.status==='Needs review').length]];
        root.find('.sig-att-tiles').html(items.map(x=>`<button class="sig-att-tile ${filter===x[0]?'active':''}" data-filter="${esc(x[0])}"><strong>${x[2]}</strong><span>${x[1]}</span></button>`).join(''));
        root.find('.sig-att-count').text(__('Showing {0}', [visible.length]));
        root.find('.sig-att-table').html(`<table class="table"><thead><tr><th>${__('Employee')}</th><th>${__('In')}</th><th>${__('Out')}</th><th>${__('Status')}</th></tr></thead><tbody>${visible.map(r=>`<tr data-employee="${esc(r.employee)}"><td><b>${esc(r.employee_name)}</b><small>${esc(r.department || '')}</small></td><td>${time(r.first_in)}</td><td>${time(r.last_out)}</td><td><span class="sig-att-status">${__(r.status)}</span></td></tr>`).join('')}</tbody></table>`);
    }
    function detail(r) {
        chosen = r;
        root.find('.sig-att-detail').html(`<div class="sig-att-head"><b>${__('Employee details')}</b></div><div class="sig-att-detail-body"><h4>${esc(r.employee_name)}</h4><p>${esc(r.department || '')}</p><h5>${__('Activity')}</h5>${r.events.map(e=>`<div class="sig-att-event"><b>${esc(e.log_type || '—')} · ${time(e.time)}</b></div>`).join('') || __('No events recorded for this day.')}<hr><b>${__('Attendance history')}</b><div class="sig-att-range"><input type="date" class="form-control sig-att-from"><input type="date" class="form-control sig-att-to"><button class="btn btn-default sig-att-history">${__('View')}</button></div><div class="sig-att-history-results"></div></div>`);
        root.find('.sig-att-from').val(frappe.datetime.add_days(date.val(), -30)); root.find('.sig-att-to').val(date.val());
    }
    function load() { frappe.call({method:'sig_warehouse.sig_hr.attendance_dashboard.get_day', args:{date:date.val()}, callback:r=>{rows=r.message || []; filter=''; chosen=null; render(); root.find('.sig-att-detail').html(`<div class="sig-att-head"><b>${__('Employee details')}</b></div><div class="sig-att-detail-body">${__('Select an employee to view their activity and history.')}</div>`);}}); }
    root.on('click','.sig-att-tile',function(){filter=$(this).attr('data-filter');render();});
    root.on('click','tr[data-employee]',function(){const r=rows.find(x=>x.employee===$(this).attr('data-employee'));if(r) detail(r);});
    root.on('click','.sig-att-history',function(){frappe.call({method:'sig_warehouse.sig_hr.attendance_dashboard.get_history',args:{employee:chosen.employee,from_date:root.find('.sig-att-from').val(),to_date:root.find('.sig-att-to').val()},callback:r=>root.find('.sig-att-history-results').html((r.message||[]).map(e=>`<div class="sig-att-event">${esc(String(e.time))} · ${esc(e.log_type||'—')}</div>`).join('') || __('No records in this range.'))});});
    root.find('.sig-att-search').on('input',render); date.on('change',load);
    root.find('.sig-att-today').on('click',()=>{date.val(frappe.datetime.get_today());load();});
    root.find('.sig-att-yesterday').on('click',()=>{date.val(frappe.datetime.add_days(frappe.datetime.get_today(),-1));load();});
    root.find('.sig-att-export').on('click',()=>window.open('/api/method/sig_warehouse.sig_hr.attendance_dashboard.export_day?date='+encodeURIComponent(date.val())));
    load();
};
