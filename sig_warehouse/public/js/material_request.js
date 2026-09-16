frappe.ui.form.on('Material Request', {
    refresh(frm) {
        if (frm.doc.material_request_type !== 'Material Issue') return;
        if (frm.doc.docstatus !== 1) return;
        if (!['PENDING', 'PARTIAL'].includes(frm.doc.custom_dispatch_stage)) return;
        if (frm.__sig_dispatch_button_added) return;
        frm.__sig_dispatch_button_added = true;
        frm.add_custom_button(__('Dispatch'), () => sig_open_dispatch_dialog(frm), __('Actions'));
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
    });
}

function sig_wait_for_kanban_board(callback, attemptsLeft = 40) {
    const $board = $('.kanban-board');
    if ($board.length) {
        callback($board);
        return;
    }
    if (attemptsLeft <= 0) return;
    setTimeout(() => sig_wait_for_kanban_board(callback, attemptsLeft - 1), 250);
}

// Column title text is the raw custom_dispatch_stage value (Kanban groups by
// that field) - matched case-insensitively since Kanban Board column labels
// are free text and could get re-cased/renamed independently of the field.
const SIG_STAGE_COLORS = {
    PENDING: '#94a3b8',
    PARTIAL: '#f59e0b',
    DISPATCHED: '#16a34a',
};

function sig_stage_color_for_column($col) {
    const title = $col.find('.kanban-column-title').first().clone()
        .children('.sig-kanban-count').remove().end()
        .text().trim().toUpperCase();
    return SIG_STAGE_COLORS[title] || null;
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
                $col.find('.kanban-column-title').append($badge);
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
