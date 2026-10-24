"""Whitelisted read-only API for the Field Planner page. Writes nothing; every read uses the caller's permissions."""
import frappe

from sig_warehouse.sig_warehouse import field_planner as planner

PLANNER_ROLES = {"System Manager", "Projects Manager", "Projects User", "SIG Field Ops"}
CYCLE_FIELDS = ["name", "site", "site_id", "project", "stage", "terminal", "tcn_at", "mir_at", "first_visit_at",
                "impl_visits", "tags_at", "planned_start", "last_event_at"]


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


@frappe.whitelist()
def get_field_plan(week_start=None, teams=None, scope_hours=None, diameter_km=None, project=None):
    """Return the weekly proposal from cycles, TCN events, visits and site coordinates the caller may read."""
    _require_access()
    today = frappe.utils.getdate(frappe.utils.nowdate())
    start = frappe.utils.getdate(week_start) if week_start else planner.week_start_for(today)
    overrides = {"teams": int(_number(teams, 0)) or None, "scope_hours": _number(scope_hours, 0) or None,
                 "diameter_km": _number(diameter_km, 0) or None}
    overrides = {key: value for key, value in overrides.items() if value}
    params = dict(planner.DEFAULTS, **overrides)

    mark_field = "plan_hold" if _has_field("SIG Site Cycle", "plan_hold") else None
    filters = {"terminal": 0, "stage": ["in", ["2 - Plan", "3 - Handover"]]}
    if project:
        filters["project"] = ["like", "%{0}%".format(project)]
    cycles = frappe.get_list("SIG Site Cycle", filters=filters, fields=CYCLE_FIELDS + ([mark_field] if mark_field else []),
                             limit_page_length=0)
    names = [cycle.name for cycle in cycles]
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

    candidates = []
    for cycle in cycles:
        window = windows.get(cycle.name)
        tier, reason = planner.classify(cycle, window, visit_days.get(cycle.name, ()), today, params,
                                        (cycle.get(mark_field) if mark_field else "") or "")
        if tier:
            anchor = window["anchor"] if window else (planner._date(cycle.planned_start) if cycle.planned_start else None)
            candidates.append({"site": (cycle.site or cycle.site_id or "").upper(), "cycle": cycle.name, "tier": tier,
                               "reason": reason, "project": cycle.project, "stage": cycle.stage, "anchor": anchor,
                               "window": ("%s to %s" % (window["start"], window["end"])) if window else "",
                               "age": str(cycle.last_event_at or "")[:10]})

    coords = {}
    if _has_field("SIG Site", "latitude") and _has_field("SIG Site", "longitude") and candidates:
        wanted = sorted({item["site"] for item in candidates})
        for row in frappe.get_list("SIG Site", filters={"name": ["in", wanted]}, fields=["name", "latitude", "longitude"],
                                   limit_page_length=0):
            if row.latitude and row.longitude:
                coords[(row.name or "").upper()] = (float(row.latitude), float(row.longitude))

    plan = planner.plan_week(candidates, coords, start, overrides)
    return _present(plan, bool(coords))


def _present(plan, has_coordinates):
    trips = []
    for cluster in plan["clusters"]:
        trips.append({"id": cluster["id"], "kind": cluster["kind"], "anchor": str(cluster["anchor"] or ""),
                      "diameter_km": cluster["diameter_km"], "hours": cluster["hours"], "team_days": cluster["team_days"],
                      "best_tier": cluster["best_tier"], "loaded": cluster["loaded"],
                      "stops": [{"order": s["order"], "site": s["site"], "cycle": s["cycle"], "project": s["project"],
                                 "tier": s["tier"], "kind": s.get("kind") or cluster["kind"], "window": s.get("window"),
                                 "reason": s["reason"], "leg_km": s["leg_km"] if s["order"] > 1 else None}
                                for s in cluster["stops"]]})
    extra = [{"site": s["site"], "cycle": s["cycle"], "project": s["project"], "tier": s["tier"],
              "kind": s.get("kind") or "Committed later", "window": s.get("window"), "reason": s["reason"]}
             for s in plan["later"] + plan["unplaced"]]
    return {"summary": plan["summary"], "params": plan["params"], "trips": trips, "other": extra,
            "tiers": planner.TIER_LABEL, "has_coordinates": has_coordinates}
