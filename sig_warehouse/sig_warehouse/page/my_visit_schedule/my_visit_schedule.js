frappe.pages['my-visit-schedule'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('My Visit Schedule'), single_column: true});
    const root = $('<div class="sig-my-visits"></div>').appendTo(page.main);
    const esc = (v) => frappe.utils.escape_html(String(v || ''));
    const dt = (v) => {
        if (!v) return '—';
        const p = String(v).slice(0, 19).split(/[- :]/);
        return p.length < 5 ? String(v).slice(0, 16) : `${p[2]}-${p[1]}-${p[0].slice(-2)} ${p[3]}:${p[4]}`;
    };
    root.html(`<p class="text-muted">${__('Visits recorded for your employee account.')}</p><div class="sig-my-visits-table"></div>`);
    frappe.call({method: 'sig_warehouse.sig_warehouse.site_visits.get_my_visit_schedule'}).then((r) => {
        const data = r.message || {};
        const rows = data.rows || [];
        if (!data.employee) {
            root.find('.sig-my-visits-table').html(`<div class="text-muted">${__('No active Employee record is linked to your login.')}</div>`);
        } else if (!rows.length) {
            root.find('.sig-my-visits-table').html(`<div class="text-muted">${__('No visits found.')}</div>`);
        } else {
            const body = rows.map((row) => `<tr>
                <td><b>${esc(row.site)}</b></td><td>${dt(row.start_at)}${row.end_at ? `<br><span class="text-muted">${__('End')}: ${dt(row.end_at)}</span>` : ''}</td>
                <td>${esc(row.activity_code)}</td><td>${row.hours == null ? '—' : esc(row.hours) + 'h'}</td>
                <td>${esc(row.photo_count)} ${__('photos')}</td><td>${esc(row.status)}</td>
            </tr>`).join('');
            root.find('.sig-my-visits-table').html(`<div class="table-responsive"><table class="table table-bordered">
                <thead><tr><th>${__('Site')}</th><th>${__('Date / Time')}</th><th>${__('Type')}</th><th>${__('Duration')}</th><th>${__('Photos')}</th><th>${__('Status')}</th></tr></thead>
                <tbody>${body}</tbody></table></div>`);
        }
    }).catch(() => root.find('.sig-my-visits-table').html(`<div class="text-muted">${__('Could not load your visit schedule.')}</div>`));
};
