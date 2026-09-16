frappe.ui.form.on('Material Request', {
    refresh(frm) {
        if (frm.doc.material_request_type !== 'Material Issue') return;
        if (frm.doc.docstatus !== 1) return;
        if (!['PENDING', 'PARTIAL'].includes(frm.doc.custom_dispatch_stage)) return;
        if (frm.__sig_dispatch_button_added) return;
        frm.__sig_dispatch_button_added = true;
        // Standalone primary button (not nested under "Actions") so it is
        // immediately visible on the page - a separate Client Script
        // ("SIG MR Issue Button") tried to add this as a shortcut by
        // simulating a click on the old dropdown item via a data-label
        // selector that Frappe's dropdown markup doesn't actually expose,
        // so it silently did nothing. Consolidated into this one real
        // button instead of maintaining two.
        frm.add_custom_button(__('Issue'), () => sig_open_dispatch_dialog(frm));
    }
});

// Kanban-only enhancements below (card-count badges, quick search). Not wired
// through frappe.listview_settings' onload/refresh - Kanban's exact call
// timing into those hooks isn't independently confirmed on this Frappe build
// and there is no desk session available in this project's tooling to watch
// it render, so a router-change watcher (fires on every route, cheap no-op
// guard for anything that isn't this Kanban board) is the safer bet: it does
// not depend on an unverified internal API surface, only on the route and the
// DOM Frappe's own kanban_column.html/kanban_card.html templates produce.
frappe.router.on('change', () => sig_maybe_setup_kanban());
sig_maybe_setup_kanban();

function sig_maybe_setup_kanban() {
    const route = frappe.get_route ? frappe.get_route() : [];
    if (route[0] !== 'List' || route[1] !== 'Material Request' || route[2] !== 'Kanban') return;
    sig_wait_for_kanban_board(($board) => {
        sig_setup_kanban_updates($board);
        sig_setup_kanban_search($board);
        sig_setup_kanban_actions($board);
    });
}

function sig_wait_for_kanban_board(callback, attemptsLeft = 40) {
    // Frappe v15's Kanban root wrapper class is '.kanban', not '.kanban-board'
    // (confirmed live on this site's Frappe 15.106.0) - the old selector never
    // matched, so none of the enhancements below ever activated in production.
    const $board = $('.kanban');
    if ($board.length) {
        callback($board);
        return;
    }
    if (attemptsLeft <= 0) return;
    setTimeout(() => sig_wait_for_kanban_board(callback, attemptsLeft - 1), 250);
}

// Each real column carries its group value in data-column-value (confirmed
// live on this site's Frappe 15 Kanban DOM: <div class="kanban-column"
// data-column-value="PENDING">) - the field grouping the board is
// custom_dispatch_stage, so this is that value verbatim. Falls back to the
// title text (case-insensitive) in case a future Frappe version drops the
// attribute, since Kanban Board column labels are otherwise free text.
const SIG_STAGE_COLORS = {
    PENDING: '#94a3b8',
    PARTIAL: '#f59e0b',
    DISPATCHED: '#16a34a',
    CLOSED: '#64748b',
};

function sig_stage_color_for_column($col) {
    const key = ($col.attr('data-column-value') || $col.find('.kanban-title').first().text())
        .trim().toUpperCase();
    return SIG_STAGE_COLORS[key] || null;
}

function sig_setup_kanban_updates($board) {
    const update = () => {
        $board.find('.kanban-column').each(function () {
            const $col = $(this);
            const $cards = $col.find('.kanban-cards .kanban-card-wrapper');
            const count = $cards.filter(':visible').length;
            let $badge = $col.find('.sig-kanban-count');
            if (!$badge.length) {
                $badge = $('<span class="sig-kanban-count badge pull-right" style="font-weight:normal;"></span>');
                $col.find('.kanban-column-header').first().append($badge);
            }
            $badge.text(count);

            const color = sig_stage_color_for_column($col);
            $cards.find('.kanban-card').css('border-left', color ? `4px solid ${color}` : '');
        });
    };
    update();
    if ($board.data('sig-update-observer')) return; // already watching this board instance
    const observer = new MutationObserver(() => update());
    observer.observe($board.get(0), { childList: true, subtree: true });
    $board.data('sig-update-observer', observer);
}

function sig_setup_kanban_search($board) {
    if ($('.sig-kanban-search').length) return; // already inserted for this page
    const $box = $(`<div class="sig-kanban-search" style="margin: 0 15px 10px;">
        <input type="text" class="form-control input-sm" placeholder="${__('Search MR #, site (e.g. 1011, ZMK113)...')}">
    </div>`);
    $board.before($box);
    $box.find('input').on('input', function () {
        const q = $(this).val().trim().toLowerCase();
        $board.find('.kanban-card-wrapper').each(function () {
            const $card = $(this);
            const match = !q || $card.text().toLowerCase().includes(q);
            $card.toggle(match);
        });
        // card visibility changed - refresh the per-column counts to match
        sig_setup_kanban_updates($board);
    });
}

// Per-card action menu, replacing Frappe's built-in assign-avatar icon (CSS-
// hidden below, scoped to this board only) - no assign-to-user workflow is
// needed here; PENDING/PARTIAL/DISPATCHED cards get Dispatch/Return/Cancel
// actions instead, calling the same three backend operations already proven
// from the Material Request form (Dispatch) and the Stock Entry form
// (Return, via sig_declare_disposition) plus the new sig_cancel_mr_lines.
// Not visually verified in this environment (no desk session available to
// render a Kanban board) - built from the confirmed-live DOM structure and
// the same dialog patterns already proven working from their form contexts.
function sig_setup_kanban_actions($board) {
    if (!$('#sig-kanban-hide-assign-style').length) {
        $('<style id="sig-kanban-hide-assign-style">.kanban-board .kanban-assignments { display: none !important; }</style>').appendTo('head');
    }
    $board.find('.kanban-card-wrapper').each(function () {
        const $card = $(this);
        if ($card.find('.sig-kanban-action-btn').length) return;
        const $btn = $(`<span class="sig-kanban-action-btn" title="${__('Actions')}"
            style="position:absolute; top:6px; right:6px; cursor:pointer; opacity:0.6; z-index:2;">
            <svg class="icon icon-sm"><use href="#icon-dot-horizontal"></use></svg>
        </span>`);
        $card.css('position', 'relative');
        $card.find('.kanban-card.content').first().append($btn);
        $btn.on('click', function (e) {
            e.stopPropagation();
            e.preventDefault();
            sig_show_kanban_action_menu($btn, $card.attr('data-name'));
        });
    });
}

function sig_show_kanban_action_menu($anchor, mrNameEncoded) {
    const mrName = decodeURIComponent(mrNameEncoded);
    $('.sig-kanban-action-menu').remove();
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Material Request', name: mrName },
        freeze: true,
        freeze_message: __('Loading...'),
        callback: (r) => {
            const doc = r.message;
            if (!doc) return;
            const stage = doc.custom_dispatch_stage;
            const actions = [];
            if (stage === 'PENDING') {
                actions.push([__('Issue'), () => sig_kanban_dispatch(doc)]);
                actions.push([__('Cancel remaining'), () => sig_kanban_cancel(doc)]);
            } else if (stage === 'PARTIAL') {
                actions.push([__('Issue'), () => sig_kanban_dispatch(doc)]);
                actions.push([__('Return'), () => sig_kanban_return(doc)]);
                actions.push([__('Cancel remaining'), () => sig_kanban_cancel(doc)]);
            } else if (stage === 'DISPATCHED') {
                actions.push([__('Return'), () => sig_kanban_return(doc)]);
            } else {
                frappe.msgprint(__('No actions available for stage {0}.', [stage]));
                return;
            }
            const $menu = $('<div class="sig-kanban-action-menu"></div>').css({
                position: 'absolute', zIndex: 1000, background: 'var(--card-bg, #fff)',
                border: '1px solid var(--border-color, #d1d8dd)', borderRadius: '6px',
                boxShadow: '0 2px 8px rgba(0,0,0,.15)', minWidth: '160px',
            });
            actions.forEach(([label, fn]) => {
                const $item = $('<div class="sig-kanban-action-item"></div>')
                    .css({ padding: '8px 12px', cursor: 'pointer' }).text(label);
                $item.on('click', () => { $menu.remove(); fn(); });
                $item.on('mouseenter', function () { $(this).css('background', 'var(--fg-hover-color, #f4f5f6)'); });
                $item.on('mouseleave', function () { $(this).css('background', ''); });
                $menu.append($item);
            });
            $('body').append($menu);
            const offset = $anchor.offset();
            $menu.css({ top: offset.top + $anchor.outerHeight() + 2, left: offset.left - $menu.outerWidth() + $anchor.outerWidth() });
            setTimeout(() => { $(document).one('click', () => $menu.remove()); }, 0);
        },
    });
}

function sig_kanban_dispatch(doc) {
    sig_open_dispatch_dialog({ doc, reload_doc: () => {} });
}

function sig_kanban_cancel(doc) {
    const openLines = (doc.items || []).filter((it) => (it.custom_qty_remaining || 0) > 0.000001);
    if (!openLines.length) {
        frappe.msgprint(__('No open lines to cancel on this request.'));
        return;
    }
    const rowsHtml = openLines.map((it) => `
        <tr data-mri="${it.name}">
            <td>${frappe.utils.escape_html(it.item_code)}</td>
            <td class="text-right">${it.custom_qty_remaining}</td>
            <td><input type="number" class="form-control input-sm sig-cancel-qty" step="any" min="0"
                max="${it.custom_qty_remaining}" value="${it.custom_qty_remaining}"></td>
        </tr>`).join('');
    const d = new frappe.ui.Dialog({
        title: __('Cancel remaining - {0}', [doc.name]),
        fields: [{
            fieldtype: 'HTML', fieldname: 'lines_html',
            options: `<div class="table-responsive"><table class="table table-bordered">
                <thead><tr><th>${__('Item')}</th><th class="text-right">${__('Remaining')}</th><th>${__('Qty to Cancel')}</th></tr></thead>
                <tbody>${rowsHtml}</tbody></table></div>`,
        }],
        primary_action_label: __('Confirm Cancel'),
        primary_action() {
            const rows = [...d.$wrapper.find('tbody tr')];
            const lines = rows.map((row) => {
                const $row = $(row);
                return { mri: $row.data('mri'), qty: parseFloat($row.find('.sig-cancel-qty').val() || '0') };
            }).filter((l) => l.qty > 0);
            if (!lines.length) {
                frappe.msgprint(__('No lines selected.'));
                return;
            }
            frappe.confirm(
                __('Cancel remaining demand on {0} line(s) of {1}? This cannot be undone from here.', [lines.length, doc.name]),
                () => {
                    const args = { operation_id: sig_gen_operation_id('CANCEL'), mr: doc.name, line_count: lines.length };
                    lines.forEach((l, i) => { args[`mri_${i + 1}`] = l.mri; args[`qty_${i + 1}`] = l.qty; });
                    frappe.call({
                        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_cancel_mr_lines',
                        args, freeze: true, freeze_message: __('Cancelling...'),
                        callback: (r) => {
                            const res = r.message || {};
                            if (res.result === 'created' || res.result === 'duplicate') {
                                frappe.show_alert({ message: __('Cancelled.'), indicator: 'green' });
                                d.hide();
                            } else if (res.result === 'exception' && res.reason === 'CAP_EXCEEDED') {
                                frappe.msgprint({ title: __('Cannot cancel'), indicator: 'red',
                                    message: __('Line {0}: requested {1} exceeds remaining {2}.', [res.line, res.requested, res.remaining]) });
                            } else if (res.result === 'conflict') {
                                frappe.msgprint({ title: __('Conflict'), indicator: 'red', message: __('This attempt changed after the operation ID was generated. Retry.') });
                            } else {
                                frappe.msgprint({ title: __('Failed'), indicator: 'red', message: __('{0}', [JSON.stringify(res)]) });
                            }
                        },
                    });
                }
            );
        },
    });
    d.show();
}

function sig_kanban_return(doc) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'SIG Dispatch Operation',
            filters: { mr: doc.name, op_type: 'DISPATCH', state: 'SUBMITTED' },
            fields: ['stock_entry'],
            limit_page_length: 0,
        },
        freeze: true, freeze_message: __('Finding dispatch...'),
        callback: (r) => {
            const ses = [...new Set((r.message || []).map((x) => x.stock_entry).filter(Boolean))];
            if (!ses.length) {
                frappe.msgprint(__('No dispatch Stock Entry found for {0}.', [doc.name]));
                return;
            }
            if (ses.length > 1) {
                const d = new frappe.ui.Dialog({
                    title: __('Select dispatch to return against'),
                    fields: [{ fieldtype: 'Select', fieldname: 'se', label: __('Stock Entry'), options: ses.join('\n'), reqd: 1 }],
                    primary_action_label: __('Continue'),
                    primary_action() {
                        const se = d.get_value('se');
                        d.hide();
                        sig_open_kanban_return_dialog(se);
                    },
                });
                d.show();
                return;
            }
            sig_open_kanban_return_dialog(ses[0]);
        },
    });
}

function sig_open_kanban_return_dialog(sourceSe) {
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Stock Entry', name: sourceSe },
        freeze: true, freeze_message: __('Loading...'),
        callback: (r) => {
            const se = r.message;
            if (!se) return;
            const openLines = (se.items || []).filter((it) => {
                const returned = it.custom_qty_returned || 0;
                const custody = it.custom_qty_custody || 0;
                const undeclared = it.qty - returned - custody;
                return !it.custom_return_closed && undeclared > 0.000001;
            });
            if (!openLines.length) {
                frappe.msgprint(__('No undeclared lines on {0}.', [sourceSe]));
                return;
            }
            const rowsHtml = openLines.map((it) => {
                const returned = it.custom_qty_returned || 0;
                const custody = it.custom_qty_custody || 0;
                const undeclared = it.qty - returned - custody;
                return `
                    <tr data-sed="${it.name}">
                        <td>${frappe.utils.escape_html(it.item_code)}</td>
                        <td class="text-right">${undeclared}</td>
                        <td><input type="number" class="form-control input-sm sig-return-qty" step="any" min="0" max="${undeclared}" value="${undeclared}"></td>
                    </tr>`;
            }).join('');
            const d = new frappe.ui.Dialog({
                title: __('Return - {0}', [sourceSe]),
                size: 'large',
                fields: [
                    { fieldtype: 'Data', fieldname: 'to_wh', label: __('To Warehouse'), default: openLines[0].s_warehouse, reqd: 1 },
                    { fieldtype: 'Section Break' },
                    {
                        fieldtype: 'HTML', fieldname: 'lines_html',
                        options: `<div class="table-responsive"><table class="table table-bordered">
                            <thead><tr><th>${__('Item')}</th><th class="text-right">${__('Undeclared')}</th><th>${__('Qty to Return')}</th></tr></thead>
                            <tbody>${rowsHtml}</tbody></table></div>`,
                    },
                ],
                primary_action_label: __('Confirm Return'),
                primary_action() {
                    const rows = [...d.$wrapper.find('tbody tr')];
                    const lines = rows.map((row) => {
                        const $row = $(row);
                        return { sed: $row.data('sed'), qty: parseFloat($row.find('.sig-return-qty').val() || '0') };
                    }).filter((l) => l.qty > 0);
                    if (!lines.length) {
                        frappe.msgprint(__('No lines selected.'));
                        return;
                    }
                    const toWh = d.get_value('to_wh');
                    frappe.confirm(
                        __('Return {0} line(s) from {1} to {2}? This submits a Stock Entry immediately.', [lines.length, sourceSe, toWh]),
                        () => {
                            const args = {
                                operation_id: sig_gen_operation_id('RETURN'), action: 'RETURN', source_se: sourceSe,
                                to_wh: toWh, line_count: lines.length,
                            };
                            lines.forEach((l, i) => { args[`sed_${i + 1}`] = l.sed; args[`qty_${i + 1}`] = l.qty; });
                            frappe.call({
                                method: 'sig_warehouse.sig_warehouse.disposition.sig_declare_disposition',
                                args, freeze: true, freeze_message: __('Returning...'),
                                callback: (res2) => {
                                    const res = res2.message || {};
                                    if (res.result === 'created' || res.result === 'duplicate') {
                                        frappe.show_alert({ message: __('Returned.'), indicator: 'green' });
                                        d.hide();
                                    } else if (res.result === 'exception' && res.reason === 'CAP_EXCEEDED') {
                                        frappe.msgprint({ title: __('Cannot return'), indicator: 'red',
                                            message: __('Line {0}: requested {1} exceeds remaining {2}.', [res.line, res.requested, res.remaining]) });
                                    } else if (res.result === 'conflict') {
                                        frappe.msgprint({ title: __('Conflict'), indicator: 'red', message: __('This attempt changed after the operation ID was generated. Retry.') });
                                    } else {
                                        frappe.msgprint({ title: __('Failed'), indicator: 'red', message: __('{0}', [JSON.stringify(res)]) });
                                    }
                                },
                            });
                        }
                    );
                },
            });
            d.show();
        },
    });
}

function sig_gen_operation_id(warehouse) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const safeWh = (warehouse || 'WH').replace(/[^A-Za-z0-9]/g, '').slice(0, 12) || 'WH';
    return `SIG-DISPOP-${safeWh}-${stamp}-${Math.floor(Math.random() * 900 + 100)}`;
}

function sig_open_dispatch_dialog(frm) {
    const openLines = (frm.doc.items || []).filter(it => (it.custom_qty_remaining || 0) > 0.000001);
    if (!openLines.length) {
        frappe.msgprint(__('No open lines to dispatch on this request.'));
        return;
    }
    const fromWarehouse = openLines[0].warehouse;

    frappe.call({
        method: 'check_dn_availability',
        args: {
            from_wh: fromWarehouse,
            line_count: openLines.length,
            ...Object.fromEntries(openLines.flatMap((it, i) => [
                [`code_${i + 1}`, it.item_code],
                [`qty_${i + 1}`, it.custom_qty_remaining],
                [`uom_${i + 1}`, it.uom],
            ])),
        },
        freeze: true,
        freeze_message: __('Checking availability...'),
        callback: (r) => sig_render_dispatch_dialog(frm, openLines, fromWarehouse, r.message),
    });
}

function sig_render_dispatch_dialog(frm, openLines, fromWarehouse, availability) {
    const avByLine = {};
    if (availability && availability.result === 'ok') {
        availability.lines.forEach((l) => { avByLine[l.line] = l; });
    }

    const rowsHtml = openLines.map((it, i) => {
        const av = avByLine[i + 1];
        const available = av ? av.available : '?';
        const defaultQty = av ? Math.min(it.custom_qty_remaining, av.available) : it.custom_qty_remaining;
        const shortFlag = av && !av.sufficient ? ' <span class="text-danger">(short)</span>' : '';
        return `
            <tr data-mri="${it.name}" data-item="${it.item_code}" data-uom="${it.uom}">
                <td>${frappe.utils.escape_html(it.item_code)}</td>
                <td class="text-right">${it.qty}</td>
                <td class="text-right">${(it.custom_qty_issued || 0)}</td>
                <td class="text-right">${it.custom_qty_remaining}</td>
                <td class="text-right">${available}${shortFlag}</td>
                <td><input type="number" class="form-control input-sm sig-qty" step="any" min="0"
                    max="${it.custom_qty_remaining}" value="${defaultQty}"></td>
                <td>
                    <select class="form-control input-sm sig-outcome">
                        <option value="DISPATCH" selected>${__('Dispatch')}</option>
                        <option value="PENDING">${__('Leave pending')}</option>
                    </select>
                </td>
            </tr>`;
    }).join('');

    const d = new frappe.ui.Dialog({
        title: __('Dispatch {0}', [frm.doc.name]),
        size: 'large',
        fields: [
            { fieldtype: 'Data', fieldname: 'from_wh', label: __('From Warehouse'), default: fromWarehouse, read_only: 1 },
            { fieldtype: 'Date', fieldname: 'posting_date', label: __('Posting Date'), default: frappe.datetime.get_today() },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Link', fieldname: 'dispatched_to', label: __('Dispatched To'), options: 'Employee' },
            { fieldtype: 'Small Text', fieldname: 'remarks', label: __('Remarks') },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'lines_html',
                options: `<div class="table-responsive"><table class="table table-bordered sig-dispatch-lines">
                    <thead><tr>
                        <th>${__('Item')}</th><th class="text-right">${__('Requested')}</th>
                        <th class="text-right">${__('Issued')}</th><th class="text-right">${__('Remaining')}</th>
                        <th class="text-right">${__('Available')}</th><th>${__('Qty to Dispatch')}</th>
                        <th>${__('Outcome')}</th>
                    </tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table></div>`,
            },
        ],
        primary_action_label: __('Confirm Dispatch'),
        primary_action() {
            const rows = [...d.$wrapper.find('.sig-dispatch-lines tbody tr')];
            const lines = rows.map((row) => {
                const $row = $(row);
                return {
                    mri: $row.data('mri'),
                    qty: parseFloat($row.find('.sig-qty').val() || '0'),
                    outcome: $row.find('.sig-outcome').val(),
                };
            }).filter((l) => l.outcome === 'DISPATCH' && l.qty > 0);

            if (!lines.length) {
                frappe.msgprint(__('No lines selected to dispatch.'));
                return;
            }
            const totalQty = lines.reduce((s, l) => s + l.qty, 0);
            const values = d.get_values();
            const operationId = sig_gen_operation_id(fromWarehouse);

            frappe.confirm(
                __('Dispatch {0} line(s), total qty {1}, from {2}?<br><br>This creates and <b>submits</b> a Stock Entry immediately - it cannot be un-submitted from here.',
                    [lines.length, totalQty, fromWarehouse]),
                () => {
                    const args = {
                        operation_id: operationId, mr: frm.doc.name, from_wh: fromWarehouse,
                        posting_date: values.posting_date, dispatched_to: values.dispatched_to,
                        remarks: values.remarks, line_count: lines.length,
                    };
                    lines.forEach((l, i) => {
                        args[`mri_${i + 1}`] = l.mri;
                        args[`qty_${i + 1}`] = l.qty;
                        args[`outcome_${i + 1}`] = l.outcome;
                    });
                    frappe.call({
                        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_dispatch_mr',
                        args,
                        freeze: true,
                        freeze_message: __('Dispatching...'),
                        callback: (r) => {
                            const res = r.message || {};
                            if (res.result === 'created' || res.result === 'duplicate') {
                                frappe.msgprint({
                                    title: __('Dispatched'),
                                    indicator: 'green',
                                    message: __('Stock Entry {0} created and submitted.', [
                                        `<a href="/app/stock-entry/${res.stock_entry}">${res.stock_entry}</a>`]),
                                });
                                d.hide();
                                frm.reload_doc();
                            } else if (res.result === 'exception' && res.reason === 'CAP_EXCEEDED') {
                                frappe.msgprint({
                                    title: __('Cannot dispatch'),
                                    indicator: 'red',
                                    message: __('Line {0}: requested {1} exceeds remaining {2}. Reload and try again.',
                                        [res.line, res.requested, res.remaining]),
                                });
                            } else if (res.result === 'conflict') {
                                frappe.msgprint({
                                    title: __('Conflict'),
                                    indicator: 'red',
                                    message: __('This dispatch attempt changed after the operation ID was generated. Close this dialog and retry.'),
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('Dispatch failed'),
                                    indicator: 'red',
                                    message: __('{0}', [JSON.stringify(res)]),
                                });
                            }
                        },
                    });
                }
            );
        },
    });
    d.show();
}
