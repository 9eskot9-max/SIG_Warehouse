import frappe
from frappe.model.document import Document

from sig_warehouse.sig_hr.employee_setup_logic import overlaps


APPROVER_ROLES = {"System Manager", "Projects Manager"}


class SIGEmployeeProjectAssignment(Document):
    def validate(self):
        self._validate_references()
        self._validate_dates()
        self._validate_approval_transition()
        self._validate_overlap()

    def _validate_references(self):
        employee = frappe.db.get_value("Employee", self.employee, ["employee_name", "status"], as_dict=True)
        if not employee:
            frappe.throw("Select an existing Employee.")
        if self.status == "Active" and employee.status != "Active":
            frappe.throw("Only an Active Employee can have an active project assignment.")
        project = frappe.db.get_value("Project", self.project, ["status"], as_dict=True)
        if not project:
            frappe.throw("Select an existing Project.")
        if self.status == "Active" and project.status in ("Completed", "Cancelled"):
            frappe.throw("A completed or cancelled Project cannot receive an active assignment.")

    def _validate_dates(self):
        if not self.start_date:
            frappe.throw("Start Date is required.")
        if self.status == "Ended" and not self.end_date:
            self.end_date = frappe.utils.getdate()
        if self.end_date and str(self.end_date) < str(self.start_date):
            frappe.throw("End Date must be on or after Start Date.")
        if self.status == "Active" and self.end_date:
            frappe.throw("An active assignment must have a blank End Date.")

    def _validate_approval_transition(self):
        old = self.get_doc_before_save()
        old_status = old.status if old else None
        if old and old_status in ("Ended", "Cancelled"):
            frappe.throw("Closed assignment history is immutable. Create a new assignment for a later period.")
        if old and old_status == "Active" and any(
            self.get(field) != old.get(field)
            for field in ("employee", "project", "project_role", "start_date", "source")
        ):
            frappe.throw("An approved assignment's employee, project, role, period start, and source are immutable. End it and create a replacement.")
        if old and self.status == "Ended" and old_status != "Active":
            frappe.throw("Only an Active assignment can be ended. Cancel an unapproved Draft instead.")
        if old and self.status == "Cancelled" and old_status != "Draft":
            frappe.throw("Only a Draft assignment can be cancelled.")
        if old and old_status == "Draft" and self.status == "Ended":
            frappe.throw("Cancel an unapproved Draft assignment instead of ending it.")
        if self.status == "Active" and old_status != "Active":
            if not APPROVER_ROLES.intersection(frappe.get_roles()):
                frappe.throw("Only Projects Manager or System Manager can approve an assignment.")
            self.approved_by = frappe.session.user
            self.approved_on = frappe.utils.now_datetime()
        elif old and old_status == "Active" and self.status == "Draft":
            frappe.throw("An active assignment cannot be returned to Draft. End it with an End Date instead.")

    def _validate_overlap(self):
        # Cancelled drafts never represented an effective assignment. Retain
        # them for audit, but do not let them block a later valid assignment.
        if self.status == "Cancelled":
            return
        existing = frappe.get_all(
            "SIG Employee Project Assignment",
            filters={"employee": self.employee, "project": self.project},
            fields=["name", "project_role", "start_date", "end_date", "status"],
            ignore_permissions=True,
        )
        for row in existing:
            if row.name == self.name:
                continue
            if row.status == "Cancelled":
                continue
            if row.project_role != self.project_role:
                continue
            if overlaps(self.start_date, self.end_date, row.start_date, row.end_date):
                frappe.throw("This employee already has an overlapping assignment for the same role and project.")

    def on_trash(self):
        frappe.throw("Project assignment records are an audit trail and cannot be deleted. End an assignment instead.")
