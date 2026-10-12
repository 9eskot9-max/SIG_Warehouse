frappe.pages['operations-workbench'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Operations Workbench'), single_column: true});
    page.add_inner_button(__('Material Request Pipeline'), () => frappe.set_route('Workspaces', 'SIG Operations'));
    const root = $('<main class="sig-ops-home"></main>').appendTo(page.main);
    let data = {};
    let filter = 'open';
    let query = '';
    let family = '';
    let selected = new Set();
    let pageNumber = 1;
    const pageSize = 50;
    const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
    const date = (v) => v ? frappe.datetime.str_to_user(String(v).slice(0, 10)) : '—';
    const link = (doctype, name) => name ? `<a href="#" data-doctype="${esc(doctype)}" data-name="${esc(name)}">${esc(name)}</a>` : '—';
    const cycles = () => (data.cycles || []).filter((r) => !family || r.family === family);

    function render() {
        const summary = data.summary || {};
        const all = cycles();
        const filteredRows = all.filter((r) => {
            if (filter === 'open' && r.terminal) return false;
            if (filter === 'review' && !r.needs_review) return false;
            if (filter === 'closed' && !r.terminal) return false;
            if (filter.startsWith('stage:') && r.stage !== filter.slice(6)) return false;
            const haystack = [r.site, r.name, r.project, r.project_id, r.stage, r.family].join(' ').toLowerCase();
            return !query || haystack.includes(query.toLowerCase());
        });
        const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
        pageNumber = Math.min(pageNumber, pageCount);
        const rows = filteredRows.slice((pageNumber - 1) * pageSize, pageNumber * pageSize);
        const rosterRows = Object.entries(data.roster || {}).filter(([key]) => !family || key === family);
        root.attr('dir', frappe.boot.lang === 'ar' ? 'rtl' : 'ltr');
        root.html(`
            <header class="sig-ops-header"><div><div class="sig-ops-eyebrow">${__('SIG Operations')}</div>
                <h1>${__('Operations Workbench')}</h1><p>${__('One view of project delivery, pending evidence, delay review, and cycle closure.')}</p></div>
                <button class="btn btn-default sig-ops-refresh">${__('Refresh')}</button></header>
            <section class="sig-ops-stats">
                <button data-filter="open"><strong>${esc(all.filter((r) => !r.terminal).length)}</strong><span>${__('Open site cycles')}</span></button>
                <button data-filter="review" class="is-warning"><strong>${esc(all.filter((r) => r.needs_review).length)}</strong><span>${__('Pending work to review')}</span></button>
                <button data-filter="closed"><strong>${esc(all.filter((r) => r.terminal).length)}</strong><span>${__('Closed cycles')}</span></button>
                <button class="is-neutral"><strong>${esc((data.todos || []).length)}${data.complete && !data.complete.todos ? '+' : ''}</strong><span>${__('My allocated ToDos')}</span></button>
            </section>
            <section class="sig-ops-stage"><div class="sig-ops-stage-title"><h2>${__('Delivery stages')}</h2><span>${__('Cycle status follows recorded evidence; parallel work can progress independently.')}</span></div>
                <div class="sig-ops-stage-flow">
                    ${['Scope & readiness', 'Preparation', 'Handover', 'Completion documents', 'Closed'].map((stage) => {
                        const count = all.filter((r) => r.stage === stage).length;
                        return `<button data-stage="${esc(stage)}" class="${filter === 'stage:' + stage ? 'active' : ''}"><b>${esc(count)}</b><span>${esc(stage)}</span>${stage === 'Handover' ? `<small>${__('Tags · Photos · As-Built BOQ (parallel)')}</small>` : ''}</button>`;
                    }).join('<i class="fa fa-angle-right" aria-hidden="true"></i>')}
                </div>
            </section>
            <div class="sig-ops-layout">
                <section class="sig-ops-panel sig-ops-main"><div class="sig-ops-panel-head"><div><h2>${__('Work and site cycles')}</h2><p>${__('Delay and aging flag existing work for review. They do not create duplicate tasks.')}</p></div>
                    <button class="btn btn-primary sig-ops-close" ${data.can_close_cycles ? '' : 'disabled'}>${__('Close selected cycles')}</button></div>
                    <div class="sig-ops-toolbar"><select class="sig-ops-family"><option value="">${__('All project scopes')}</option>${['Capex','Incident','Colocation'].map((x) => `<option ${family === x ? 'selected' : ''}>${x}</option>`).join('')}</select>
                        <input class="form-control sig-ops-search" placeholder="${__('Search site, project, or cycle')}" value="${esc(query)}">
                        <nav>${[['open',__('Open')],['review',__('Review')],['closed',__('Closed')]].map(([key,label]) => `<button data-filter="${key}" class="${filter === key ? 'active' : ''}">${label}</button>`).join('')}</nav></div>
                    <div class="sig-ops-selection"><label><input type="checkbox" class="sig-ops-select-visible"> ${__('Select this page (up to 50)')}</label><span>${esc(selected.size)} ${__('selected')}</span><small>${filteredRows.length ? (pageNumber - 1) * pageSize + 1 : 0}–${Math.min(pageNumber * pageSize, filteredRows.length)} ${__('of')} ${filteredRows.length}${data.complete && !data.complete.cycles ? ` · ${__('partial read')}` : ''}</small></div>
                    ${rows.length ? `<div class="sig-ops-table-wrap"><table class="sig-ops-table"><thead><tr><th></th><th>${__('Site / cycle')}</th><th>${__('Project')}</th><th>${__('Stage / pending evidence')}</th><th>${__('Owners')}</th><th>${__('Signal')}</th><th>${__('Due')}</th></tr></thead><tbody>${rows.map((r) => {
                        const work = (r.work || []).map((w) => {
                            const role = w.owner_role === 'pm' ? __('PM') : __('Coordinator');
                            const names = (w.owners || []).map(esc).join(', ');
                            return `${esc(w.label)} — ${esc(role)}${names ? `: ${names}` : ''}`;
                        }).join('<br>') || __('No pending evidence task derived');
                        const signal = r.terminal ? __('Closed') : r.needs_review ? [r.is_delayed && __('Delayed'), r.is_aged && __('Aged'), r.past_due && __('Past due')].filter(Boolean).join(' · ') : __('On track');
                        const people = r.people ? `<small><b>${__('PM')}:</b> ${(r.people.pm || []).map(esc).join(', ') || '—'}<br><b>${__('Coordinator')}:</b> ${(r.people.co || []).map(esc).join(', ') || '—'}</small>` : '—';
                        return `<tr data-cycle="${esc(r.name)}" class="${selected.has(r.name) ? 'selected' : ''}"><td><input type="checkbox" class="sig-ops-cycle-check" value="${esc(r.name)}" ${selected.has(r.name) ? 'checked' : ''} ${r.terminal ? 'disabled' : ''}></td>
                            <td><b>${link('SIG Site Cycle', r.name)}</b><small>${esc(r.site)}</small></td><td>${r.project ? `<b>${esc(r.project)}</b>` : '—'}<small>${esc(r.family)}</small></td>
                            <td><b>${esc(r.stage)}</b><small>${work}</small></td><td>${people}</td><td><span class="${r.needs_review ? 'sig-ops-badge warning' : r.terminal ? 'sig-ops-badge closed' : 'sig-ops-badge'}">${esc(signal)}</span>${r.delay_reason ? `<small>${esc(r.delay_reason)}${r.delay_note ? ` · ${esc(r.delay_note)}` : ''}</small>` : ''}</td><td>${date(r.stage_due_on)}</td></tr>`;
                    }).join('')}</tbody></table></div>${pageCount > 1 ? `<div class="sig-ops-pagination"><button class="btn btn-default sig-ops-prev" ${pageNumber <= 1 ? 'disabled' : ''}>${__('Previous')}</button><span>${__('Page {0} of {1}', [pageNumber, pageCount])}</span><button class="btn btn-default sig-ops-next" ${pageNumber >= pageCount ? 'disabled' : ''}>${__('Next')}</button></div>` : ''}` : `<div class="sig-ops-empty">${__('No matching cycles are visible to your ERP role.')}</div>`}
                    ${data.can_close_cycles ? `<div class="sig-ops-footnote">${__('Cycle closure is explicit and recorded with a reason. Evidence milestones remain in the cycle history.')}</div>` : ''}
                </section>
                <aside class="sig-ops-side">
                    <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('My ToDos')}</h2><p>${__('Personal follow-ups assigned in ERPNext.')}</p></div></div>
                        ${(data.todos || []).length ? `<div class="sig-ops-todos">${data.todos.map((t) => `<label><input type="checkbox" class="sig-ops-todo-check" value="${esc(t.name)}"><span><b>${esc(t.description || __('Follow-up'))}</b><small>${esc(t.reference_type || '')} ${t.reference_name ? `· ${link(t.reference_type, t.reference_name)}` : ''} · ${date(t.date)}</small></span></label>`).join('')}</div><button class="btn btn-default sig-ops-complete-todos">${__('Complete selected ToDos')}</button>` : `<div class="sig-ops-empty">${__('No open ToDos allocated to you.')}</div>`}
                        <button class="btn btn-default sig-ops-new-todo">${__('Create a follow-up')}</button>
                    </section>
                    <section class="sig-ops-panel"><div class="sig-ops-panel-head"><div><h2>${__('Project responsibilities')}</h2><p>${__('Display ownership by project scope; site cycles remain team work.')}</p></div></div>
                        ${rosterRows.map(([scope, roles]) => `<div class="sig-ops-roster"><b>${esc(scope)}</b><div><strong>${__('PM')}</strong>: ${roles.pm.map(esc).join(', ') || '—'}</div><div><strong>${__('Coordinator')}</strong>: ${roles.co.map(esc).join(', ') || '—'}</div></div>`).join('') || `<div class="sig-ops-empty">${__('Choose a scope to see its project team.')}</div>`}
                    </section>
                </aside>
            </div>`);
        root.find('button[data-filter]').on('click', function () { filter = $(this).data('filter'); pageNumber = 1; selected.clear(); render(); });
        root.find('[data-stage]').on('click', function () { filter = 'stage:' + $(this).data('stage'); pageNumber = 1; selected.clear(); render(); });
        root.find('.sig-ops-family').on('change', function () { family = this.value; pageNumber = 1; selected.clear(); render(); });
        root.find('.sig-ops-search').on('change', function () { query = this.value.trim(); pageNumber = 1; selected.clear(); render(); });
        root.find('.sig-ops-refresh').on('click', load);
        root.find('.sig-ops-cycle-check').on('change', function () {
            if (this.checked && !selected.has(this.value) && selected.size >= 50) {
                this.checked = false;
                return frappe.msgprint(__('Select up to 50 cycles per bulk closure.'));
            }
            this.checked ? selected.add(this.value) : selected.delete(this.value); render();
        });
        root.find('.sig-ops-select-visible').on('change', function () {
            const visible = rows.filter((r) => !r.terminal);
            if (this.checked) {
                const available = Math.max(0, 50 - selected.size);
                const unselected = visible.filter((r) => !selected.has(r.name));
                unselected.slice(0, available).forEach((r) => selected.add(r.name));
                if (unselected.length > available) frappe.show_alert({message:__('Selected up to 50 cycles. Clear some to select more.'), indicator:'orange'});
            } else visible.forEach((r) => selected.delete(r.name));
            render();
        });
        root.find('.sig-ops-prev').on('click', () => { pageNumber = Math.max(1, pageNumber - 1); render(); });
        root.find('.sig-ops-next').on('click', () => { pageNumber += 1; render(); });
        root.find('a[data-doctype]').on('click', function (e) { e.preventDefault(); frappe.set_route('Form', $(this).data('doctype'), $(this).data('name')); });
        root.find('.sig-ops-close').on('click', closeSelected);
        root.find('.sig-ops-complete-todos').on('click', completeTodos);
        root.find('.sig-ops-new-todo').on('click', () => frappe.new_doc('ToDo'));
    }

    function closeSelected() {
        const names = Array.from(selected);
        if (!names.length) return frappe.msgprint(__('Select one or more open site cycles first.'));
        frappe.prompt([{fieldname:'reason', label:__('Closure reason'), fieldtype:'Small Text', reqd:1}], (values) => {
            frappe.call({method:'sig_warehouse.sig_warehouse.operations_workbench.close_cycles', args:{cycles:names, reason:values.reason}})
                .then((r) => { selected.clear(); frappe.show_alert({message:__('Closed {0} site cycles.', [((r.message || {}).closed || []).length]), indicator:'green'}); load(); });
        }, __('Close selected site cycles'), __('Close cycles'));
    }

    function completeTodos() {
        const names = root.find('.sig-ops-todo-check:checked').map((_, e) => e.value).get();
        if (!names.length) return frappe.msgprint(__('Select one or more of your ToDos first.'));
        frappe.confirm(__('Mark {0} selected ToDos complete?', [names.length]), () => {
            Promise.all(names.map((name) => frappe.call('frappe.client.set_value', {doctype:'ToDo', name, fieldname:'status', value:'Closed'})))
                .then(() => { frappe.show_alert({message:__('Selected ToDos completed.'), indicator:'green'}); load(); });
        });
    }

    function load() {
        root.html(`<div class="sig-ops-loading">${__('Loading operations…')}</div>`);
        frappe.call({method:'sig_warehouse.sig_warehouse.operations_workbench.get_overview'})
            .then((r) => { data = r.message || {}; render(); })
            .catch(() => root.html(`<div class="sig-ops-error">${__('Operations data could not be loaded. Check your ERP access and refresh.')}</div>`));
    }
    load();
};

