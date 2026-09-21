// Kanban/List-only enhancements (card-count badges, quick search, per-card
// actions, stock-availability dots). This is a SEPARATE bundle from
// material_request.js: Frappe loads `doctype_js` only on a Form page and
// `doctype_list_js` (this file) only on a List/Kanban page - a bundle
// registered under the wrong hook simply never executes on the page it was
// meant for. This file was previously (wrongly) merged into material_request.js
// under doctype_js, which is why none of this ever actually ran on the
// Kanban board - confirmed live 2026-09-18 (frappe.boot had no doctype_js
// entry for this page at all, and the doctype's __js bundle, while correctly
// built and served, is only evaluated by Frappe's Form controller, not by
// the Kanban/List view). Moved here under doctype_list_js instead, which
// Frappe does load for List/Kanban (confirmed live: erpnext's own core
// material_request_list.js already arrives via this exact hook).
//
// The bootstrap call itself (frappe.router.on + the initial call) is at the
// BOTTOM of this file, not here, on purpose: when this script evaluates, the
// Kanban board's DOM is often already present, so sig_maybe_setup_kanban()
// runs synchronously all the way down into functions that read `const`
// declarations further down this same file (SIG_STAGE_COLORS etc.) - a
// `const` is in the temporal dead zone until its own declaration line runs,
// so calling this before those declarations throws "Cannot access before
// initialization" and aborts the whole script silently. Confirmed live
// 2026-09-18: this was the actual reason nothing ever rendered, even after
// fixing the doctype_js/doctype_list_js hook above - not a Frappe loading
// problem at all, just this ordering bug (present since the very first
// version of this file, before the doctype_list_js split too).

// Tracks the exact .kanban DOM node our setup last ran against - not just
// whether we've "ever" set up. Confirmed live 2026-09-19 (after switching
// this file to app_include_js, which loads it much earlier than the old
// doctype_list_js path did): Frappe can still be constructing the Kanban
// board when this first runs, and later replaces that early/premature
// .kanban element wholesale with the real, fully-populated one - our
// MutationObserver only protects against mutations on the SAME node, not
// the node itself being swapped out, so a setup that fires too early binds
// to a node Frappe is about to discard and nothing (badges/dots/search/
// dispatch button) shows up on the real board that replaces it, even
// though comment-hiding still visibly worked (that part is a global CSS
// rule keyed by selector, not tied to a specific node reference). Re-
// checking on every call and re-running setup whenever the live node
// differs from last time is a cheap, robust fix regardless of exactly when
// Frappe decides to do that replacement.
let __sig_last_kanban_node = null;
function sig_maybe_setup_kanban() {
    // Defensive: confirmed live 2026-09-19 that something inside this call
    // chain (most likely frappe.get_route() itself, or frappe internals it
    // touches) can throw at certain moments now that this script - loaded
    // via app_include_js - runs much earlier than before, sometimes ahead
    // of Frappe's own router being fully ready. This runs on a 1s interval
    // (see bottom of file) for the lifetime of the tab, so left unguarded a
    // transient throw here is not fatal to the interval itself, but it is
    // an uncaught exception on every tick until conditions change - swallow
    // it and let the next tick retry instead.
    try {
        const route = (frappe.get_route && frappe.get_route()) || [];
        if (route[0] !== 'List' || route[1] !== 'Material Request' || route[2] !== 'Kanban') return;
        sig_wait_for_kanban_board(($board) => {
            // Frappe can add the native toolbar/column-create controls after
            // the board node exists. Re-run this cheap cleanup on every poll,
            // even when the board node itself has not changed.
            sig_hide_kanban_create_controls($board);
            const node = $board.get(0);
            if (node === __sig_last_kanban_node && document.body.contains(node)) return;
            __sig_last_kanban_node = node;
            sig_setup_kanban_updates($board);
            sig_setup_kanban_search($board);
            sig_setup_kanban_actions($board);
            sig_setup_dispatch_tool_button($board);
        });
    } catch (e) {
        console.error('sig_maybe_setup_kanban: transient error, will retry', e);
    }
}
// Route changes alone don't cover an in-place node replacement (no route
// change happens when Frappe swaps the board out from under us), so also
// poll cheaply while this tab might be sitting on the Kanban route. The
// node-identity check above makes repeated calls a fast no-op once the
// board has stabilized.
setInterval(() => sig_maybe_setup_kanban(), 1000);

function sig_wait_for_kanban_board(callback, attemptsLeft = 40) {
    // Frappe v15's Kanban root wrapper class is '.kanban', not '.kanban-board'
    // (confirmed live on this site's Frappe 15.106.0).
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
        sig_hide_kanban_create_controls($board);
        $board.find('.kanban-column').each(function () {
            const $col = $(this);
            const $cards = $col.find('.kanban-cards .kanban-card-wrapper');
            const count = $cards.filter(':visible').length;
            let $badge = $col.find('.sig-kanban-count');
            if (!$badge.length) {
                $badge = $('<span class="sig-kanban-count badge pull-right" style="font-weight:normal;"></span>');
                $col.find('.kanban-column-header').first().append($badge);
            }
            // Only write when the value actually changes: .text() replaces
            // the text node even when the string is identical, which is a
            // real childList mutation - inside a MutationObserver watching
            // childList:true, an unconditional write here re-triggers the
            // observer on every single call, forever. Confirmed live in an
            // isolated repro (2026-09-19): this pre-existing line, not the
            // availability-dot feature added this session, was the actual
            // cause of the Kanban board becoming unresponsive - update()
            // ran 2000+ times in 8 seconds from this alone, with the
            // server only ever called once as expected.
            if ($badge.text() !== String(count)) $badge.text(count);

            const color = sig_stage_color_for_column($col);
            $cards.find('.kanban-card').css('border-left', color ? `4px solid ${color}` : '');
        });
        sig_refresh_kanban_availability($board);
    };
    update();
    if ($board.data('sig-update-observer')) return; // already watching this board instance
    const observer = new MutationObserver(() => update());
    observer.observe($board.get(0), { childList: true, subtree: true });
    $board.data('sig-update-observer', observer);
}

function sig_hide_kanban_create_controls($board) {
    // This is an operational dispatch board, not a request-intake board.
    // Frappe's Kanban adds one native create control in the toolbar and one
    // in every column; each creates a new Material Request rather than
    // issuing an existing one. Suppress them only on this SIG route.
    const hiddenLabels = new Set(['add material request', '+ add material request', '+ add column']);
    // Frappe's current Kanban renderer uses stable structural classes for
    // these native creation affordances. Hide them directly so late-rendered
    // controls cannot escape the text-based fallback below.
    $('.page-container .standard-actions .primary-action').hide();
    $('.page-container .kanban-column.add-new-column, .page-container .kanban-column .add-card').hide();
    $('.page-container button, .page-container a, .page-container span, .page-container div')
        .filter(function () {
        return hiddenLabels.has($(this).text().replace(/\s+/g, ' ').trim().toLowerCase());
        }).hide();
}

// Per-MR stock-availability traffic light (green/yellow/red dot on each
// card), separate from the stage-color left border above. Debounced and
// deduped: the MutationObserver in sig_setup_kanban_updates fires on every
// DOM change (including the dot being added), so without both guards this
// would call the server in a tight loop. A card with no dot (server left it
// out of the response - no open lines) gets no dot at all, not a default
// color, so a fully-dispatched/cancelled MR is left unmarked rather than
// implying a stock state that doesn't apply to it.
const SIG_AVAILABILITY_COLOR = { green: '#16a34a', yellow: '#eab308', red: '#dc2626' };
let sig_availability_fetch_pending = false;

function sig_refresh_kanban_availability($board) {
    // Marked "checked" (not just "has a dot") the moment a card is picked up
    // for this batch, synchronously, before the async frappe.call even
    // returns - a card with no open lines never gets a dot back from the
    // server, so filtering on the dot alone would make this function pick
    // the same never-dotted cards again on every subsequent mutation
    // (including the mutation caused by THIS batch's own dot insertions),
    // looping indefinitely and freezing the board. Filtering on the
    // "checked" marker instead guarantees the candidate set strictly
    // shrinks to empty after one pass, regardless of how many cards never
    // get a dot. Confirmed live 2026-09-18: the dot-only version froze the
    // real board (216 cards, most DISPATCHED/CLOSED with no open lines).
    const $wrappers = $board.find('.kanban-card-wrapper').not('.sig-kanban-availability-checked');
    if (!$wrappers.length || sig_availability_fetch_pending) return;
    const names = [...new Set($wrappers.map(function () { return decodeURIComponent($(this).attr('data-name')); }).get())];
    $wrappers.addClass('sig-kanban-availability-checked');
    if (!names.length) return;
    sig_availability_fetch_pending = true;
    frappe.call({
        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_kanban_availability_status',
        args: { mrs: names },
        callback: (r) => {
            sig_availability_fetch_pending = false;
            const statuses = r.message || {};
            // Re-select the board fresh from the live document instead of
            // using the $board this call closed over: confirmed live
            // 2026-09-19 that Frappe can re-render this board's cards
            // (new DOM nodes replacing the old ones) while this request is
            // in flight - by the time this callback runs, the captured
            // $board can point at a detached snapshot, so writing into it
            // silently succeeds in JS terms but never appears on screen
            // (no error, no dots, response data was fine the whole time).
            $('.kanban').find('.kanban-card-wrapper').each(function () {
                const $card = $(this);
                if ($card.find('.sig-kanban-availability-dot').length) return;
                const mrName = decodeURIComponent($card.attr('data-name'));
                const status = statuses[mrName];
                if (!status) return;
                const $dot = $(`<span class="sig-kanban-availability-dot" title="${__('Stock availability')}: ${status}"
                    style="position:absolute; top:6px; left:6px; width:9px; height:9px; border-radius:50%; z-index:2;
                    background:${SIG_AVAILABILITY_COLOR[status]};"></span>`);
                $card.css('position', 'relative');
                $card.find('.kanban-card.content').first().append($dot);
            });
        },
        error: () => { sig_availability_fetch_pending = false; },
    });
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

// Standalone tool/equipment custody dispatch - deliberately NOT reachable
// from a Material Request (owner decision: issuing consumable material is
// linked to a site/project/return chain; a tool going out to a person isn't
// - it has no site/project, and comes back through custody return, not the
// MR-line return flow). Lives on the Dispatch Board's toolbar instead, next
// to the search box, since that's the warehouse's general action surface.
function sig_setup_dispatch_tool_button($board) {
    if ($('.sig-dispatch-tool-btn').length) return;
    const $btn = $(`<button type="button" class="btn btn-default btn-sm sig-dispatch-tool-btn" style="margin: 0 15px 10px;">
        ${__('Dispatch Tool')}
    </button>`);
    $('.sig-kanban-search').after($btn);
    $btn.on('click', () => sig_open_dispatch_tool_dialog());
}

function sig_open_dispatch_tool_dialog() {
    const d = new frappe.ui.Dialog({
        title: __('Dispatch Tool (Custody)'),
        fields: [
            { fieldtype: 'Link', fieldname: 'item_code', label: __('Item'), options: 'Item', reqd: 1,
              get_query: () => ({ filters: { disabled: 0 } }) },
            { fieldtype: 'Link', fieldname: 'from_wh', label: __('From Warehouse'), options: 'Warehouse', reqd: 1,
              get_query: () => ({ filters: { is_group: 0, disabled: 0 } }) },
            { fieldtype: 'Float', fieldname: 'qty', label: __('Qty'), default: 1, reqd: 1 },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Select', fieldname: 'custodian_type', label: __('Custodian'),
              options: ['Employee', 'Other'], default: 'Employee', reqd: 1 },
            { fieldtype: 'Link', fieldname: 'custodian', label: __('Employee'), options: 'Employee',
              depends_on: 'eval:doc.custodian_type=="Employee"', mandatory_depends_on: 'eval:doc.custodian_type=="Employee"' },
            { fieldtype: 'Data', fieldname: 'custodian_name', label: __('Name'),
              depends_on: 'eval:doc.custodian_type=="Other"', mandatory_depends_on: 'eval:doc.custodian_type=="Other"' },
            { fieldtype: 'Data', fieldname: 'custodian_phone', label: __('Phone'),
              depends_on: 'eval:doc.custodian_type=="Other"' },
            { fieldtype: 'Section Break' },
            { fieldtype: 'Small Text', fieldname: 'reason', label: __('Reason / Remarks') },
        ],
        primary_action_label: __('Confirm Dispatch'),
        primary_action(values) {
            frappe.confirm(
                __('Dispatch {0} x {1} from {2} to {3}?<br><br>This creates and <b>submits</b> a Stock Entry immediately - it cannot be un-submitted from here.',
                    [values.qty, values.item_code, values.from_wh, values.custodian_type === 'Employee' ? values.custodian : values.custodian_name]),
                () => {
                    frappe.call({
                        method: 'sig_warehouse.sig_warehouse.custody.sig_dispatch_tool',
                        args: {
                            operation_id: sig_gen_operation_id('TOOL-' + values.from_wh),
                            item_code: values.item_code, qty: values.qty, from_wh: values.from_wh,
                            custodian_type: values.custodian_type, custodian: values.custodian,
                            custodian_name: values.custodian_name, custodian_phone: values.custodian_phone,
                            reason: values.reason,
                        },
                        freeze: true, freeze_message: __('Dispatching...'),
                        callback: (r) => {
                            const res = r.message || {};
                            if (res.result === 'created' || res.result === 'duplicate') {
                                frappe.msgprint({
                                    title: __('Dispatched'), indicator: 'green',
                                    message: __('Stock Entry {0} created and submitted. In custody of {1}.', [
                                        `<a href="/app/stock-entry/${res.stock_entry}">${res.stock_entry}</a>`, res.custodian_name || '']),
                                });
                                d.hide();
                            } else {
                                frappe.msgprint({
                                    title: __('Dispatch failed'), indicator: 'red',
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

// Per-card actions. Repurposes Frappe's native card-corner "+" (normally
// "assign this document to a user" - .kanban-assignments/.avatar-action in
// the live DOM) into the Dispatch/Return/Cancel action menu instead: no
// assign-to-user workflow is needed here, and the owner wants the "+" to be
// the obvious, single way to act on a card rather than a second icon next to
// an unrelated native one. Bound on the capture phase so this runs before
// Frappe's own delegated click handler ever sees the event, regardless of
// whether that handler is bound on the element itself or delegated from a
// distant ancestor - stopping propagation in the bubble phase alone would
// only be guaranteed to beat a handler bound on this element or an ancestor
// further out, not one bound directly on the assign icon itself.
// Also drops the per-card comment-count badge (small chat-bubble icon) -
// not useful on this board and adds visual noise; comments are still fully
// visible from the document itself.
function sig_setup_kanban_actions($board) {
    if (!$('#sig-kanban-card-style').length) {
        $('<style id="sig-kanban-card-style">' +
          '.kanban .list-comment-count { display: none !important; } ' +
          '.kanban .kanban-assignments { cursor: pointer; }' +
          '</style>').appendTo('head');
    }
    $board.find('.kanban-card-wrapper').each(function () {
        const $card = $(this);
        const assignEl = $card.find('.kanban-assignments').get(0);
        if (!assignEl || assignEl.__sigBound) return;
        assignEl.__sigBound = true;
        assignEl.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            sig_show_kanban_action_menu($(assignEl), $card.attr('data-name'));
        }, true);
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
                    { fieldtype: 'Check', fieldname: 'close_as_consumed',
                        label: __('No material returned — close all undeclared lines as consumed'), default: 0 },
                    { fieldtype: 'Section Break' },
                    {
                        fieldtype: 'HTML', fieldname: 'lines_html',
                        options: `<div class="table-responsive"><table class="table table-bordered">
                            <thead><tr><th>${__('Item')}</th><th class="text-right">${__('Undeclared')}</th><th>${__('Qty to Return')}</th></tr></thead>
                            <tbody>${rowsHtml}</tbody></table></div>`,
                    },
                ],
                primary_action_label: __('Confirm disposition'),
                primary_action() {
                    const rows = [...d.$wrapper.find('tbody tr')];
                    const closeAsConsumed = !!d.get_value('close_as_consumed');
                    const returnedLines = rows.map((row) => {
                        const $row = $(row);
                        return { sed: $row.data('sed'), qty: parseFloat($row.find('.sig-return-qty').val() || '0') };
                    }).filter((l) => l.qty > 0);
                    const lines = closeAsConsumed
                        ? rows.map((row) => ({ sed: $(row).data('sed'), qty: null }))
                        : returnedLines;
                    if (!lines.length) {
                        frappe.msgprint(__('Enter a return quantity, or explicitly select close as consumed.'));
                        return;
                    }
                    const toWh = d.get_value('to_wh');
                    const action = closeAsConsumed ? 'CLOSE' : 'RETURN';
                    frappe.confirm(
                        closeAsConsumed
                            ? __('Close {0} undeclared line(s) on {1} as consumed? No stock movement will be made. You may reopen the original Stock Entry later for a correction.', [lines.length, sourceSe])
                            : __('Return {0} line(s) from {1} to {2}? This submits a Stock Entry immediately.', [lines.length, sourceSe, toWh]),
                        () => {
                            const args = {
                                operation_id: sig_gen_operation_id(action), action, source_se: sourceSe,
                                line_count: lines.length,
                            };
                            if (action === 'RETURN') args.to_wh = toWh;
                            lines.forEach((l, i) => {
                                args[`sed_${i + 1}`] = l.sed;
                                if (l.qty !== null) args[`qty_${i + 1}`] = l.qty;
                            });
                            frappe.call({
                                method: 'sig_warehouse.sig_warehouse.disposition.sig_declare_disposition',
                                args, freeze: true, freeze_message: closeAsConsumed ? __('Closing...') : __('Returning...'),
                                callback: (res2) => {
                                    const res = res2.message || {};
                                    if (res.result === 'created' || res.result === 'duplicate') {
                                        frappe.show_alert({ message: closeAsConsumed ? __('Closed as consumed.') : __('Returned.'), indicator: 'green' });
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

// Dispatch dialog builder - duplicated from material_request.js on purpose;
// see the comment at the top of that file's copy for why.
function sig_gen_operation_id(warehouse) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const safeWh = (warehouse || 'WH').replace(/[^A-Za-z0-9]/g, '').slice(0, 12) || 'WH';
    return `SIG-DISPOP-${safeWh}-${stamp}-${Math.floor(Math.random() * 900 + 100)}`;
}

// Warehouses that can be a dispatch source. The request's WH text picks the
// line's default warehouse at intake with no stock check, so a Makkah-area
// request can point at a warehouse that has none of the item while another
// holds it - the dispatch dialog therefore lets the operator choose the
// source and pre-selects one that actually covers the lines.
const SIG_SOURCE_WAREHOUSES = [
    'مستودع المزاحمية - SIG',
    'مستودع مكة - SIG',
    'مستودع القصيم - SIG',
    'مستودع جازان - SIG',
];

function sig_check_availability(wh, openLines) {
    return frappe.call({
        method: 'check_dn_availability',
        args: {
            from_wh: wh,
            line_count: openLines.length,
            ...Object.fromEntries(openLines.flatMap((it, i) => [
                [`code_${i + 1}`, it.item_code],
                [`qty_${i + 1}`, it.custom_qty_remaining],
                [`uom_${i + 1}`, it.uom],
            ])),
        },
    }).then((r) => r.message);
}

async function sig_open_dispatch_dialog(frm, overrideWh) {
    const openLines = (frm.doc.items || []).filter(it => (it.custom_qty_remaining || 0) > 0.000001);
    if (!openLines.length) {
        frappe.msgprint(__('No open lines to dispatch on this request.'));
        return;
    }
    let fromWarehouse = overrideWh || openLines[0].warehouse;
    let note = '';
    frappe.dom.freeze(__('Checking availability...'));
    try {
        let availability = await sig_check_availability(fromWarehouse, openLines);
        const short = (a) => a && a.result === 'ok' && a.lines.some((l) => !l.sufficient);
        if (!overrideWh && short(availability)) {
            for (const wh of SIG_SOURCE_WAREHOUSES.filter((w) => w !== fromWarehouse)) {
                const alt = await sig_check_availability(wh, openLines);
                if (alt && alt.result === 'ok' && alt.lines.every((l) => l.sufficient)) {
                    note = __('Stock is not fully available in {0}; source switched to {1}, which covers every line. Change the warehouse below if that is wrong.',
                        [fromWarehouse, wh]);
                    fromWarehouse = wh;
                    availability = alt;
                    break;
                }
            }
        }
        frappe.dom.unfreeze();
        sig_render_dispatch_dialog(frm, openLines, fromWarehouse, availability, note);
    } catch (e) {
        frappe.dom.unfreeze();
        throw e;
    }
}

function sig_render_dispatch_dialog(frm, openLines, fromWarehouse, availability, note) {
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
                <td></td>
            </tr>`;
    }).join('');

    const d = new frappe.ui.Dialog({
        title: __('Dispatch {0}', [frm.doc.name]),
        size: 'large',
        fields: [
            ...(note ? [{ fieldtype: 'HTML', fieldname: 'switch_note',
                          options: `<div class="alert alert-warning" style="margin-bottom:8px;">${frappe.utils.escape_html(note)}</div>` }] : []),
            { fieldtype: 'Select', fieldname: 'from_wh', label: __('From Warehouse'),
              options: [...new Set([fromWarehouse, ...SIG_SOURCE_WAREHOUSES])].join('\n'), default: fromWarehouse,
              change() {
                  const v = d.get_value('from_wh');
                  if (v && v !== fromWarehouse) { d.hide(); sig_open_dispatch_dialog(frm, v); }
              } },
            { fieldtype: 'Date', fieldname: 'posting_date', label: __('Posting Date'), default: frappe.datetime.get_today() },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Select', fieldname: 'recipient_type', label: __('Dispatched To Type'),
              options: 'Employee\nOther', default: 'Employee', reqd: 1 },
            { fieldtype: 'Link', fieldname: 'dispatched_to', label: __('Employee'), options: 'Employee',
              depends_on: 'eval:doc.recipient_type=="Employee"', mandatory_depends_on: 'eval:doc.recipient_type=="Employee"' },
            { fieldtype: 'Data', fieldname: 'dispatched_to_other', label: __('Other recipient'),
              depends_on: 'eval:doc.recipient_type=="Other"', mandatory_depends_on: 'eval:doc.recipient_type=="Other"' },
            { fieldtype: 'Small Text', fieldname: 'remarks', label: __('Remarks') },
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'HTML', fieldname: 'lines_html',
                options: `<div class="table-responsive"><table class="table table-bordered sig-dispatch-lines">
                    <thead><tr>
                        <th>${__('Item')}</th><th class="text-right">${__('Requested')}</th>
                        <th class="text-right">${__('Issued')}</th><th class="text-right">${__('Remaining')}</th>
                        <th class="text-right">${__('Available')}</th><th>${__('Qty to Dispatch')}</th>
                        <th>${__('Outcome')}</th><th></th>
                    </tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table></div>`,
            },
            { fieldtype: 'Section Break', label: __('Add an item not on this request') },
            { fieldtype: 'Link', fieldname: 'new_item_code', label: __('Item'), options: 'Item',
              get_query: () => ({ filters: { disabled: 0 } }) },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Float', fieldname: 'new_item_qty', label: __('Qty'), default: 1 },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Button', fieldname: 'add_item_btn', label: __('+ Add to list'),
              click: () => sig_add_line_to_dispatch_dialog(d) },
        ],
        primary_action_label: __('Confirm Dispatch'),
        async primary_action() {
            const rows = [...d.$wrapper.find('.sig-dispatch-lines tbody tr')];
            const existingLines = rows.filter((row) => !$(row).data('new')).map((row) => {
                const $row = $(row);
                return {
                    mri: $row.data('mri'),
                    qty: parseFloat($row.find('.sig-qty').val() || '0'),
                    outcome: $row.find('.sig-outcome').val(),
                };
            }).filter((l) => l.outcome === 'DISPATCH' && l.qty > 0);
            const newRows = rows.filter((row) => $(row).data('new'));

            const addedLines = [];
            for (const row of newRows) {
                const $row = $(row);
                const qty = parseFloat($row.find('.sig-qty').val() || '0');
                if (!(qty > 0)) continue;
                let res;
                try {
                    res = (await frappe.call({
                        method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_add_mr_line',
                        args: { mr: frm.doc.name, item_code: $row.data('item'), qty, uom: $row.data('uom') },
                        freeze: true, freeze_message: __('Adding {0}...', [$row.data('item')]),
                    })).message || {};
                } catch (e) {
                    res = { result: 'exception', reason: String(e) };
                }
                if (res.result !== 'created') {
                    frappe.msgprint({
                        title: __('Could not add {0}', [$row.data('item')]),
                        indicator: 'red',
                        message: __('{0}', [JSON.stringify(res)]),
                    });
                    return;
                }
                addedLines.push({ mri: res.mri, qty, outcome: 'DISPATCH' });
            }

            const lines = existingLines.concat(addedLines);
            if (!lines.length) {
                frappe.msgprint(__('No lines selected to dispatch.'));
                return;
            }
            const totalQty = lines.reduce((s, l) => s + l.qty, 0);
            const values = d.get_values();
            if (values.recipient_type === 'Employee' && !values.dispatched_to) {
                frappe.msgprint(__('Select the employee receiving this dispatch.'));
                return;
            }
            if (values.recipient_type === 'Other' && !String(values.dispatched_to_other || '').trim()) {
                frappe.msgprint(__('Enter the manual recipient for Other.'));
                return;
            }
            const operationId = sig_gen_operation_id(fromWarehouse);

            frappe.confirm(
                __('Dispatch {0} line(s), total qty {1}, from {2}?<br><br>This creates and <b>submits</b> a Stock Entry immediately - it cannot be un-submitted from here.',
                    [lines.length, totalQty, fromWarehouse]),
                () => {
                    const args = {
                        operation_id: operationId, mr: frm.doc.name, from_wh: fromWarehouse,
                        posting_date: values.posting_date, dispatched_to: values.dispatched_to,
                        dispatched_to_other: values.recipient_type === 'Other' ? values.dispatched_to_other : '',
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
                                if (frm.reload_doc) frm.reload_doc();
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

function sig_add_line_to_dispatch_dialog(d) {
    const itemCode = d.get_value('new_item_code');
    const qty = parseFloat(d.get_value('new_item_qty') || '0');
    if (!itemCode) {
        frappe.msgprint(__('Pick an item first.'));
        return;
    }
    if (!(qty > 0)) {
        frappe.msgprint(__('Qty must be greater than 0.'));
        return;
    }
    frappe.db.get_value('Item', itemCode, 'stock_uom').then((r) => {
        const uom = (r.message && r.message.stock_uom) || '';
        const $row = $(`
            <tr data-new="1" data-item="${itemCode}" data-uom="${uom}">
                <td>${frappe.utils.escape_html(itemCode)} <span class="text-muted">(${__('new')})</span></td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td class="text-right">-</td>
                <td><input type="number" class="form-control input-sm sig-qty" step="any" min="0" value="${qty}"></td>
                <td><select class="form-control input-sm sig-outcome">
                        <option value="DISPATCH" selected>${__('Dispatch')}</option>
                    </select></td>
                <td><span class="sig-remove-new-row text-danger" style="cursor:pointer;" title="${__('Remove')}">&times;</span></td>
            </tr>`);
        $row.find('.sig-remove-new-row').on('click', () => $row.remove());
        d.$wrapper.find('.sig-dispatch-lines tbody').append($row);
        d.set_value('new_item_code', '');
        d.set_value('new_item_qty', 1);
    });
}

// Bootstrap - must be the LAST thing in this file. See the comment near
// sig_maybe_setup_kanban's definition above for why: this can run
// synchronously all the way through to code that reads a `const` declared
// earlier in this file, and that only works once every such declaration has
// already executed.
frappe.router.on('change', () => sig_maybe_setup_kanban());
sig_maybe_setup_kanban();
