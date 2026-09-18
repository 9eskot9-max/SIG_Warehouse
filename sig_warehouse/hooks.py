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
# before). Re-enabled after that verification.
doctype_list_js = {
    "Material Request": "public/js/material_request_list.js",
}

doc_events = {
    "Stock Entry": {
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
