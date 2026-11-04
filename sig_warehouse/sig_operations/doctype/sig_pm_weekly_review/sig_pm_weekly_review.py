"""One PM's weekly check. Saving a Box 2 decision writes the existing SIG Plan Decision through the planner's own
endpoint, so the planner sees it the same way as a decision made on the Field Planner page."""
import frappe
from frappe import _
from frappe.model.document import Document


class SIGPMWeeklyReview(Document):
    def validate(self):
        from sig_warehouse.sig_operations.pm_weekly_logic import valid_score
        if not valid_score(self.trust_score):
            frappe.throw(_("The score must be between 1 and 5."))

    def on_update(self):
        from sig_warehouse.sig_warehouse.field_planner_api import set_plan_decision
        for line in self.get("this_week_lines") or []:
            if not line.decision or line.recorded or not line.cycle:
                continue
            set_plan_decision(line.cycle, line.decision, reason=(line.note or line.reason or "")[:140])
            frappe.db.set_value("SIG PM Weekly Line", line.name, "recorded", 1, update_modified=False)
        if self.trust_score and self.status == "Sent":
            frappe.db.set_value("SIG PM Weekly Review", self.name, "status", "Answered", update_modified=False)
