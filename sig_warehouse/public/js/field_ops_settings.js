frappe.ui.form.on("SIG Field Ops Settings", {
    refresh(frm) {
        frm.set_df_property("nv_lookback_days", "hidden", 1);
        frm.set_df_property("nv_include", "hidden", 1);
        frm.set_df_property("nv_mode", "description", __("Recipients are current leaders of enabled Field crews in Excel Setup. Friday and Saturday are excluded."));
        const call = (mode) => frappe.call({
            method: "sig_warehouse.sig_operations.no_visit_nudge.run_now", args: {mode}, freeze: true,
            callback(r) {
                const d = r.message || {};
                const rows = (d.rows || []).map((x) => `<tr><td>${frappe.utils.escape_html(x.employee_name || x.employee)}</td><td>${x.phone}</td><td>${x.decision}</td><td>${x.reason}</td></tr>`).join("");
                frappe.msgprint({
                    title: __("No-visit message: {0} ({1})", [d.mode, d.day]), wide: true,
                    message: `<p>${__("Would send")}: <b>${d.would_send}</b>${d.sent !== undefined ? ` · ${__("Sent")}: <b>${d.sent}</b>` : ""}${(d.failed || []).length ? ` · ${__("Failed")}: ${d.failed.length}` : ""}</p>`
                        + `<table class="table table-bordered"><tr><th>${__("Employee")}</th><th>${__("Phone")}</th><th>${__("Decision")}</th><th>${__("Reason")}</th></tr>${rows}</table>`
                        + `<pre style="white-space:pre-wrap">${frappe.utils.escape_html(d.text || "")}</pre>`,
                });
            },
        });
        frm.add_custom_button(__("Preview no-visit message"), () => call("preview"), __("No-visit message"));
        frm.add_custom_button(__("Send test to test number"), () => frappe.confirm(
            __("Send the messages to the Maytapi test number only?"), () => call("test")), __("No-visit message"));
    },
});
