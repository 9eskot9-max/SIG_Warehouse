app_name = "sig_warehouse"
app_title = "SIG Warehouse"
app_publisher = "SIG"
app_description = "ERP-native warehouse workbench: dispatch, returns and custody for ERPNext"
app_email = "it@sigtele.com"
app_license = "mit"

doctype_js = {
    "Material Request": "public/js/material_request.js",
    "Stock Entry": "public/js/stock_entry.js",
}

# Root cause of the 2026-09-18 freeze found and fixed (isolated offline
# repro against 216 mock cards, no live server involved): sig_setup_kanban_
# updates wrote $badge.text(count) unconditionally on every call. .text()
# replaces the DOM text node even when the value is unchanged - a real
# childList mutation - and this ran inside a MutationObserver watching
# childList:true, so every write re-triggered the observer, forever. This
# line predates this session's availability-dot work entirely; it was only
# ever exposed once two earlier, unrelated bugs (wrong hook, then a
# TDZ ordering crash) stopped preventing the script from running at all.
# Fixed by only writing when the value actually changes - repro confirmed
# clean afterward (2 update() calls total, matching expectations, vs 2000+
# before).
#
# NOT using doctype_list_js for material_request_list.js (2026-09-19):
# confirmed live that Frappe only reliably evaluates a doctype's __list_js
# when its full meta happens to already be cached - e.g. switching from the
# plain List view to the Kanban sub-view client-side works, because the
# List view's own load already pulled it in - but a direct page load or a
# plain reload of the Kanban URL itself does not reliably trigger it, so
# the whole enhancement (including the availability dots) silently doesn't
# run on a fresh visit. app_include_js loads unconditionally on every desk
# page instead, sidestepping that lazy-meta dependency entirely; the file's
# own sig_maybe_setup_kanban() already checks frappe.get_route() before
# doing anything, so it is a safe no-op everywhere except this one board.
# Version query forces Desk clients/CDNs to fetch the current bundle after a
# deploy; the unversioned app-included URL can remain cached for a long time.
app_include_js = ["/assets/sig_warehouse/js/material_request_list.js?v=20260921-1"]

doc_events = {
    "Stock Entry": {
        # Child-line custom_site is the authoritative allocation.  A
        # single-site entry gets a header summary at insert time so normal
        # Stock Entry search/filtering finds it too; multi-site entries stay
        # header-blank rather than being assigned a misleading first site.
        "before_insert": "sig_warehouse.sig_warehouse.site_material_issue.sync_stock_entry_site_summary",
        "on_submit": "sig_warehouse.sig_warehouse.rollup.on_stock_entry_submit",
        "on_cancel": "sig_warehouse.sig_warehouse.rollup.on_stock_entry_cancel",
    },
    "Material Request": {
        "validate": "sig_warehouse.sig_warehouse.rollup.set_display_title",
        "on_submit": "sig_warehouse.sig_warehouse.rollup.on_material_request_submit",
        "on_cancel": "sig_warehouse.sig_warehouse.rollup.on_material_request_cancel",
        "on_update_after_submit": "sig_warehouse.sig_warehouse.rollup.on_material_request_update_after_submit",
    },
}
