"""Whitelisted read-only API for the Field Planner page. Writes nothing; every read uses the caller's permissions."""
import json
import os

import frappe

from sig_warehouse.sig_warehouse import field_planner as planner

PLANNER_ROLES = {"System Manager", "Projects Manager", "Projects User", "SIG Field Ops"}
CYCLE_FIELDS = ["name", "site", "site_id", "project", "po", "erp_project", "stage", "terminal", "tcn_at", "mir_at",
                "first_visit_at", "impl_visits", "tags_at", "planned_start", "last_event_at", "gross_value"]


def _require_access():
    user = frappe.session.user
    roles = set(frappe.get_roles(user)) if user != "Guest" else set()
    if user == "Guest" or not roles.intersection(PLANNER_ROLES) or not frappe.has_permission("SIG Site Cycle", "read"):
        frappe.throw("You need an Operations page role and SIG Site Cycle read access to view the field plan.",
                     frappe.PermissionError)


def _has_field(doctype, fieldname):
    return bool(frappe.get_meta(doctype).get_field(fieldname))


def _number(value, default, minimum=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > minimum else default


def _projects():
    """ERP Projects (name, title, family, agreement/PO) read with the caller's permissions; none if not readable."""
    try:
        return frappe.get_list("Project", fields=["name", "project_name", "custom_project_family", "custom_family",
                                                  "custom_agreement_no"], limit_page_length=0)
    except frappe.PermissionError:
        return []


@frappe.whitelist()
def get_field_plan(week_start=None, teams=None, scope_hours=None, diameter_km=None, project=None):
    """Return the weekly plan: TCN windows are options, trips are placed on the teams that exist, the rest lapse."""
    _require_access()
    today = frappe.utils.getdate(frappe.utils.nowdate())
    start = frappe.utils.getdate(week_start) if week_start else planner.week_start_for(today)
    overrides = {"teams": int(_number(teams, 0)) or None, "scope_hours": _number(scope_hours, 0) or None,
                 "diameter_km": _number(diameter_km, 0) or None}
    overrides = {key: value for key, value in overrides.items() if value}
    params = dict(planner.DEFAULTS, **overrides)

    filters = {"terminal": 0, "stage": ["in", ["2 - Plan", "3 - Handover"]]}
    if project:
        filters["project"] = ["like", "%{0}%".format(project)]
    fields = CYCLE_FIELDS + (["plan_hold"] if _has_field("SIG Site Cycle", "plan_hold") else [])
    cycles = [dict(c) for c in frappe.get_list("SIG Site Cycle", filters=filters, fields=fields, limit_page_length=0)]
    names = [cycle["name"] for cycle in cycles]
    events, visits = [], []
    if names:
        events = frappe.get_list("SIG Evidence Event", filters={"event_code": "TCN_GENERATED", "cycle": ["in", names]},
                                 fields=["cycle", "event_code", "occurred_at", "recorded_at"], limit_page_length=0)
        visits = frappe.get_list("SIG Field Visit", filters={"cycle": ["in", names]}, fields=["cycle", "start_at"],
                                 limit_page_length=0)
    windows = planner.tcn_windows(events, params["tcn_gap_days"])
    visit_days = {}
    for visit in visits:
        visit_days.setdefault(visit.cycle, set()).add(frappe.utils.getdate(visit.start_at))
    candidates, _ = planner.build_candidates(cycles, windows, visit_days, today, params,
                                             planner.index_projects(_projects()), "plan_hold")

    coords = {}
    if _has_field("SIG Site", "site_latitude") and _has_field("SIG Site", "site_longitude") and candidates:
        wanted = sorted({item["site"] for item in candidates})
        for row in frappe.get_list("SIG Site", filters={"name": ["in", wanted]},
                                   fields=["name", "site_latitude", "site_longitude"], limit_page_length=0):
            if row.site_latitude and row.site_longitude:
                coords[(row.name or "").upper()] = (float(row.site_latitude), float(row.site_longitude))

    plan = planner.choose_week(candidates, coords, start, overrides)
    return _present(plan, coords)


@frappe.whitelist()
def get_reference_towns():
    """Static reference towns (zone, overnight base candidates) for the plan map. Read-only file in the app."""
    _require_access()
    with open(os.path.join(os.path.dirname(__file__), "field_planner_towns.json"), encoding="utf-8") as handle:
        return json.load(handle)


def _present(plan, coords):
    trips = []
    for cluster in plan["clusters"]:
        days = cluster.get("days") or []
        trips.append({"id": cluster["id"], "kind": cluster["kind"], "status": cluster.get("status", ""),
                      "team": cluster.get("team"), "first_day": str(days[0]) if days else "",
                      "last_day": str(days[-1]) if days else "", "anchor": str(cluster["anchor"] or ""),
                      "diameter_km": cluster["diameter_km"], "hours": cluster["hours"], "team_days": cluster["team_days"],
                      "best_tier": cluster["best_tier"], "loaded": cluster.get("loaded", False),
                      "value": cluster.get("value"), "priority_label": cluster.get("priority_label", ""),
                      "stops": [{"order": s["order"], "site": s["site"], "lat": coords[s["site"]][0],
                                 "lon": coords[s["site"]][1], "cycle": s["cycle"], "project": s["project"],
                                 "tier": s["tier"], "kind": s.get("kind") or cluster["kind"], "window": s.get("window"),
                                 "reason": s["reason"], "leg_km": s["leg_km"] if s["order"] > 1 else None,
                                 "value": s.get("value"), "must": bool(s.get("must"))}
                                for s in cluster["stops"] if s["site"] in coords]})
    extra = [{"site": s["site"], "cycle": s["cycle"], "project": s["project"], "tier": s["tier"],
              "kind": s.get("kind") or "Committed later", "window": s.get("window"), "reason": s["reason"]}
             for s in plan["later"] + plan["unplaced"]]
    return {"summary": plan["summary"], "params": plan["params"], "trips": trips, "other": extra,
            "tiers": planner.TIER_LABEL, "has_coordinates": bool(coords)}
