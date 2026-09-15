app_name = "sig_warehouse"
app_title = "SIG Warehouse"
app_publisher = "SIG"
app_description = "ERP-native warehouse workbench: dispatch, returns and custody for ERPNext"
app_email = "it@sigtele.com"
app_license = "mit"

doctype_js = {
    "Material Request": "public/js/material_request.js",
}

doc_events = {
    "Stock Entry": {
        "on_submit": "sig_warehouse.sig_warehouse.rollup.on_stock_entry_submit",
        "on_cancel": "sig_warehouse.sig_warehouse.rollup.on_stock_entry_cancel",
    },
    "Material Request": {
        "on_cancel": "sig_warehouse.sig_warehouse.rollup.on_material_request_cancel",
        "on_update_after_submit": "sig_warehouse.sig_warehouse.rollup.on_material_request_update_after_submit",
    },
}
