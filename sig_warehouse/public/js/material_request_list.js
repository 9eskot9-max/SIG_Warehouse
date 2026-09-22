// Kanban/List-only enhancements (card-count badges, quick search, per-card
// actions, stock-availability dots). Loaded via app_include_js (this file,
// material_request.js and stock_entry.js all load on every desk page - see
// hooks.py). Everything below is scoped inside one IIFE so this file's names
// can never collide with the other two, whatever they declare (2026-09-22
// fix: two files each declared a function literally named
// `sig_open_dispatch_dialog` with a different signature; classic scripts
// share one global scope, so the last one loaded silently won regardless of
// which page you were on, and the toolbar button below - which always meant
// to call the OTHER (custody) dialog - called the MR-dispatch one with no
// argument instead and threw. The single MR-dispatch implementation now
// lives only in material_request.js and is called here through
// `window.sig_wh.open_mr_dispatch`, resolved at click time, never at
// file-evaluation time, so load order can't matter again).
(() => {
    'use strict';

    const ROUTE = 'List/Material Request/Kanban/SIG Dispatch Queue';

    function on_our_route() {
        const r = (frappe.get_route && frappe.get_route()) || [];
        return r[0] === 'List' && r[1] === 'Material Request' && r[2] === 'Kanban';
    }

    // ---------------------------------------------------------------------
    // Static CSS instead of a polling text-scan. The previous version ran a
    // 1-second setInterval for the tab's whole lifetime, text-scanning every
    // button/link/span/div under .page-container (~4,300 elements on this
    // board, confirmed live) on every tick - this was the board's main-thread
    // lag. An attribute-selector CSS rule re-applies itself automatically the
    // instant Frappe adds a matching node or updates data-page-route; no JS
    // needs to run at all, on every tick or otherwise.
    // ---------------------------------------------------------------------
    function ensure_style_once() {
        if (document.getElementById('sig-kanban-style')) return;
        const scope = `.page-container[data-page-route="${ROUTE}"]`;
        $(`<style id="sig-kanban-style">
            ${scope} .kanban .add-card,
            ${scope} .kanban-column.add-new-column,
            ${scope} .standard-actions .primary-action,
            ${scope} .kanban .list-comment-count { display: none !important; }
            ${scope} .kanban .kanban-assignments { cursor: pointer; }
        </style>`).appendTo('head');
    }

    // ---------------------------------------------------------------------
    // Card-count badges + stage-colored borders. Unchanged from the previous
    // version except for the rename - still only writes when the value
    // actually changes: .text() replaces the text node even when the string
    // is identical, which is a real childList mutation and would re-trigger
    // the observer below on every single call, forever (this exact bug froze
    // the live board once already, 2026-09-19).
    // ---------------------------------------------------------------------
    const SIG_STAGE_COLORS = {
        PENDING: '#94a3b8',
        PARTIAL: '#f59e0b',
        DISPATCHED: '#16a34a',
        CLOSED: '#64748b',
    };

    function stage_color_for_column($col) {
        const key = ($col.attr('data-column-value') || $col.find('.kanban-title').first().text())
            .trim().toUpperCase();
        return SIG_STAGE_COLORS[key] || null;
    }

    function paint_badges_and_borders($board) {
        $board.find('.kanban-column').each(function () {
            const $col = $(this);
            const $cards = $col.find('.kanban-cards .kanban-card-wrapper');
            const count = $cards.filter(':visible').length;
            let $badge = $col.find('.sig-kanban-count');
            if (!$badge.length) {
                $badge = $('<span class="sig-kanban-count badge pull-right" style="font-weight:normal;"></span>');
                $col.find('.kanban-column-header').first().append($badge);
            }
            if ($badge.text() !== String(count)) $badge.text(count);

            const color = stage_color_for_column($col);
            $cards.find('.kanban-card').css('border-left', color ? `4px solid ${color}` : '');
        });
    }

    // ---------------------------------------------------------------------
    // Search box. Always re-selects the live `.kanban` node at filter time
    // instead of closing over the node captured when the box was inserted -
    // Frappe replaces that node wholesale on redraw (confirmed live), so the
    // old version's captured `$board` went stale and typing silently
    // filtered a detached copy of the board until a full page reload.
    // `decorate()` re-applies the current query after every redraw too, for
    // the same reason.
    // ---------------------------------------------------------------------
    let sig_search_query = '';

    function ensure_search_box($board) {
        if (document.getElementById('sig-kanban-search-input')) return;
        const $box = $(`<div class="sig-kanban-search" style="margin: 0 15px 10px;">
            <input type="text" id="sig-kanban-search-input" class="form-control input-sm" placeholder="${__('Search MR #, site (e.g. 1011, ZMK113)...')}">
        </div>`);
        $board.before($box);
        $box.find('input').on('input', function () {
            sig_search_query = $(this).val().trim().toLowerCase();
            apply_search_filter($('.kanban').first());
            paint_badges_and_borders($('.kanban').first());
        });
    }

    function apply_search_filter($board) {
        if (!$board || !$board.length) return;
        $board.find('.kanban-card-wrapper').each(function () {
            const $card = $(this);
            const match = !sig_search_query || $card.text().toLowerCase().includes(sig_search_query);
            $card.toggle(match);
        });
    }

    // ---------------------------------------------------------------------
    // Per-MR stock-availability traffic light. Cached with a TTL instead of
    // re-fetched on every redraw (previously: a card-identity "checked" flag
    // stopped an infinite loop, but every board rebuild still re-fetched all
    // ~270 MRs from scratch). The cache also records a lookup for an MR the
    // server left out of the response (no open lines) so such a card is not
    // endlessly re-requested. `invalidate_availability` is exported so a
    // dispatch/return/cancel elsewhere (material_request.js, or the card
    // actions below) can force a fresh check for just that one MR instead of
    // waiting out the TTL.
    // ---------------------------------------------------------------------
    const SIG_AVAILABILITY_COLOR = { green: '#16a34a', yellow: '#eab308', red: '#dc2626' };
    const SIG_AVAILABILITY_TTL_MS = 60000;
    const sig_availability_cache = new Map(); // mrName -> { status: 'green'|'yellow'|'red'|null, at: epoch ms }
    let sig_availability_fetch_pending = false;

    function invalidate_availability(mrName) {
        sig_availability_cache.delete(mrName);
    }

    function paint_cached_dots($board) {
        if (!$board || !$board.length) return;
        $board.find('.kanban-card-wrapper').each(function () {
            const $card = $(this);
            const mrName = decodeURIComponent($card.attr('data-name') || '');
            const cached = sig_availability_cache.get(mrName);
            const status = cached && cached.status;
            let $dot = $card.find('.sig-kanban-availability-dot');
            if (!status) { $dot.remove(); return; }
            if (!$dot.length) {
                $dot = $('<span class="sig-kanban-availability-dot"></span>');
                $card.css('position', 'relative');
                $card.find('.kanban-card.content').first().append($dot);
            }
            $dot.attr('title', `${__('Stock availability')}: ${status}`).css({
                position: 'absolute', top: '6px', left: '6px', width: '9px', height: '9px',
                borderRadius: '50%', zIndex: 2, background: SIG_AVAILABILITY_COLOR[status],
            });
        });
    }

    function refresh_availability($board) {
        paint_cached_dots($board);
        if (sig_availability_fetch_pending) return;
        const now = Date.now();
        const names = [...new Set($board.find('.kanban-card-wrapper').map(function () {
            return decodeURIComponent($(this).attr('data-name') || '');
        }).get())].filter((n) => n && (!sig_availability_cache.has(n) || now - sig_availability_cache.get(n).at > SIG_AVAILABILITY_TTL_MS));
        if (!names.length) return;
        sig_availability_fetch_pending = true;
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.dispatch_operation.sig_kanban_availability_status',
            args: { mrs: names },
            callback: (r) => {
                sig_availability_fetch_pending = false;
                const statuses = r.message || {};
                const stamp = Date.now();
                names.forEach((n) => { sig_availability_cache.set(n, { status: statuses[n] || null, at: stamp }); });
                // Re-select fresh: Frappe can have replaced the board node
                // while this call was in flight (confirmed live 2026-09-19).
                paint_cached_dots($('.kanban').first());
            },
            error: () => { sig_availability_fetch_pending = false; },
        });
    }

    // ---------------------------------------------------------------------
    // Standalone tool/equipment custody dispatch - deliberately NOT
    // reachable from a Material Request (owner decision: issuing consumable
    // material is linked to a site/project/return chain; a tool going out to
    // a person isn't - it has no site/project, and comes back through
    // custody return, not the MR-line return flow). Lives on the board's
    // toolbar, next to the search box.
    //
    // Renamed from `sig_open_dispatch_dialog` (2026-09-22): this file used to
    // declare a function of that exact name twice - once here (2 args,
    // custody) and once below where the MR-dispatch dialog was duplicated -
    // the second declaration silently won even within this one file, so this
    // custody dialog was ALREADY permanently unreachable before
    // material_request.js's copy ever entered the picture. The toolbar
    // "Dispatch / Return" button has therefore never actually opened this
    // dialog on the live board. Fixed by giving each dialog its own name and
    // deleting the duplicate MR-dispatch copy entirely (see the bottom of
    // this file, where the Kanban card's Issue action now calls
    // `window.sig_wh.open_mr_dispatch` in material_request.js instead).
    // ---------------------------------------------------------------------
    function sig_gen_operation_id(warehouse) {
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const safeWh = (warehouse || 'WH').replace(/[^A-Za-z0-9]/g, '').slice(0, 12) || 'WH';
        return `SIG-DISPOP-${safeWh}-${stamp}-${Math.floor(Math.random() * 900 + 100)}`;
    }

    function sig_open_custody_dialog() {
        const T = 'doc.kind=="Tool"', A = 'doc.kind=="Asset"';
        const AD = A + ' && doc.mode=="Dispatch"', AR = A + ' && doc.mode=="Return"';
        const TE = T + ' && doc.custodian_type=="Employee"', TO = T + ' && doc.custodian_type=="Other"';
        const d = new frappe.ui.Dialog({
            title: __('Dispatch / Return'),
            fields: [
                { fieldtype: 'Link', fieldname: 'item_code', label: __('Item'), options: 'Item', reqd: 1,
                  get_query: () => ({ filters: { disabled: 0 } }),
                  change() {
                      const code = d.get_value('item_code');
                      if (!code) return;
                      frappe.db.get_value('Item', code, 'is_fixed_asset').then(r => {
                          d.set_value('kind', (r.message && r.message.is_fixed_asset) ? 'Asset' : 'Tool');
                          d.set_value('asset', '');
                      });
                  } },
                { fieldtype: 'Data', fieldname: 'kind', hidden: 1, default: 'Tool' },
                { fieldtype: 'Select', fieldname: 'mode', label: __('Action'), options: ['Dispatch', 'Return'], default: 'Dispatch',
                  depends_on: 'eval:' + A },
                // --- Tool (stock) ---
                { fieldtype: 'Link', fieldname: 'from_wh', label: __('From Warehouse'), options: 'Warehouse',
                  depends_on: 'eval:' + T, mandatory_depends_on: 'eval:' + T,
                  get_query: () => ({ filters: { is_group: 0, disabled: 0 } }) },
                { fieldtype: 'Float', fieldname: 'qty', label: __('Qty'), default: 1, depends_on: 'eval:' + T + ' && !doc.as_asset' },
                { fieldtype: 'Check', fieldname: 'as_asset', label: __('Register this unit as an Asset (capitalize from stock)'),
                  depends_on: 'eval:' + T },
                { fieldtype: 'Link', fieldname: 'store_location', label: __('Asset Location (store)'), options: 'Location',
                  depends_on: 'eval:' + T + ' && doc.as_asset', mandatory_depends_on: 'eval:' + T + ' && doc.as_asset' },
                { fieldtype: 'Data', fieldname: 'tag', label: __('Asset Tag / Serial'), depends_on: 'eval:' + T + ' && doc.as_asset' },
                // --- Asset ---
                { fieldtype: 'Link', fieldname: 'asset', label: __('Asset (tag / serial)'), options: 'Asset',
                  depends_on: 'eval:' + A, mandatory_depends_on: 'eval:' + A,
                  get_query: () => ({ filters: { docstatus: 1, item_code: d.get_value('item_code') } }),
                  change() {
                      const v = d.get_value('asset');
                      if (!v) return;
                      frappe.db.get_value('Asset', v, ['asset_name', 'location', 'custom_custody_status', 'custom_custodian_employee']).then(r => {
                          const a = r.message || {};
                          d.set_df_property('info', 'options', `<b>${frappe.utils.escape_html(a.asset_name || '')}</b> - ${__('at')} ${frappe.utils.escape_html(a.location || '-')} - ${__('custody')}: ${frappe.utils.escape_html(a.custom_custody_status || 'In Store')} ${frappe.utils.escape_html(a.custom_custodian_employee || '')}`);
                          d.refresh();
                      });
                  } },
                { fieldtype: 'HTML', fieldname: 'info', depends_on: 'eval:' + A },
                { fieldtype: 'Column Break' },
                // --- Destination ---
                { fieldtype: 'Select', fieldname: 'custodian_type', label: __('Custodian'), options: ['Employee', 'Other'],
                  default: 'Employee', depends_on: 'eval:' + T },
                { fieldtype: 'Select', fieldname: 'dest_type', label: __('To'), options: ['Employee', 'Site', 'Subcontractor'],
                  default: 'Employee', depends_on: 'eval:' + AD },
                { fieldtype: 'Link', fieldname: 'custodian', label: __('Employee'), options: 'Employee',
                  depends_on: 'eval:' + TE, mandatory_depends_on: 'eval:' + TE },
                { fieldtype: 'Link', fieldname: 'employee', label: __('Employee'), options: 'Employee',
                  depends_on: 'eval:' + AD + ' && doc.dest_type=="Employee"',
                  mandatory_depends_on: 'eval:' + AD + ' && doc.dest_type=="Employee"' },
                { fieldtype: 'Data', fieldname: 'custodian_name', label: __('Name'), depends_on: 'eval:' + TO, mandatory_depends_on: 'eval:' + TO },
                { fieldtype: 'Data', fieldname: 'custodian_phone', label: __('Phone'), depends_on: 'eval:' + TO },
                { fieldtype: 'Link', fieldname: 'location', label: __('Destination Location'), options: 'Location',
                  depends_on: 'eval:' + AD + ' && doc.dest_type!="Employee"',
                  mandatory_depends_on: 'eval:' + AD + ' && doc.dest_type!="Employee"' },
                { fieldtype: 'Link', fieldname: 'sig_site', label: __('SIG Site'), options: 'SIG Site',
                  depends_on: 'eval:' + AD + ' && doc.dest_type=="Site"' },
                { fieldtype: 'Link', fieldname: 'to_location', label: __('Return to Location'), options: 'Location',
                  depends_on: 'eval:' + AR, mandatory_depends_on: 'eval:' + AR },
                { fieldtype: 'Select', fieldname: 'condition', label: __('Condition on Return'),
                  options: ['Good', 'Needs Repair', 'Damaged', 'Unserviceable'], default: 'Good', depends_on: 'eval:' + AR },
                { fieldtype: 'Date', fieldname: 'expected_return', label: __('Expected Return'), depends_on: 'eval:' + AD },
                { fieldtype: 'Data', fieldname: 'handover_ref', label: __('Handover Ref'), depends_on: 'eval:' + A },
                { fieldtype: 'Section Break' },
                { fieldtype: 'Small Text', fieldname: 'reason', label: __('Reason / Remarks') },
            ],
            primary_action_label: __('Confirm'),
            primary_action(v) { (v.kind === 'Asset' ? sig_submit_asset_dispatch : sig_submit_tool_dispatch)(d, v); },
        });
        d.show();
    }

    // Stock -> Asset: capitalize one unit of the stock Item (Asset Capitalization,
    // native). The new Asset is dispatched afterwards by picking its FA- item.
    function sig_submit_tool_capitalize(d, v) {
        const opId = sig_gen_operation_id('CAP-' + v.from_wh);
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.asset_ops.sig_capitalize_tool',
            args: { operation_id: opId, stock_item: v.item_code, warehouse: v.from_wh, location: v.store_location,
                    tag: v.tag, remarks: v.reason },
            freeze: true, freeze_message: __('Capitalizing...'),
            callback: (r) => {
                const res = r.message || {};
                if (res.result !== 'created' && res.result !== 'duplicate') {
                    frappe.msgprint({ title: __('Failed'), indicator: 'red', message: frappe.utils.escape_html(JSON.stringify(res)) });
                    return;
                }
                frappe.msgprint({ title: __('Asset created'), indicator: 'green',
                    message: __('Asset {0} created from stock (Asset Capitalization {1}). Dispatch it by picking its FA- item.',
                        [`<a href="/app/asset/${res.asset}">${res.asset}</a>`, res.asset_capitalization]) });
                d.hide();
            },
        });
    }

    function sig_submit_tool_dispatch(d, values) {
        if (values.as_asset) return sig_submit_tool_capitalize(d, values);
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
                            frappe.msgprint({ title: __('Dispatch failed'), indicator: 'red', message: frappe.utils.escape_html(JSON.stringify(res)) });
                        }
                    },
                });
            }
        );
    }

    function sig_submit_asset_dispatch(d, v) {
        const ret = v.mode === 'Return';
        frappe.call({
            method: 'sig_warehouse.sig_warehouse.asset_ops.' + (ret ? 'sig_return_asset' : 'sig_dispatch_asset'),
            args: ret
                ? { operation_id: sig_gen_operation_id('ASSET-R-' + v.asset), asset: v.asset, to_location: v.to_location,
                    condition: v.condition, handover_ref: v.handover_ref, remarks: v.reason }
                : { operation_id: sig_gen_operation_id('ASSET-D-' + v.asset), asset: v.asset, dest_type: v.dest_type,
                    employee: v.employee, location: v.location, sig_site: v.sig_site,
                    expected_return: v.expected_return, handover_ref: v.handover_ref, remarks: v.reason },
            freeze: true, freeze_message: __('Submitting...'),
            callback: (r) => {
                const res = r.message || {};
                if (res.result === 'created' || res.result === 'duplicate') {
                    frappe.msgprint({ title: __('Done'), indicator: 'green',
                        message: __('Asset Movement {0} submitted.', [`<a href="/app/asset-movement/${res.asset_movement}">${res.asset_movement}</a>`]) });
                    d.hide();
                } else {
                    frappe.msgprint({ title: __('Failed'), indicator: 'red', message: frappe.utils.escape_html(JSON.stringify(res)) });
                }
            },
        });
    }

    function ensure_dispatch_tool_button() {
        if (document.getElementById('sig-dispatch-tool-btn')) return;
        const $searchBox = $('.sig-kanban-search');
        if (!$searchBox.length) return; // search box goes in first; button sits after it
        const $btn = $(`<button type="button" id="sig-dispatch-tool-btn" class="btn btn-default btn-sm" style="margin: 0 15px 10px;">
            ${__('Dispatch / Return')}
        </button>`);
        $searchBox.after($btn);
        $btn.on('click', () => sig_open_custody_dialog());
    }

    // ---------------------------------------------------------------------
    // Per-card actions. Repurposes Frappe's native card-corner "+" (normally
    // "assign this document to a user" - .kanban-assignments/.avatar-action
    // in the live DOM) into the Dispatch/Return/Cancel action menu instead:
    // no assign-to-user workflow is needed here, and the single obvious way
    // to act on a card should be its own "+", not a second icon next to an
    // unrelated native one. Bound on the capture phase so this runs before
    // Frappe's own delegated click handler ever sees the event. This is a
    // document-level listener guarded by a one-time flag - unlike the
    // painting/search/availability work above, it does not depend on which
    // `.kanban` node currently exists (it re-checks `.closest('.kanban')` at
    // click time), so it is bound once at bootstrap, not inside decorate().
    // ---------------------------------------------------------------------
    function bind_card_actions_once() {
        if (document.__sigKanbanActionCaptureBound) return;
        document.__sigKanbanActionCaptureBound = true;
        document.addEventListener('click', function (e) {
            const target = e.target && e.target.closest && e.target.closest('.kanban-assignments');
            if (!target || !target.closest('.kanban')) return;
            const card = target.closest('.kanban-card-wrapper');
            if (!card || !card.getAttribute('data-name')) return;
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            sig_show_kanban_action_menu($(target), card.getAttribute('data-name'));
        }, true);
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
        // Calls the single MR-dispatch implementation exported by
        // material_request.js (see the header comment). Guarded in case that
        // file has not evaluated yet for some reason - fails safe with a
        // message instead of throwing.
        if (window.sig_wh && window.sig_wh.open_mr_dispatch) {
            window.sig_wh.open_mr_dispatch({ doc, reload_doc: () => {} });
        } else {
            frappe.msgprint(__('Dispatch module still loading - try again in a moment.'));
        }
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
                                    invalidate_availability(doc.name);
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
                            sig_open_kanban_return_dialog(se, doc.name);
                        },
                    });
                    d.show();
                    return;
                }
                sig_open_kanban_return_dialog(ses[0], doc.name);
            },
        });
    }

    function sig_open_kanban_return_dialog(sourceSe, mrName) {
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
                                            invalidate_availability(mrName);
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

    // ---------------------------------------------------------------------
    // Bootstrap. One debounced MutationObserver on the stable
    // `.page-container[data-page-route=...]` node - not on the `.kanban`
    // node itself, which Frappe replaces wholesale on redraw, and not a
    // 1-second poll. `decorate()` re-verifies the container is still in the
    // document on every run and re-binds if not, so this self-heals without
    // any interval. Route changes still trigger a re-bind because Frappe
    // does not always keep the same page-container instance across a full
    // navigation away and back.
    // ---------------------------------------------------------------------
    let sig_observed_container = null;
    let sig_decorate_timer = null;

    function schedule_decorate() {
        clearTimeout(sig_decorate_timer);
        sig_decorate_timer = setTimeout(decorate, 150);
    }

    function ensure_observer() {
        if (!on_our_route()) return;
        const pc = document.querySelector(`.page-container[data-page-route="${ROUTE}"]`);
        if (!pc) return;
        if (pc === sig_observed_container) { schedule_decorate(); return; }
        if (sig_observed_container && sig_observed_container.__sigKanbanObserver) {
            sig_observed_container.__sigKanbanObserver.disconnect();
        }
        const observer = new MutationObserver(schedule_decorate);
        observer.observe(pc, { childList: true, subtree: true });
        pc.__sigKanbanObserver = observer;
        sig_observed_container = pc;
        schedule_decorate();
    }

    function decorate() {
        if (!on_our_route()) return;
        if (!sig_observed_container || !document.body.contains(sig_observed_container)) {
            ensure_observer();
            if (!sig_observed_container) return;
        }
        const $board = $(sig_observed_container).find('.kanban').first();
        if (!$board.length) return;
        ensure_style_once();
        ensure_search_box($board);
        ensure_dispatch_tool_button();
        apply_search_filter($board);
        paint_badges_and_borders($board);
        refresh_availability($board);
    }

    window.sig_wh = Object.assign(window.sig_wh || {}, { invalidate_availability });

    bind_card_actions_once();
    frappe.router.on('change', () => setTimeout(ensure_observer, 0));
    ensure_observer();
})();
