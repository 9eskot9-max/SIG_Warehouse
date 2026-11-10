frappe.ui.form.on("SIG Candidate Intake", {
    refresh(frm) {
        if (frm.is_new()) return;
        if (["HR Manager", "System Manager"].some((role) => frappe.user.has_role(role))) {
            if (frm.doc.duplicate_status === "Review Required") {
                frm.add_custom_button(__("Resolve Phone Review"), () => {
                    frappe.prompt(
                        [{ fieldname: "reason", fieldtype: "Small Text", label: __("Review Evidence and Decision"), reqd: 1 }],
                        (values) => frappe.call({
                            method: "sig_warehouse.sig_hr.candidate_intake.resolve_phone_review",
                            args: { candidate: frm.doc.name, resolution_note: values.reason },
                            freeze: true,
                        }).then(() => frm.reload_doc()),
                        __("Resolve Phone Match"),
                        __("Record Review")
                    );
                }, __("HR Review"));
            }
            if (["Draft", "Correction Requested", "Awaiting Candidate"].includes(frm.doc.status) &&
                (!frm.doc.consent_to_contact || !frm.doc.outbound_instructions_sent_at || !frm.doc.outbound_template_sent_at)) {
                const label = __("Send or retry EMP-DATA request");
                frm.add_custom_button(label, () => {
                    frappe.confirm(
                        __("Send the onboarding request to the saved WhatsApp number?"),
                        () => frappe.call({
                            method: "sig_warehouse.sig_hr.candidate_intake.send_candidate_messages",
                            args: { candidate: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Sending the onboarding request…"),
                        }).then((r) => {
                            if (!r.message.accepted) {
                                const message = r.message.throttled
                                    ? __("A message to this number was attempted recently. Wait five minutes before retrying.")
                                    : __("Maytapi did not accept the message. The failure is recorded in the message log.");
                                frappe.msgprint({message, indicator: "red"});
                            } else {
                                const label = r.message.sent === "candidate_data_request"
                                    ? __("Candidate information request sent to {0}", [r.message.phone])
                                    : __("Confirmation request sent to {0}", [r.message.phone]);
                                frappe.show_alert({ message: label, indicator: "green" });
                            }
                            frm.reload_doc();
                        })
                    );
                }, __("WhatsApp"));
            }
            if (frm.doc.status === "HR Review") {
                frm.add_custom_button(__("Approve Candidate"), () => {
                    frappe.confirm(
                        __("Record HR approval for this candidate after reviewing the submitted values and duplicate check?"),
                        () => frappe.call({
                            method: "sig_warehouse.sig_hr.candidate_intake.approve_candidate",
                            args: { candidate: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Recording HR approval…"),
                        }).then(() => frm.reload_doc())
                    );
                }, __("HR Review"));
            }
            if (frm.doc.status === "Approved") {
                frm.add_custom_button(__("Create Employee"), () => {
                    frappe.confirm(
                        __("Create the Employee and ERP User and send the User welcome email? Salary and PC routing are completed separately."),
                        () => frappe.call({
                            method: "sig_warehouse.sig_hr.candidate_intake.create_employee_from_candidate",
                            args: { candidate: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Creating Employee…"),
                        }).then((r) => {
                            const assignment = r.message.project_assignment
                                ? __(" Draft project assignment {0} needs Projects Manager approval.", [r.message.project_assignment])
                                : "";
                            frappe.msgprint({
                                title: __("Employee created"),
                                message: __("Employee {0} created. Verify the SIG Employee Onboarding control row and complete its remaining HR/Finance setup gates.", [r.message.employee]) + assignment,
                                indicator: "green",
                            });
                            frm.reload_doc();
                        })
                    );
                }, __("HR Review"));
            }
            if (frm.doc.status === "Employee Created" && frm.doc.pc_work_group && frappe.user.has_role("System Manager")) {
                frm.add_custom_button(__("Preview PC routing"), () => {
                    frappe.call({method: "sig_warehouse.sig_hr.candidate_intake.preview_onboarding_pc_routing", args: {candidate: frm.doc.name}}).then((r) => {
                        const preview = r.message;
                        frappe.confirm(__("This adds {0} reviewer scopes and removes {1}. Publish this PC routing?", [preview.added, preview.removed]), () => {
                            frappe.call({method: "sig_warehouse.sig_hr.candidate_intake.publish_onboarding_pc_routing", args: {candidate: frm.doc.name, base_revision: preview.revision, preview_hash: preview.hash}}).then(() => frappe.show_alert(__("PC routing published")));
                        });
                    });
                }, __("HR Review"));
            }
            if (frm.doc.status === "Employee Created" && frm.doc.salary_structure && frm.doc.salary_effective_date) {
                frm.add_custom_button(__("Create salary assignment"), () => {
                    frappe.confirm(__("Create and submit the salary assignment using the entered salary and effective date?"), () => {
                        frappe.call({method: "sig_warehouse.sig_hr.candidate_intake.create_salary_assignment", args: {candidate: frm.doc.name}}).then((r) => frappe.msgprint(__("Salary assignment {0} created.", [r.message.assignment])));
                    });
                }, __("HR Review"));
            }
        }
    },
});
