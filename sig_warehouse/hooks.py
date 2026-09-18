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

# doctype_list_js intentionally NOT registered right now: enabling it
# (2026-09-18) made the live Kanban board's tab become unresponsive to any
# further script injection on the real board (216 cards) - root cause not
# yet confirmed (a fix for one identified feedback loop in
# sig_refresh_kanban_availability did not resolve it, so something else is
# also at fault). Pulled from production as a safety measure until the real
# cause is found and verified fixed against the live card count, not a
# smaller test board. material_request_list.js itself is left in place,
# just not wired up - re-enable this dict only after that verification.
# doctype_list_js = {
#     "Material Request": "public/js/material_request_list.js",
# }

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
