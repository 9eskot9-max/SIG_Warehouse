import json

import frappe
from frappe.model.document import Document


class SIGPlannerPosition(Document):
    """Append-only PM-confirmed last-known position for a deployed Project team."""

    def validate(self):
        if not self.is_new():
            frappe.throw("Planner positions are a log. Add a new update instead of editing this record.")
        config = frappe.db.get_single_value("SIG Excel Setup", "configuration_json") or "{}"
        try:
            teams = json.loads(config).get("teams", [])
        except (TypeError, ValueError):
            teams = []
        allowed = {str(row.get("leader")) for row in teams
                   if row.get("enabled") and row.get("leader") and (row.get("archetype") or "Project") == "Project"}
        if self.team_leader not in allowed:
            frappe.throw("Select an enabled Project team from Excel Setup.")
        if not self.site or not frappe.db.exists("SIG Site", self.site):
            frappe.throw("Select a valid ERP Site.")
        coordinates = frappe.db.get_value("SIG Site", self.site, ["site_latitude", "site_longitude"], as_dict=True)
        if not coordinates or coordinates.site_latitude in (None, "") or coordinates.site_longitude in (None, ""):
            frappe.throw("The selected ERP Site needs coordinates before it can be a planner position.")
        self.updated_by = frappe.session.user
        self.updated_at = frappe.utils.now_datetime()

    def on_trash(self):
        frappe.throw("Planner position records are an audit log and cannot be deleted.")
