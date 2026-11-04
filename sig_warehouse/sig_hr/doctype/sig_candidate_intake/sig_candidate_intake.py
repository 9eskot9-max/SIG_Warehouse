import frappe
from frappe import _
from frappe.model.document import Document


class SIGCandidateIntake(Document):
    def validate(self):
        from sig_warehouse.sig_hr.candidate_intake_logic import normalize_phone

        if self.is_new() and not self.company:
            self.company = frappe.defaults.get_global_default("company")
        if self.is_new() and not self.company:
            frappe.throw(_("Set the ERP default Company before starting candidate intake."))
        if self.is_new() and not self.hr_owner:
            self.hr_owner = frappe.session.user
        old = self.get_doc_before_save()
        if self.is_new() and self.status != "Draft":
            frappe.throw(_("A new Candidate Intake must start in Draft."))
        if old and old.outbound_intro_sent_at and self.whatsapp_phone != old.whatsapp_phone:
            frappe.throw(_("The contacted phone is immutable. Close this case and start a new one for a different number."))
        if old and old.status in ("Approved", "Employee Created"):
            employment_fields = (
                "candidate_name", "whatsapp_phone", "gender", "designation", "proposed_salary",
                "salary_period", "salary_currency", "company", "date_of_joining", "employment_type",
                "department", "reports_to", "project", "project_role", "assignment_start_date",
                "proposed_legal_name", "proposed_preferred_name", "proposed_official_phone",
                "proposed_email", "date_of_birth", "nationality", "identity_type_digit",
            )
            if any(self.get(field) != old.get(field) for field in employment_fields):
                frappe.throw(_("Approved employment fields are locked. Correct the Employee or start a new HR-reviewed case."))
        if old and self.status != old.status and not self.flags.get("allow_intake_status_transition"):
            frappe.throw(_("Change the intake status using its HR action buttons."))
        if old and not self.flags.get("allow_intake_system_fields"):
            protected = (
                "company", "status", "duplicate_status", "duplicate_notes", "last_inbound_at",
                "last_inbound_message_id", "last_parse_result", "outbound_intro_sent_at",
                "outbound_intro_attempted_at", "outbound_instructions_sent_at",
                "outbound_instructions_attempted_at", "outbound_template_sent_at",
                "outbound_template_attempted_at", "inbound_messages",
                "employee", "project_assignment", "consent_to_contact", "phone_control_confirmed",
                "hr_approved_by", "hr_approved_at", "employee_creation_note", "secure_handoff_fields",
                "identity_category", "identity_last4", "iban_last4",
            )
            changed = {field for field in protected if self.get(field) != old.get(field)}
            if self.whatsapp_phone != old.whatsapp_phone:
                changed -= {"duplicate_status", "duplicate_notes"}
            if changed:
                frappe.throw(_("System-managed onboarding fields can only be changed by their HR actions."))
        if self.whatsapp_phone:
            normalized = normalize_phone(self.whatsapp_phone)
            if not normalized:
                frappe.throw(_("Enter a valid mobile number with country code."))
            self.whatsapp_phone = normalized
        if self.sender_staging:
            if not frappe.has_permission("SIG PC Sender Staging", "read"):
                frappe.throw(_("You cannot read petty-cash sender staging."), frappe.PermissionError)
            source = frappe.get_doc("SIG PC Sender Staging", self.sender_staging)
            source.check_permission("read")
            if source.employee:
                frappe.throw(_("The source sender is already linked to an Employee."))
            if normalize_phone(source.sender_phone) != normalize_phone(self.whatsapp_phone):
                frappe.throw(_("The sender record phone must match the Candidate Intake phone."))
        if self.proposed_email:
            self.proposed_email = self.proposed_email.strip().lower()
        if self.proposed_official_phone:
            normalized = normalize_phone(self.proposed_official_phone)
            if not normalized:
                frappe.throw(_("Enter a valid official mobile number with country code."))
            self.proposed_official_phone = normalized
        if self.proposed_salary is not None and float(self.proposed_salary or 0) < 0:
            frappe.throw(_("Proposed salary cannot be negative."))
        self.identity_category = {
            "1": "Saudi National ID",
            "2": "Resident / Iqama",
            "Other": "Compliance Review",
        }.get(self.identity_type_digit, "")
        if self.is_new() or not old or old.whatsapp_phone != self.whatsapp_phone:
            from sig_warehouse.sig_hr.candidate_intake import _set_duplicate_check

            _set_duplicate_check(self)
        if self.status in ("Approved", "Employee Created") and not self.hr_approved_by:
            self.hr_approved_by = frappe.session.user

    def on_trash(self):
        frappe.throw(_("Candidate Intake is an onboarding audit record and cannot be deleted."))
