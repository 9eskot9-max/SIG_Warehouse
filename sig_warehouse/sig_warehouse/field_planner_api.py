"""Whitelisted read-only API for the Field Planner page. Writes nothing; every read uses the caller's permissions."""
import json
import os

import frappe

from sig_warehouse.sig_warehouse import continuity
from sig_warehouse.sig_warehouse import field_planner as planner

PLANNER_ROLES = {"System Manager", "Projects Manager", "Projects User", "SIG Field Ops"}
CYCLE_FIELDS = ["name", "site", "site_id", "project", "po", "erp_project", "stage", "terminal", "tcn_at", "mir_at",
                "first_visit_at", "last_visit_at", "ho_at", "impl_visits", "tags_at", "planned_start", "last_event_at", "gross_value"]


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


def _decisions(names):
    """The PM decision log for these cycles, newest first, read with the caller's permissions."""
    if not names:
        return {}
    rows = frappe.get_list("SIG Plan Decision", filters={"cycle": ["in", names]},
                           fields=["cycle", "action", "reason", "until", "decided_at"], order_by="decided_at desc",
                           limit_page_length=0)
    out = {}
    for r in rows:
        out.setdefault(r.cycle, []).append({"action": r.action or "", "reason": r.reason, "until": r.until,
                                            "created": r.decided_at})
    return out


@frappe.whitelist(methods=["POST"])
def set_plan_decision(cycle, action="", reason=""):
    """Record one PM decision for a cycle: Must, Hold, Remove, or blank to clear. Saved at once, logged, never edited."""
    _require_access()
    if action not in ("", "Must", "Hold", "Remove"):
        frappe.throw("Unknown plan decision.")
    if not frappe.db.exists("SIG Site Cycle", cycle):
        frappe.throw("The site cycle no longer exists. Refresh the plan.")
    if not frappe.has_permission("SIG Site Cycle", "read", cycle):
        frappe.throw("You cannot view this cycle.", frappe.PermissionError)
    if not frappe.has_permission("SIG Plan Decision", "create"):
        frappe.throw("You cannot record a planner decision.", frappe.PermissionError)
    today = frappe.utils.getdate(frappe.utils.nowdate())
    doc = frappe.get_doc({
        "doctype": "SIG Plan Decision", "cycle": cycle,
        "site_key": frappe.db.get_value("SIG Site Cycle", cycle, "site_key"),
        "action": action, "reason": (reason or "")[:140],
        "until": frappe.utils.add_days(today, 30) if action == "Hold" else None,
        "decided_by": frappe.session.user, "decided_at": frappe.utils.now_datetime(),
    })
    doc.insert()
    # The append-only Planner Decision is authoritative. This endpoint mirrors
    # its current value for the cycle form; no general cycle-write grant is needed.
    frappe.db.set_value("SIG Site Cycle", cycle, "plan_hold", action, update_modified=False)
    return {"name": doc.name, "action": action}


def _team_setup():
    """Enabled field teams from the published Excel Setup (a team is its leader).

    Read straight from the published setup so planner roles need no Excel Setup access; only the leader, team name
    and phone leave this function, and callers are already limited to PLANNER_ROLES.
    """
    try:
        data = json.loads(frappe.db.get_single_value("SIG Excel Setup", "configuration_json") or "{}")
    except (ValueError, frappe.DoesNotExistError):
        return []
    return [{"leader": r["leader"], "team": r.get("team") or r["leader"], "phone": r.get("phone", ""),
             "archetype": r.get("archetype") or "Project"}
            for r in data.get("teams", []) if r.get("enabled") and r.get("leader")]


def _projects():
    """ERP Projects (name, title, family, agreement/PO) read with the caller's permissions; none if not readable."""
    try:
        return frappe.get_list("Project", fields=["name", "project_name", "custom_project_family", "custom_family",
                                                  "custom_agreement_no"], limit_page_length=0)
    except frappe.PermissionError:
        return []


def _position_team_roster():
    """Enabled Project teams, keyed by the Employee ID recorded in Field Visits."""
    return {row["leader"]: row for row in _team_setup()
            if row["archetype"] == "Project"}


def _latest_manual_positions(leaders):
    if not leaders:
        return {}
    # Planner audience is explicitly role-gated; per-user Employee Link filters
    # must not hide the other enabled field teams from this aggregate view.
    rows = frappe.get_all("SIG Planner Position", filters={"team_leader": ["in", leaders]},
                          fields=["team_leader", "site", "updated_at", "updated_by"],
                          order_by="updated_at desc", limit_page_length=500)
    latest = {}
    for row in rows:
        latest.setdefault(row.team_leader, dict(row))
    return latest


def _set_manual_position(position, manual, coords, today):
    """A newer PM update replaces the displayed last-known site, without editing visit evidence."""
    if not manual:
        return
    site = (manual.get("site") or "").upper()
    stamp = str(manual.get("updated_at") or "")[:19]
    if not site or not stamp or site not in coords:
        return
    if stamp >= str(position.get("seen_at") or "")[:19]:
        position["site"] = site
        position["seen_at"] = stamp
        position["on_site"] = False
        position["source"] = "PM update"
        position["updated_by"] = manual.get("updated_by") or ""
        position["lat"], position["lon"] = coords[site]
        position["age_days"] = (today - frappe.utils.getdate(stamp)).days
        position["state"] = "Current" if position["age_days"] <= 14 else "Stale"


def _require_position_manager():
    roles = set(frappe.get_roles(frappe.session.user)) if frappe.session.user != "Guest" else set()
    if not roles.intersection({"System Manager", "Projects Manager"}):
        frappe.throw("Only Project Managers can update a team's planner position.", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def update_team_position(team_leader, site):
    """Append a PM-confirmed last-known site for one enabled Project team."""
    _require_position_manager()
    roster = _position_team_roster()
    team_leader = str(team_leader or "").strip()
    site = str(site or "").strip()
    if team_leader not in roster:
        frappe.throw("Select an enabled Project team from Excel Setup.")
    if not site or not frappe.db.exists("SIG Site", site):
        frappe.throw("Select a site from the ERP Site list.")
    if not frappe.has_permission("SIG Site", "read", site):
        frappe.throw("You do not have read access to the selected ERP Site.", frappe.PermissionError)
    coords = frappe.db.get_value("SIG Site", site, ["site_latitude", "site_longitude"], as_dict=True)
    if not coords or coords.site_latitude in (None, "") or coords.site_longitude in (None, ""):
        frappe.throw("This Site has no coordinates, so it cannot be used as a planner starting position.")
    doc = frappe.get_doc({
        "doctype": "SIG Planner Position", "team_leader": team_leader, "site": site,
        "updated_by": frappe.session.user, "updated_at": frappe.utils.now_datetime(),
    })
    doc.insert()
    return {"name": doc.name, "team_leader": team_leader, "team": roster[team_leader]["team"],
            "site": site, "updated_at": str(doc.updated_at)}


@frappe.whitelist()
def get_field_plan(week_start=None, teams=None, scope_hours=None, diameter_km=None, project=None):
    """Return the weekly plan: TCN windows are options, trips are placed on the teams that exist, the rest lapse."""
    _require_access()
    today = frappe.utils.getdate(frappe.utils.nowdate())
    start = frappe.utils.getdate(week_start) if week_start else frappe.utils.add_days(today, 1)
    overrides = {"teams": int(_number(teams, 0)) or None, "scope_hours": _number(scope_hours, 0) or None,
                 "diameter_km": _number(diameter_km, 0) or None}
    overrides = {key: value for key, value in overrides.items() if value}
    params = dict(planner.DEFAULTS, **overrides)

    filters = {"terminal": 0, "stage": ["in", ["2 - Plan", "3 - Handover"]]}
    fields = CYCLE_FIELDS + (["plan_hold"] if _has_field("SIG Site Cycle", "plan_hold") else [])
    cycles = [dict(c) for c in frappe.get_list("SIG Site Cycle", filters=filters, fields=fields, limit_page_length=0)]
    if project:
        # Project is selected from ERP Project's Link search. Match the stable
        # ERP link first, with agreement/PO compatibility for older cycles.
        agreement = frappe.db.get_value("Project", project, "custom_agreement_no")
        cycles = [c for c in cycles if c.get("erp_project") == project
                  or (agreement and str(c.get("po") or "").strip() == str(agreement).strip())]
    names = [cycle["name"] for cycle in cycles]
    events, visits = [], []
    if names:
        events = frappe.get_list("SIG Evidence Event", filters={"event_code": "TCN_GENERATED", "cycle": ["in", names]},
                                 fields=["cycle", "event_code", "occurred_at", "recorded_at"], limit_page_length=0)
        visits = frappe.get_all("SIG Field Visit", filters={"cycle": ["in", names]}, fields=["cycle", "start_at", "status"],
                                limit_page_length=0)
    windows = planner.tcn_windows(events, params["tcn_gap_days"])
    visit_days = {}
    for visit in visits:
        visit_days.setdefault(visit.cycle, set()).add(frappe.utils.getdate(visit.start_at))
    decisions = _decisions(names)
    # This view is for tomorrow-forward field planning. A cycle with an
    # existing visit is complete for the visit-planning queue; a later scope
    # remains eligible under its own cycle.
    visited_cycles = {v.cycle for v in visits if v.get("cycle") and v.get("status") == "COMPLETED"}
    plan_cycles = [c for c in cycles if c["name"] not in visited_cycles]
    candidates, excluded = planner.build_candidates(plan_cycles, windows, visit_days, today, params,
                                                    planner.index_projects(_projects()), "plan_hold", decisions)

    all_teams = _team_setup()
    team_setup = [t for t in all_teams if t["archetype"] == "Project"]     # Incident teams are never planned
    team_visits = []
    manual_positions = _latest_manual_positions([t["leader"] for t in team_setup])
    if all_teams:
        team_visits = [dict(v) for v in frappe.get_all(
            "SIG Field Visit", filters={"employee": ["in", [t["leader"] for t in all_teams]],
                                        "start_at": [">=", frappe.utils.add_days(today, -45)]},
            fields=["employee", "site", "start_at", "end_at", "status"], order_by="start_at desc", limit_page_length=500)]
        team_visits = [dict(v, source="Posted visit") for v in team_visits]
        team_sessions = [dict(v) for v in frappe.get_all(
            "SIG Field Session", filters={"employee": ["in", [t["leader"] for t in all_teams]],
                                           "start_at": [">=", frappe.utils.add_days(today, -45)],
                                           "disposition": ["not in", ["IN_ERP_WINDOW", "VOID"]]},
            fields=["employee", "site", "site_key", "start_at", "end_at", "status", "disposition"],
            order_by="start_at desc", limit_page_length=500)]
        team_visits.extend(dict(v, site=v.get("site") or v.get("site_key"),
                                source="WhatsApp report") for v in team_sessions)

    coords = {}
    if _has_field("SIG Site", "site_latitude") and _has_field("SIG Site", "site_longitude") and (candidates or team_visits or manual_positions):
        wanted = sorted({item["site"] for item in candidates}
                        | {(v["site"] or "").upper() for v in team_visits if v["site"]}
                        | {(p.get("site") or "").upper() for p in manual_positions.values() if p.get("site")})
        for row in frappe.get_list("SIG Site", filters={"name": ["in", wanted]},
                                   fields=["name", "site_latitude", "site_longitude"], limit_page_length=0):
            if row.site_latitude and row.site_longitude:
                coords[(row.name or "").upper()] = (float(row.site_latitude), float(row.site_longitude))

    positions = planner.team_positions(team_setup, team_visits, coords, today)
    for position in positions:
        _set_manual_position(position, manual_positions.get(position["leader"]), coords, today)
    positions += [{"leader": t["leader"], "team": t["team"], "phone": t["phone"], "site": "", "seen_at": "",
                   "on_site": False, "age_days": None, "state": "Incident", "lat": None, "lon": None}
                  for t in all_teams if t["archetype"] == "Incident"]
    starts, names = None, None
    planned = [p for p in positions if p["state"] != "Incident"]
    if planned:
        count = overrides.get("teams") or len(planned)         # a Teams value typed on the page wins over the setup
        starts = [(p["lat"], p["lon"]) if p["state"] == "Current" else None for p in planned][:count]
        starts += [None] * (count - len(starts))
        names = {i + 1: p["team"] for i, p in enumerate(planned[:count])}
    plan = continuity.schedule_continuity(planner.plan_week(candidates, coords, start, overrides), coords, start, overrides,
                                          starts, names)
    plan["team_positions"] = positions
    plan["summary"]["visited_cycles_dismissed"] = len(visited_cycles)
    for ex in excluded:
        if ex["reason"].startswith("PM "):
            c = ex["cycle"]
            site = (c.get("site_id") or c.get("site") or "").upper()
            plan["later"].append({"site": site, "cycle": c["name"], "project": c.get("project") or "", "tier": "",
                                  "kind": "Held" if ex["reason"].startswith("PM Hold") else "Removed",
                                  "window": "", "reason": ex["reason"], "must": False, "decision": "Hold"
                                  if ex["reason"].startswith("PM Hold") else "Remove",
                                  "lat": coords[site][0] if site in coords else None,
                                  "lon": coords[site][1] if site in coords else None})
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
                                 "value": s.get("value"), "value_source": s.get("value_source", ""), "decision": s.get("decision", ""),
                                 "day": s.get("day", ""),
                                 "class": planner.CLASS_LABEL[planner.priority_class(s)], "must": bool(s.get("must"))}
                                for s in cluster["stops"] if s["site"] in coords]})
    extra = [{"site": s["site"], "cycle": s["cycle"], "project": s["project"], "tier": s["tier"],
              "kind": s.get("kind") or "Committed later", "window": s.get("window"), "reason": s["reason"],
              "lat": coords[s["site"]][0] if s["site"] in coords else None,
              "lon": coords[s["site"]][1] if s["site"] in coords else None,
              "must": bool(s.get("must")), "decision": s.get("decision", "")}
             for s in plan["later"] + plan["unplaced"]]
    return {"summary": plan["summary"], "params": plan["params"], "trips": trips, "other": extra,
            "teams": plan.get("teams", []), "team_positions": plan.get("team_positions", []),
            "tiers": planner.TIER_LABEL, "has_coordinates": bool(coords)}
