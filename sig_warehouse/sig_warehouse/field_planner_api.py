"""Whitelisted read-only API for the Field Planner page. Writes nothing; every read uses the caller's permissions."""
import json
import os
from uuid import uuid4

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


def _riyadh_now():
    """Current time in the agreed Tawal business timezone, independent of site/user timezone."""
    return frappe.utils.get_datetime_in_timezone("Asia/Riyadh")


def _trace_export_enabled():
    """Site-level kill switch for diagnostic capture/export; absent means disabled."""
    value = getattr(frappe, "conf", {}).get("sig_field_planner_trace_export_enabled", False)
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _decisions(names):
    """The PM decision log for these cycles, newest first, read with the caller's permissions."""
    if not names:
        return {}
    rows = frappe.get_list("SIG Plan Decision", filters={"cycle": ["in", names]},
                           fields=["name", "cycle", "action", "reason", "until", "decided_at"], order_by="decided_at desc",
                           limit_page_length=0)
    out = {}
    for r in rows:
        out.setdefault(r.cycle, []).append({"name": r.name, "action": r.action or "", "reason": r.reason,
                                            "until": r.until, "created": r.decided_at})
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
    business_now = _riyadh_now()
    today = business_now.date()
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
def get_field_plan(week_start=None, teams=None, scope_hours=None, diameter_km=None, project=None, capture_trace=0):
    """Return the weekly plan: TCN windows are options, trips are placed on the teams that exist, the rest lapse."""
    _require_access()
    business_now = _riyadh_now()
    today = business_now.date()
    start = frappe.utils.getdate(week_start) if week_start else frappe.utils.add_days(today, 1)
    overrides = {"teams": int(_number(teams, 0)) or None, "scope_hours": _number(scope_hours, 0) or None,
                 "diameter_km": _number(diameter_km, 0) or None}
    configured_travel_mode = str(getattr(frappe, "conf", {}).get("sig_field_planner_travel_mode", "town_mesh")).lower()
    overrides["travel_mode"] = configured_travel_mode if configured_travel_mode in ("town_mesh", "legacy") else "town_mesh"
    overrides = {key: value for key, value in overrides.items() if value}
    params = dict(planner.DEFAULTS, **overrides)
    schedule_dates = planner.planning_days(start, params["work_days"])
    trace_enabled = _trace_export_enabled()
    trace = None
    if trace_enabled and str(capture_trace).lower() in ("1", "true", "yes", "on"):
        trace = {"schema": "sig-field-planner-decision-trace/v1", "run_id": str(uuid4()),
                 "generated_at_riyadh": business_now.isoformat(), "week_start": str(start),
                 "limitations": ["This is a plan-time judgement, not proof that visits were executed.",
                                "Rejected randomized optimizer trials are counted but not individually retained.",
                                "Application revision and authenticated user identity are not stamped."],
                 "inputs": {"parameters": params,
                            "parameter_sources": {"teams": "page override" if overrides.get("teams") else "planner default until roster is loaded",
                                                  "scope_hours": "page override" if overrides.get("scope_hours") else "planner default",
                                                  "diameter_km": "page override" if overrides.get("diameter_km") else "planner default",
                                                  "travel_mode": "site config" if configured_travel_mode in ("town_mesh", "legacy") else "planner default",
                                                  "other parameters": "SIG Warehouse field_planner.DEFAULTS"},
                            "schedule_dates": [str(day) for day in schedule_dates],
                            "selected_project": project or "All projects", "erp_policy": "Stage 2 scopes plus Stage 3 scopes with Tags outstanding; dated TCNs constrain dates; other dates remain provisional through the preceding-workday 14:00 cutoff.",
                            "candidate_scope": "Open, non-terminal SIG Site Cycles in stages 2 - Plan and 3 - Handover"},
                 "candidate_decisions": [], "evidence_summary": {}}

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
                                 fields=["name", "cycle", "event_code", "occurred_at", "recorded_at"], limit_page_length=0)
        visits = frappe.get_all("SIG Field Visit", filters={"cycle": ["in", names]}, fields=["name", "cycle", "start_at", "status"],
                                limit_page_length=0)
    windows = planner.tcn_windows(events, params["tcn_gap_days"])
    visit_days = {}
    for visit in visits:
        visit_days.setdefault(visit.cycle, set()).add(frappe.utils.getdate(visit.start_at))
    # The scheduler uses visit counts from get_all. Downloadable trace detail must
    # still obey the caller's record permissions.
    trace_visits = []
    visit_detail_access = bool(trace is not None and frappe.has_permission("SIG Field Visit", "read"))
    if visit_detail_access and names:
        trace_visits = frappe.get_list("SIG Field Visit", filters={"cycle": ["in", names]},
                                      fields=["name", "cycle", "start_at", "status"], limit_page_length=0)
    trace_visit_days = {}
    for visit in trace_visits:
        trace_visit_days.setdefault(visit.cycle, set()).add(frappe.utils.getdate(visit.start_at))
    decisions = _decisions(names)
    # ERP Field Planner pools all open Stage 2 scopes, plus Stage 3 scopes with
    # Tags outstanding. A visit is evidence, not a declaration that the scope
    # no longer needs field work.
    candidates, excluded = planner.build_candidates(cycles, windows, visit_days, today, params,
                                                    planner.index_projects(_projects()), "plan_hold", decisions,
                                                    erp_policy=True, schedule_dates=schedule_dates, now=business_now.replace(tzinfo=None))

    if trace is not None:
        candidates_by_cycle = {item["cycle"]: item for item in candidates}
        excluded_by_cycle = {item["cycle"]["name"]: item["reason"] for item in excluded}
        for cycle in cycles:
            cycle_id = cycle["name"]
            candidate = candidates_by_cycle.get(cycle_id)
            window = windows.get(cycle_id) or {}
            dated_days = [day for day in schedule_dates if planner.window_covers(window, day)]
            eligible_days = {str(day)[:10] for day in (candidate or {}).get("eligible_days", [])}
            provisional_days = {str(day)[:10] for day in (candidate or {}).get("provisional_days", [])}
            day_checks = []
            for day in schedule_dates:
                key = str(day)
                if not candidate:
                    status, reason = "excluded", excluded_by_cycle.get(cycle_id, "Excluded by Stage 2/3 policy")
                elif key in eligible_days:
                    status = "eligible_provisional" if key in provisional_days else "eligible_dated_tcn"
                    reason = (("No TCN covers this date; TCN must be generated by the preceding-workday 14:00 cutoff"
                               if key in provisional_days else "A generated TCN window covers this date"))
                elif dated_days:
                    status, reason = "blocked_by_dated_tcn", "A dated TCN constrains this scope to its evidenced date(s)"
                elif business_now.replace(tzinfo=None) >= planner.tcn_cutoff(day):
                    status, reason = "cutoff_expired", "No TCN evidence existed by the preceding-workday 14:00 cutoff"
                else:
                    status, reason = "not_eligible", excluded_by_cycle.get(cycle_id, "Excluded by Stage 2/3 policy")
                day_checks.append({"date": key, "status": status, "reason": reason,
                                   "tcn_cutoff": str(planner.tcn_cutoff(day)) if status in ("eligible_provisional", "cutoff_expired") else ""})
            visits_for_cycle = sorted(str(day) for day in trace_visit_days.get(cycle_id, ()))
            tcn_dates = sorted(str(day) for day in (window.get("dates") or []))
            trace["candidate_decisions"].append({"cycle": cycle_id,
                "site": (cycle.get("site_id") or cycle.get("site") or "").upper(),
                "project": cycle.get("project") or "", "po": cycle.get("po") or "", "stage": cycle.get("stage") or "",
                "included": bool(candidate), "tier": candidate.get("tier") if candidate else "",
                "priority_reason": candidate.get("reason") if candidate else "",
                "priority_class": planner.CLASS_LABEL[planner.priority_class(candidate)] if candidate else "",
                "gross_value": candidate.get("value") if candidate else None,
                "value_source": candidate.get("value_source", "") if candidate else "",
                "must": bool(candidate.get("must")) if candidate else False,
                "exclusion_reason": excluded_by_cycle.get(cycle_id, ""),
                "pm_decision": candidate.get("decision", "") if candidate else "",
                "pm_decision_history": [{"id": entry.get("name"), "action": entry.get("action"),
                                         "reason": entry.get("reason"), "until": str(entry.get("until") or ""),
                                         "created": str(entry.get("created") or "")}
                                        for entry in (decisions or {}).get(cycle_id, [])],
                "mir_evidence_present": bool(cycle.get("mir_at")), "tags_complete": bool(cycle.get("tags_at")),
                "visit_dates": visits_for_cycle, "visit_count_used": len(visit_days.get(cycle_id, ())),
                "visit_detail_access": visit_detail_access, "tcn_dates": tcn_dates,
                "planning_day_checks": day_checks})
        trace["evidence_summary"] = {"cycles_in_scope": len(cycles), "included_candidates": len(candidates),
                                     "excluded_cycles": len(excluded), "dated_tcn_cycles": sum(bool(windows.get(c["name"])) for c in cycles),
                                     "cycles_with_mir": sum(bool(c.get("mir_at")) for c in cycles),
                                     "cycles_with_tags_complete": sum(bool(c.get("tags_at")) for c in cycles),
                                     "cycles_with_visit_evidence": sum(bool(visit_days.get(c["name"])) for c in cycles)}
        trace["evidence_records"] = {
            "tcn_events": [{"id": event.get("name"), "cycle": event.get("cycle"), "occurred_at": str(event.get("occurred_at") or ""),
                            "recorded_at": str(event.get("recorded_at") or "")} for event in events],
            "cycle_visits": [{"id": visit.get("name"), "cycle": visit.get("cycle"), "start_at": str(visit.get("start_at") or ""),
                              "status": visit.get("status") or ""} for visit in trace_visits],
        }

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
    if trace is not None:
        trace["inputs"]["team_positions"] = [{"leader": p.get("leader"), "team": p.get("team"), "site": p.get("site"),
                                               "seen_at": p.get("seen_at"), "source": p.get("source"),
                                               "state": p.get("state"), "age_days": p.get("age_days"),
                                               "starting_coordinates": [p.get("lat"), p.get("lon")]
                                               if p.get("lat") is not None and p.get("lon") is not None else None}
                                              for p in positions]
    starts, names = None, None
    planned = [p for p in positions if p["state"] != "Incident"]
    if planned:
        count = overrides.get("teams") or len(planned)         # a Teams value typed on the page wins over the setup
        starts = [(p["lat"], p["lon"]) if p["state"] == "Current" else None for p in planned][:count]
        starts += [None] * (count - len(starts))
        names = {i + 1: p["team"] for i, p in enumerate(planned[:count])}
    clustered = planner.plan_week(candidates, coords, start, overrides, schedule_singletons=True, trace=trace)
    plan = continuity.schedule_continuity(clustered, coords, start, overrides, starts, names, trace=trace)
    if trace is not None:
        trace["inputs"]["coordinates_used"] = {site: [lat, lon] for site, (lat, lon) in coords.items()}
        trace["diagnostics"] = []
        actual_team_count = len(starts) if starts is not None else int(overrides.get("teams") or params["teams"])
        if int(clustered["params"]["teams"]) != actual_team_count:
            trace["diagnostics"].append({"type": "team_capacity_basis_differs",
                "message": "Preliminary cluster loading uses its configured team count, while continuity scheduling uses the enabled roster/override count.",
                "preliminary_team_count": int(clustered["params"]["teams"]), "continuity_team_count": actual_team_count})
    plan["team_positions"] = positions
    plan["summary"].update({
        "tcn_needed": sum(1 for item in candidates if not item.get("dated_tcn")),
        "stage2_candidates": sum(1 for item in candidates if str(item.get("stage") or "").startswith("2")),
        "stage3_tags_outstanding": sum(1 for item in candidates if str(item.get("stage") or "").startswith("3")),
    })
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
    next_cutoff = min((planner.tcn_cutoff(day) for day in schedule_dates
                       if planner.tcn_cutoff(day) > business_now.replace(tzinfo=None)), default=None)
    cutoff_text = next_cutoff.replace(tzinfo=business_now.tzinfo).isoformat() if next_cutoff else ""
    result = _present(plan, coords, cutoff_text)
    result["trace_export_enabled"] = trace_enabled
    if trace is not None:
        accounted_cycles = {stop.get("cycle") for cluster in plan["clusters"] for stop in cluster.get("stops", [])}
        accounted_cycles.update(item.get("cycle") for item in plan["later"])
        accounted_cycles.update(item.get("cycle") for item in plan["unplaced"])
        accounted_cycles.discard(None)
        candidate_cycles = {item.get("cycle") for item in candidates}
        accounted_candidate_cycles = accounted_cycles & candidate_cycles
        scope_dated_tcn = sum(bool(item.get("dated_tcn")) for item in candidates)
        unplaced_dated_tcn = sum(bool(item.get("dated_tcn")) for item in plan["unplaced"])
        incomplete = bool(plan["unplaced"] or not candidate_cycles <= accounted_candidate_cycles)
        trace["outcome"].update({"candidate_cycles": len(candidates), "cycles_without_coordinates": len(plan["unplaced"]),
                                 "dated_tcn_candidates_in_scope": scope_dated_tcn,
                                 "dated_tcn_candidates_without_coordinates": unplaced_dated_tcn,
                                 "tcn_dates_total_basis": "scheduler trips only; see dated_tcn_candidates_in_scope for all candidate cycles",
                                 "accounted_candidate_cycles": len(accounted_candidate_cycles),
                                 "all_candidate_cycles_accounted_for": candidate_cycles <= accounted_candidate_cycles,
                                 "plan_validity": "review_required" if incomplete else trace["outcome"]["plan_validity"],
                                 "judgement": ("Review required" if trace["outcome"]["judgement"] == "Review required" or
                                               incomplete
                                               else trace["outcome"]["judgement"])})
        result["decision_trace"] = trace
    return result


@frappe.whitelist()
def get_reference_towns():
    """Static reference towns (zone, overnight base candidates) for the plan map. Read-only file in the app."""
    _require_access()
    with open(os.path.join(os.path.dirname(__file__), "field_planner_towns.json"), encoding="utf-8") as handle:
        return json.load(handle)


def _tcn_status(stop, cluster):
    provisional = {str(day)[:10] for day in stop.get("provisional_days", [])}
    scheduled_day = str(stop.get("day") or cluster.get("day_start") or "")[:10]
    due_for = (scheduled_day if scheduled_day in provisional else "") if scheduled_day else (min(provisional) if provisional else "")
    return {"needs_tcn": bool(due_for),
            "tcn_due_at": str(planner.tcn_cutoff(due_for)) if due_for else "",
            "tcn_due_for": due_for}


def _present(plan, coords, next_cutoff_at=""):
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
                                 "class": planner.CLASS_LABEL[planner.priority_class(s)], "must": bool(s.get("must")),
                                 **_tcn_status(s, cluster),
                                 "has_tags": bool(s.get("has_tags")), "visit_count": s.get("visit_count", 0)}
                                for s in cluster["stops"] if s["site"] in coords]})
    extra = [{"site": s["site"], "cycle": s["cycle"], "project": s["project"], "tier": s["tier"],
              "kind": s.get("kind") or "Committed later", "window": s.get("window"), "reason": s["reason"],
              "lat": coords[s["site"]][0] if s["site"] in coords else None,
              "lon": coords[s["site"]][1] if s["site"] in coords else None,
              "must": bool(s.get("must")), "decision": s.get("decision", ""),
              "needs_tcn": bool(s.get("needs_tcn")), "tcn_due_at": s.get("tcn_due_at", ""),
              "tcn_due_for": s.get("tcn_due_for", ""), "has_tags": bool(s.get("has_tags")),
              "visit_count": s.get("visit_count", 0)}
             for s in plan["later"] + plan["unplaced"]]
    return {"summary": plan["summary"], "params": plan["params"], "trips": trips, "other": extra,
            "teams": plan.get("teams", []), "team_positions": plan.get("team_positions", []),
            "tiers": planner.TIER_LABEL, "has_coordinates": bool(coords), "next_cutoff_at": next_cutoff_at}
