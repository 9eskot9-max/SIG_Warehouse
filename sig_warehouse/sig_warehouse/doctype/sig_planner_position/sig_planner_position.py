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
            setup = json.loads(config)
            teams = setup.get("teams", [])
        except (TypeError, ValueError):
            setup = {}
            teams = []
        from sig_warehouse.sig_warehouse.people_model_gate import PEOPLE_MODEL_ACTIVE
        all_operational = {str(row.get("id")): row for row in setup.get("operational_teams", []) if row.get("enabled")} if PEOPLE_MODEL_ACTIVE else {}
        operational = {team_id: row for team_id, row in all_operational.items()
                       if (row.get("archetype") or "Project") == "Project"}
        if all_operational:
            today = str(frappe.utils.nowdate())[:10]
            leaders = {}
            for row in setup.get("team_memberships", []):
                start, end = str(row.get("effective_from") or "")[:10], str(row.get("effective_to") or "")[:10]
                if (row.get("enabled") and row.get("role") == "leader" and row.get("team") in operational
                        and row.get("employee") and start and start <= today and (not end or today <= end)):
                    leaders.setdefault(row["team"], set()).add(str(row["employee"]))
            allowed = {next(iter(values)) for values in leaders.values() if len(values) == 1}
        else:
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
