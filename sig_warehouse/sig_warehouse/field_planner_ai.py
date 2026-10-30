"""Safe, ERP-validated alternatives for the Field Planner's AI reviewer.

The model only ranks schedules prepared here. This module keeps schedule
feasibility and TCN eligibility inside the existing ERP continuity scheduler.
"""
from copy import deepcopy

from sig_warehouse.sig_warehouse import continuity, field_planner as planner, town_mesh


_ELIGIBLE = {"eligible_provisional", "eligible_dated_tcn"}
_FILL_CHECKPOINTS = (1, 3, 6)


def _candidate_decisions(data):
    trace = data.get("decision_trace") or {}
    return {row.get("cycle"): row for row in trace.get("candidate_decisions") or [] if row.get("cycle")}


def _annotate_stop(stop, decision):
    """Restore the per-day eligibility facts omitted from the normal page payload."""
    result = deepcopy(stop)
    checks = decision.get("planning_day_checks") or []
    result["eligible_days"] = [row["date"] for row in checks if row.get("status") in _ELIGIBLE]
    result["tcn_days"] = [str(row["date"])[:10] for row in checks
                           if row.get("status") == "eligible_dated_tcn"]
    result["provisional_days"] = [row["date"] for row in checks if row.get("status") == "eligible_provisional"]
    result["critical_days"] = [str(day)[:10] for day in decision.get("critical_days") or []]
    result["critical_source"] = decision.get("critical_source") or "unknown"
    result["effective_tcn_windows"] = [{"start": row["effective_start"], "end": row["effective_end"], "kind": row.get("kind") or ""}
                                       for row in decision.get("tcn_windows") or []
                                       if row.get("effective_start") and row.get("effective_end")]
    result["tcn_time_review"] = bool(decision.get("tcn_time_review"))
    result["dated_tcn"] = bool(result["tcn_days"])
    result["has_mir"] = bool(decision.get("mir_evidence_present"))
    result["has_tags"] = bool(decision.get("tags_complete"))
    result["must"] = bool(decision.get("must"))
    result["cycle"] = decision.get("cycle") or result.get("cycle")
    result["tier"] = result.get("tier") or decision.get("tier")
    result["value"] = result.get("value") or decision.get("gross_value") or 0
    result["value_source"] = result.get("value_source") or decision.get("value_source") or "unknown"
    result["leg_km"] = float(result.get("leg_km") or 0)
    return result


def _internal_trip(display_trip, stops, coords, week_start, params, index):
    cluster = {"id": display_trip["id"], "kind": display_trip.get("kind") or "Proposed",
               "anchor": display_trip.get("anchor"), "diameter_km": display_trip.get("diameter_km") or 0,
               "hours": display_trip.get("hours") or 0, "team_days": display_trip.get("team_days") or 1,
               "best_tier": display_trip.get("best_tier") or (stops[0].get("tier") if stops else "T5"),
               "stops": stops}
    trip = continuity._trip_model(cluster, index, coords, week_start, int(params["work_days"]), params)
    trip["_display"] = deepcopy(display_trip)
    return trip


def _team_context(data, team_count):
    trace_positions = ((data.get("decision_trace") or {}).get("inputs") or {}).get("team_positions") or []
    positions = data.get("team_positions") or trace_positions
    project_positions = [row for row in positions if row.get("state") != "Incident"]
    starts = []
    rendered_teams = {}
    for index in range(1, team_count + 1):
        position = project_positions[index - 1] if index <= len(project_positions) else {}
        point = None
        if position and position.get("state") == "Current":
            coordinates = position.get("starting_coordinates") or [position.get("lat"), position.get("lon")]
            if len(coordinates) == 2 and coordinates[0] is not None and coordinates[1] is not None:
                point = (float(coordinates[0]), float(coordinates[1]))
        starts.append(point)
        rendered_teams[index] = {"leader": position.get("team") or position.get("leader") or ""}
    return starts, rendered_teams


def _route_models(data):
    trace = data.get("decision_trace") or {}
    coords_source = ((trace.get("inputs") or {}).get("coordinates_used") or {})
    coords = {str(site).upper(): (float(point[0]), float(point[1]))
              for site, point in coords_source.items() if point and len(point) == 2}
    decisions = _candidate_decisions(data)
    params = data.get("params") or {}
    week_start = planner._date((data.get("summary") or {}).get("week_start"))
    team_count = int(params.get("teams") or max([int(row.get("team") or 0) for row in data.get("teams") or []] or [0]))
    starts, teams = _team_context(data, team_count)
    routes = [[] for _ in range(team_count)]
    unscheduled = []
    next_index = 0
    for display_trip in data.get("trips") or []:
        team = display_trip.get("team")
        status = display_trip.get("status")
        stops = []
        for row in display_trip.get("stops") or []:
            decision = decisions.get(row.get("cycle"))
            if decision:
                stops.append(_annotate_stop(row, decision))
        if not stops:
            continue
        if status == "Scheduled" and team is not None and 1 <= int(team) <= team_count:
            next_index += 1
            trip = _internal_trip(display_trip, stops, coords, week_start, params, next_index)
            routes[int(team) - 1].append(trip)
        elif status in ("Lapsed", "Waiting for neighbours"):
            for stop in stops:
                site = str(stop.get("site") or "").upper()
                cycle = str(stop.get("cycle") or "")
                if not cycle or site not in coords or not stop.get("eligible_days"):
                    continue
                next_index += 1
                candidate_display = {"id": "AI_FILL_" + cycle, "kind": "AI scope fill", "status": "Lapsed",
                                     "team": None, "first_day": "", "last_day": "", "anchor": "",
                                     "diameter_km": 0, "hours": params.get("scope_hours", 2), "team_days": 1,
                                     "best_tier": stop.get("tier"), "loaded": False, "stops": [row],
                                     "_source_trip_id": display_trip.get("id")}
                singleton = deepcopy(stop)
                singleton["leg_km"] = 0
                trip = _internal_trip(candidate_display, [singleton], coords, week_start, params, next_index)
                trip["_fill_cycle"] = cycle
                trip["_fill_site"] = site
                trip["_source_trip_id"] = display_trip.get("id")
                unscheduled.append(trip)
    return routes, unscheduled, coords, week_start, params, starts, teams


def _schedule_objective(routes, days_n, params, starts):
    return continuity._objective(routes, days_n, params, starts)


def _render_fill_plan(base, routes, score, week_start, params, starts, teams, added):
    """Build the same read-only plan shape as get_field_plan, with dates recomputed by ERP."""
    rendered = deepcopy(base)
    work_dates = planner.planning_days(week_start, int(params["work_days"]))
    scheduled_trips = []
    team_rows = []
    loaded_days = set()
    windows_met = 0
    moved_cycles = {row["cycle"] for row in added}
    for team_index, route in enumerate(routes, 1):
        result = continuity._walk(route, int(params["work_days"]), params, starts[team_index - 1]) if route else (0, 0, 0, [], [])
        if not route:
            continue
        travel, work, relocation, spans, stop_days = result
        team = teams.get(team_index) or {}
        team_rows.append({"team": team_index, "leader": team.get("leader") or "", "trips": len(route),
                          "travel_h": round(travel, 1), "work_h": round(work, 1),
                          "reloc_km": round(relocation), "days": int(params["work_days"])})
        for trip, span, stop_indexes in zip(route, spans, stop_days):
            display = deepcopy(trip["_display"])
            scheduled_days = [work_dates[day] for day in range(span[0], span[1] + 1)]
            display.update({"status": "Scheduled", "team": team_index,
                            "first_day": str(scheduled_days[0]), "last_day": str(scheduled_days[-1]),
                            "loaded": True, "days": [str(day) for day in scheduled_days]})
            new_stops = []
            for order, (stop, day_index) in enumerate(zip(trip["stops"], stop_indexes), 1):
                shown = deepcopy(stop)
                shown["order"] = order
                shown["day"] = str(trip["work_dates"][day_index]) if stop_indexes and trip.get("work_dates") else str(work_dates[span[0]])
                windows_met += int(bool(stop.get("tcn_days") and str(shown["day"])[:10] in
                                         {str(day)[:10] for day in stop.get("tcn_days") or []}))
                provisional = {str(day)[:10] for day in stop.get("provisional_days") or []}
                day_text = str(shown["day"])[:10]
                shown["tcn_due_for"] = day_text if day_text in provisional else ""
                shown["needs_tcn"] = bool(shown["tcn_due_for"])
                shown["tcn_due_at"] = str(planner.tcn_cutoff(day_text)) if shown["needs_tcn"] else ""
                shown["critical"] = day_text in {str(d)[:10] for d in stop.get("critical_days") or []}
                for key in ("planned_visit_start", "planned_visit_end", "planned_visit_timezone", "planned_visit_is_estimate", "tcn_time_status"):
                    shown.pop(key, None)
                shown.update(planner.critical_visit_plan(stop, day_text, params))
                shown.pop("eligible_days", None)
                shown.pop("tcn_days", None)
                shown.pop("provisional_days", None)
                shown.pop("dated_tcn", None)
                shown.pop("has_mir", None)
                new_stops.append(shown)
            display["stops"] = new_stops
            display["hours"] = round(trip["work"], 1)
            display["value"] = round(trip["value"])
            scheduled_trips.append(display)
            for day in scheduled_days:
                loaded_days.add((team_index, str(day)))

    # Retain every unscheduled scope; remove only scopes promoted by the fill pass.
    pending_trips = []
    for original in base.get("trips") or []:
        if original.get("status") not in ("Lapsed", "Waiting for neighbours"):
            continue
        remaining = [stop for stop in original.get("stops") or [] if stop.get("cycle") not in moved_cycles]
        if remaining:
            row = deepcopy(original)
            row["stops"] = remaining
            pending_trips.append(row)
    rendered["trips"] = scheduled_trips + pending_trips
    rendered["teams"] = team_rows
    summary = rendered.setdefault("summary", {})
    scheduled_stops = [stop for trip in scheduled_trips for stop in trip.get("stops") or []]
    pending_stops = [stop for trip in pending_trips for stop in trip.get("stops") or []]
    summary["trips_scheduled"] = len(scheduled_trips)
    summary["trips_lapsed"] = sum(trip.get("status") == "Lapsed" for trip in pending_trips)
    summary["trips_waiting"] = sum(trip.get("status") == "Waiting for neighbours" for trip in pending_trips)
    summary["sites_scheduled"] = len(scheduled_stops)
    summary["sites_lapsed"] = sum(len(trip.get("stops") or []) for trip in pending_trips if trip.get("status") == "Lapsed")
    summary["sites_waiting"] = sum(len(trip.get("stops") or []) for trip in pending_trips if trip.get("status") == "Waiting for neighbours")
    summary["must_lapsed"] = sum(bool(stop.get("must")) for stop in pending_stops)
    # The candidate pool does not change in this pass, so keep the baseline's exact
    # eligible-window denominator (including the scheduler's lapsed/waiting rules).
    summary["windows_total"] = int((base.get("summary") or {}).get("windows_total") or 0)
    summary["windows_met"] = windows_met
    summary["travel_h"] = round(sum(row["travel_h"] for row in team_rows), 1)
    summary["work_h"] = round(sum(row["work_h"] for row in team_rows), 1)
    summary["reloc_km"] = sum(row["reloc_km"] for row in team_rows)
    summary["loaded_team_days"] = len(loaded_days)
    summary["capacity_team_days"] = int(params["teams"]) * int(params["work_days"])
    summary["value_scheduled"] = sum(float(stop.get("value") or 0) for stop in scheduled_stops)
    summary["value_lapsed"] = sum(float(stop.get("value") or 0) for trip in pending_trips
                                   if trip.get("status") == "Lapsed" for stop in trip.get("stops") or [])
    rendered["scheduler_objective"] = list(score)
    rendered["_ai_added_scopes"] = [dict(row) for row in added]
    trace = rendered.get("decision_trace") or {}
    baseline_trace = base.get("decision_trace") or {}
    trace["baseline_final_assignments"] = deepcopy(baseline_trace.get("final_assignments") or [])
    trace["baseline_outcome"] = deepcopy(baseline_trace.get("outcome") or {})
    assignments = [{"cycle": stop.get("cycle"), "site": stop.get("site"), "day": stop.get("day"),
                    "team": trip.get("team"), "status": trip.get("status")}
                   for trip in rendered.get("trips") or [] for stop in trip.get("stops") or []]
    decisions = _candidate_decisions(base)
    final_assignments = []
    for trip in rendered.get("trips") or []:
        stop_rows = []
        for stop in trip.get("stops") or []:
            decision = decisions.get(stop.get("cycle")) or {}
            day_text = str(stop.get("day") or "")[:10]
            checks = decision.get("planning_day_checks") or []
            dated_days = {str(row.get("date") or "")[:10] for row in checks
                          if row.get("status") == "eligible_dated_tcn"}
            provisional_days = {str(row.get("date") or "")[:10] for row in checks
                                if row.get("status") == "eligible_provisional"}
            stop_rows.append({"cycle": stop.get("cycle"), "site": stop.get("site"),
                              "scheduled_day": day_text or None, "tcn_days": sorted(dated_days),
                              "tcn_met": bool(day_text in dated_days),
                              "tcn_state": "dated_tcn_evidenced" if day_text in dated_days else
                                           "provisional_tcn_required" if day_text in provisional_days else "not_scheduled"})
        leader = next((row.get("leader") for row in team_rows if row.get("team") == trip.get("team")), "")
        final_assignments.append({"trip": trip.get("id"), "kind": trip.get("kind"),
                                  "status": trip.get("status"), "team_index": trip.get("team"),
                                  "team": leader, "days": trip.get("days") or [],
                                  "lapse_reason": trip.get("lapse_reason") or "", "stops": stop_rows})
    trace["final_assignments"] = final_assignments
    trace_outcome = trace.setdefault("outcome", {})
    needs_review = bool(summary["sites_lapsed"] or summary["sites_waiting"] or summary["must_lapsed"] or
                        summary["windows_met"] < summary["windows_total"])
    trace_outcome.update({"scheduled_trips": summary["trips_scheduled"], "lapsed_trips": summary["trips_lapsed"],
                          "waiting_trips": summary["trips_waiting"], "scheduled_sites": summary["sites_scheduled"],
                          "must_sites_scheduled": sum(bool(stop.get("must")) for stop in scheduled_stops),
                          "must_sites_lapsed": summary["must_lapsed"], "tcn_dates_met": summary["windows_met"],
                          "tcn_dates_total": summary["windows_total"], "loaded_team_days": summary["loaded_team_days"],
                          "provisional_sites_awaiting_tcn": sum(bool(stop.get("needs_tcn")) for stop in scheduled_stops),
                          "capacity_team_days": summary["capacity_team_days"], "over_capacity": False,
                          "plan_validity": "review_required" if needs_review else "recommendation_only",
                          "judgement": "Recommendation only; review ai_review for selection rationale"})
    trace["ai_scope_fill"] = {"method": "ERP checked single-scope insertion into existing routes",
                               "max_added_scopes": _FILL_CHECKPOINTS[-1],
                               "added_scopes": [dict(row) for row in added],
                               "resulting_assignments": assignments,
                               "resulting_outcome": {key: summary.get(key) for key in
                                   ("sites_scheduled", "sites_lapsed", "sites_waiting", "must_lapsed",
                                    "windows_met", "windows_total", "travel_h", "reloc_km")},
                               "unchanged_baseline_scopes_retained": True,
                               "coordinate_source": "SIG Site coordinates; not sent to the model"}
    rendered["decision_trace"] = trace
    return rendered


def scope_fill_variants(data):
    """Create small fill prefixes; every insertion is checked by the ERP route simulator."""
    if not data.get("decision_trace"):
        return []
    routes, pool, coords, week_start, params, starts, teams = _route_models(data)
    if not routes or not pool or len(starts) != len(routes) or not params:
        return []
    current = _schedule_objective(routes, len(planner.planning_days(week_start, int(params["work_days"]))), params, starts)
    if current is None:
        return []
    added = []
    variants = []
    checkpoints = set(_FILL_CHECKPOINTS)
    max_additions = _FILL_CHECKPOINTS[-1]
    while pool and len(added) < max_additions:
        best = None
        for trip in pool:
            for team_index in range(len(routes)):
                for insertion in range(len(routes[team_index]) + 1):
                    proposed = [list(route) for route in routes]
                    proposed[team_index].insert(insertion, trip)
                    score = _schedule_objective(proposed, len(planner.planning_days(week_start, int(params["work_days"]))), params, starts)
                    if score is None or score[0] < current[0] or score[1] < current[1] or score[2] < current[2]:
                        continue
                    travel_delta = -(score[4] - current[4])
                    # Favor a useful scope with the smallest added route cost when
                    # objective gains are otherwise equal; the model sees the full delta.
                    key = (score[0], score[1], score[2], score[3], score[4], -round(travel_delta, 4),
                           str(trip.get("_fill_cycle") or ""), -team_index, -insertion)
                    if best is None or key > best[0]:
                        best = (key, proposed, score, trip, team_index)
        if best is None:
            break
        _key, routes, next_score, selected, team_index = best
        prior_travel_score = current[4]
        travel_delta = -(next_score[4] - prior_travel_score)
        current = next_score
        cycle = selected["_fill_cycle"]
        pool = [row for row in pool if row.get("_fill_cycle") != cycle]
        added.append({"cycle": cycle, "site": selected["_fill_site"], "team": team_index + 1,
                      "travel_delta_hours": round(travel_delta, 3)})
        if len(added) in checkpoints:
            rendered = _render_fill_plan(data, routes, current, week_start, params, starts, teams, added)
            variants.append(("SCOPE_FILL_" + str(len(added)), rendered))
    if added and len(added) not in checkpoints:
        rendered = _render_fill_plan(data, routes, current, week_start, params, starts, teams, added)
        variants.append(("SCOPE_FILL_" + str(len(added)), rendered))
    return variants


def add_movement_context(summary, data):
    """Add OSRM mesh leg provenance and anonymized starting-position facts to the model input."""
    params = data.get("params") or {}
    matrix_available = bool(town_mesh.MATRIX_AVAILABLE)
    trace_positions = ((data.get("decision_trace") or {}).get("inputs") or {}).get("team_positions") or []
    all_positions = data.get("team_positions") or trace_positions
    visible_positions = [row for row in all_positions if row.get("state") != "Incident"]
    position_by_team = {}
    for index, row in enumerate(visible_positions, 1):
        position_by_team[str(index)] = {"last_site": row.get("site"), "state": row.get("state"),
                                         "age_days": row.get("age_days"), "source": row.get("source")}
    coords_source = ((data.get("decision_trace") or {}).get("inputs") or {}).get("coordinates_used") or {}
    coords = {str(site).upper(): (float(point[0]), float(point[1])) for site, point in coords_source.items()
              if point and len(point) == 2}
    route_legs = []
    for team_route in summary.get("team_routes", []):
        team, info = team_route.get("team"), team_route
        team_id = str(team).replace("Team ", "")
        position = position_by_team.get(team_id) or {}
        point = None
        origin_site = position.get("last_site")
        if position.get("state") == "Current" and origin_site and origin_site.upper() in coords:
            point = coords[origin_site.upper()]
        for trip in info.get("trips") or []:
            stops = trip.get("sites") or []
            if not stops:
                continue
            first_site = str(stops[0].get("site") or "").upper()
            if point is not None and first_site in coords:
                leg = town_mesh.estimate(point, coords[first_site], params)
                route_legs.append({"team": team, "from_site": origin_site, "to_site": first_site,
                                   "km": round(float(leg.get("km") or 0), 1),
                                   "hours": round(float(leg.get("hours") or 0), 2),
                                   "method": leg.get("method"), "origin_towns": leg.get("origin_towns") or [],
                                   "destination_towns": leg.get("destination_towns") or [],
                                   "hub_pair": leg.get("hub_pair") or [], "fallback_reason": leg.get("fallback_reason") or ""})
            elif not origin_site:
                route_legs.append({"team": team, "from_site": "unknown starting position", "to_site": first_site,
                                   "method": "not_estimated", "fallback_reason": "no current start coordinate"})
            last_site = str(stops[-1].get("site") or "").upper()
            point = coords.get(last_site)
            origin_site = last_site
    summary["team_start_context"] = [{"team": "Team " + key, **position_by_team.get(key, {})}
                                      for key in sorted(position_by_team, key=lambda value: int(value) if value.isdigit() else 0)]
    summary["inter_trip_road_estimates"] = {"matrix_version": town_mesh.MATRIX_VERSION if matrix_available else "",
                                             "method": "OSRM town mesh with existing direct fallback",
                                             "legs": route_legs,
                                             "within_trip_method": "existing straight-line/circuity estimate"}
    return summary
