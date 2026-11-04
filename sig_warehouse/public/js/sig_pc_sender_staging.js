frappe.ui.form.on("SIG PC Sender Staging", {
    refresh(frm) {
        if (frm.is_new() || frm.doc.employee || frm.doc.status !== "Staged") return;
        if (!frappe.model.can_read("SIG PC Sender Staging") ||
            !["HR Manager", "System Manager"].some((role) => frappe.user.has_role(role))) return;

        frm.add_custom_button(__("Start Candidate Intake"), () => {
            frappe.confirm(
                __("Create a restricted Candidate Intake linked to this sender? This does not send a message or create an Employee."),
                () => frappe.call({
                    method: "sig_warehouse.sig_hr.candidate_intake.start_candidate_from_pc_sender",
                    args: { sender_staging: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Starting Candidate Intake…"),
                }).then((r) => {
                    frappe.set_route("Form", "SIG Candidate Intake", r.message.candidate);
                })
            );
        }, __("HR"));
    },
});
