import json

import frappe
from frappe.model.document import Document
from sig_warehouse.sig_warehouse.planner_position_cities import PLANNER_CITY_COORDS


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
        site = str(self.site or "").strip()
        city = str(self.city or "").strip()
        if bool(site) == bool(city):
            frappe.throw("Choose exactly one starting point: an ERP Site or a city.")
        if city and city not in PLANNER_CITY_COORDS:
            frappe.throw("Select a supported planner starting city.")
        if site:
            if not frappe.db.exists("SIG Site", site):
                frappe.throw("Select a valid ERP Site.")
            coordinates = frappe.db.get_value("SIG Site", site, ["site_latitude", "site_longitude"], as_dict=True)
            if not coordinates or coordinates.site_latitude in (None, "") or coordinates.site_longitude in (None, ""):
                frappe.throw("The selected ERP Site needs coordinates before it can be a planner position.")
        self.updated_by = frappe.session.user
        self.updated_at = frappe.utils.now_datetime()

    def on_trash(self):
        frappe.throw("Planner position records are an audit log and cannot be deleted.")
