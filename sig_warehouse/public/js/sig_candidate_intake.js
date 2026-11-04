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
                const label = frm.doc.consent_to_contact ? __("Send or retry EMP-DATA request") : __("Send WhatsApp confirmation request");
                frm.add_custom_button(label, () => {
                    frappe.confirm(
                        frm.doc.consent_to_contact
                            ? __("Send any missing instructions or EMP-DATA message to the confirmed number?")
                            : __("Send the neutral number confirmation message to the saved WhatsApp phone?"),
                        () => frappe.call({
                            method: "sig_warehouse.sig_hr.candidate_intake.send_candidate_messages",
                            args: { candidate: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Sending the confirmation request…"),
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
                        __("Create one Active Employee from the HR approved fields? User, salary assignment, custody account, mappings, and messages remain separate gates."),
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
        }
    },
});
