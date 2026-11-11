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
        return r[0] === 'List' && r[1] === 'Material Request' && r[2] === 'Kanban' && r[3] === 'SIG Dispatch Queue';
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
            ${scope} .kanban .list-comment-count,
            ${scope} .kanban .sig-kanban-count { display: none !important; }
            ${scope} .kanban.sig-search-active .kanban-card-wrapper:not(.sig-search-card) { display: none !important; }
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
            const color = stage_color_for_column($col);
            $col.find('.kanban-cards .kanban-card').css('border-left', color ? `4px solid ${color}` : '');
        });
    }

    // Search the permission-filtered full dataset and render matches in their
    // stages. Native Kanban pagination alone cannot find cards not yet loaded.
    let sig_search_query = '';
    let sig_search_timer = null;
    let sig_search_request = 0;
    let sig_search_rows = [];
    let sig_search_version = 0;
    let sig_search_message = '';

    function ensure_search_box($board) {
        if (document.getElementById('sig-kanban-search-input')) return;
        const $box = $(`<div class="sig-kanban-search" style="margin: 0 15px 10px; max-width: 520px;">
            <input type="search" id="sig-kanban-search-input" class="form-control input-sm" autocomplete="off" placeholder="${__('Search MIR #, MR ID, or site...')}">
            <div class="sig-kanban-search-status text-muted" role="status" aria-live="polite"></div>
        </div>`);
        $board.before($box);
        $box.find('input').val(sig_search_query).on('input', function () {
            sig_search_query = String($(this).val() || '').trim().toLowerCase();
            clearTimeout(sig_search_timer);
            const requestId = ++sig_search_request;
            sig_search_rows = [];
            sig_search_version++;
            sig_search_message = sig_search_query.length === 1 ? __('Enter at least 2 characters to search.') :
                sig_search_query ? __('Searching...') : '';
            apply_search_filter($('.kanban').first());
            if (sig_search_query.length >= 2) {
                const query = sig_search_query;
                sig_search_timer = setTimeout(() => search_dispatch_records(query, requestId), 250);
            }
        });
        $box.find('input').on('keydown', function (event) {
            if (event.key === 'Escape') { $(this).val('').trigger('input'); }
        });
    }

    function search_dispatch_records(query, requestId) {
        const like = `%${query.replace(/[\\%_]/g, '\\$&')}%`;
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Material Request',
                fields: ['name', 'custom_mir_number', 'custom_site', 'custom_dispatch_stage'],
                filters: [['docstatus', '=', 1], ['material_request_type', '=', 'Material Issue']],
                or_filters: [
                    ['name', 'like', like],
                    ['custom_mir_number', 'like', like],
                    ['custom_site', 'like', like],
                ],
                order_by: 'modified desc',
                limit_page_length: 100,
            },
            callback: (response) => {
                if (requestId !== sig_search_request || query !== sig_search_query) return;
                sig_search_rows = response.message || [];
                sig_search_message = !sig_search_rows.length ? __('No matching submitted Material Issues found.') :
                    sig_search_rows.length === 100 ? __('Showing the first 100 matches. Refine your search for more specific results.') : '';
                sig_search_version++;
                apply_search_filter($('.kanban').first());
                refresh_availability($('.kanban').first());
            },
            error: () => {
                if (requestId !== sig_search_request || query !== sig_search_query) return;
                sig_search_rows = [];
                sig_search_message = __('Search failed. Check your access and try again.');
                sig_search_version++;
                apply_search_filter($('.kanban').first());
            },
        });
    }

    function apply_search_filter($board) {
        if (!$board || !$board.length) return;
        const active = sig_search_query.length > 0;
        $board.toggleClass('sig-search-active', active);
        const $status = $('.sig-kanban-search-status').first();
        // Rebuild only for a new response or a replaced board. The observer
        // also sees our own insertions; repeated replacement would flicker.
        if ($board.data('sig-search-version') === sig_search_version &&
            $board.find('.sig-search-card').length === ($board.data('sig-search-rendered') || 0)) return;
        $board.data('sig-search-version', sig_search_version);
        $board.find('.sig-search-card').remove();
        if (!active) {
            $board.data('sig-search-rendered', 0);
            if ($status.text() !== sig_search_message) $status.text(sig_search_message);
            return;
        }
        let rendered = 0;
        sig_search_rows.forEach((row) => {
            const stage = String(row.custom_dispatch_stage || 'PENDING').trim().toUpperCase();
            const $column = $board.find('.kanban-column').filter(function () {
                return String($(this).attr('data-column-value') || $(this).find('.kanban-title').first().text()).trim().toUpperCase() === stage;
            }).first();
            const $container = $column.find('.kanban-cards').first();
            if (!$container.length) return;
            const $card = $('<div class="kanban-card-wrapper sig-search-card"><div class="kanban-card content"><div class="sig-search-card-title"></div><div class="sig-search-card-meta text-muted"></div><button type="button" class="kanban-assignments btn btn-default btn-xs" aria-label="Actions">+</button></div></div>');
            $card.attr('data-name', encodeURIComponent(row.name));
            $card.find('.sig-search-card-title').text([row.name, row.custom_site].filter(Boolean).join(' '));
            $card.find('.sig-search-card-meta').text(row.custom_mir_number ? `MIR ${row.custom_mir_number}` : '');
            $card.find('.kanban-card').css('border-left', `4px solid ${SIG_STAGE_COLORS[stage] || '#94a3b8'}`);
            $card.on('click', function (event) { event.stopPropagation(); frappe.set_route('Form', 'Material Request', row.name); });
            $container.append($card);
            rendered++;
        });
        $board.data('sig-search-rendered', rendered);
        const message = rendered < sig_search_rows.length ?
            __('Some matches have a dispatch stage that is not shown on this board.') : sig_search_message;
        if ($status.text() !== message) $status.text(message);
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
        const names = [...new Set($board.find(sig_search_query ? '.sig-search-card' : '.kanban-card-wrapper:not(.sig-search-card)').map(function () {
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

    function ensure_dispatch_tool_button() {
        if (document.getElementById('sig-dispatch-tool-btn')) return;
        const $searchBox = $('.sig-kanban-search');
        if (!$searchBox.length) return; // search box goes in first; button sits after it
        const $btn = $(`<button type="button" id="sig-dispatch-tool-btn" class="btn btn-default btn-sm" style="margin: 0 15px 10px;">
            ${__('Dispatch / Return')}
        </button>`);
        $searchBox.after($btn);
        $btn.on('click', () => (window.sig_wh && window.sig_wh.open_custody_dialog ? window.sig_wh.open_custody_dialog() : frappe.msgprint(__('Dispatch module still loading - try again in a moment.'))));
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
                    actions.push([__('Cancel remaining'), () => (window.sig_wh && window.sig_wh.open_mr_cancel ? window.sig_wh.open_mr_cancel(doc) : frappe.msgprint(__('Cancel module still loading - try again in a moment.')))]);
                } else if (stage === 'PARTIAL') {
                    actions.push([__('Issue'), () => sig_kanban_dispatch(doc)]);
                    actions.push([__('Return'), () => sig_kanban_return(doc)]);
                    actions.push([__('Cancel remaining'), () => (window.sig_wh && window.sig_wh.open_mr_cancel ? window.sig_wh.open_mr_cancel(doc) : frappe.msgprint(__('Cancel module still loading - try again in a moment.')))]);
                } else if (stage === 'DISPATCHED') {
                    actions.push([__('Return'), () => sig_kanban_return(doc)]);
                } else {
                    // CLOSED (or any other stage): nothing to issue or cancel, but a return
                    // that was never declared can still be entered.
                    actions.push([__('Return'), () => sig_kanban_return(doc)]);
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

    function sig_kanban_return(doc) {
        // Same MR-level return entry point as the form's Manage > Return
        // (material_request.js): finds the dispatch Stock Entry(ies) through
        // the rows' own MR link, so it also works for MRs dispatched outside
        // the Kanban flow.
        if (window.sig_wh && window.sig_wh.open_mr_return) {
            window.sig_wh.open_mr_return(doc.name, () => invalidate_availability(doc.name));
        } else {
            frappe.msgprint(__('Return module still loading - try again in a moment.'));
        }
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

    function wait_for_board(attempts = 0) {
        if (!on_our_route()) return;
        const pc = document.querySelector(`.page-container[data-page-route="${ROUTE}"]`);
        if (pc) {
            ensure_observer();
            return;
        }
        // The router event can fire before Frappe inserts the page container.
        // Retry briefly after navigation instead of silently missing a direct
        // Kanban URL load for the lifetime of the Desk tab.
        if (attempts < 40) setTimeout(() => wait_for_board(attempts + 1), 100);
    }

    bind_card_actions_once();
    frappe.router.on('change', () => wait_for_board());
    wait_for_board();
})();
