"""Continuity scheduler: teams carry on from where they stopped, travel counts, TCN windows are honoured.

Pure Python, no frappe imports. Entry point: schedule_continuity(plan, coords, week_start, overrides).
Every timing rule lives in _walk(); every search step only asks _walk() whether a route is feasible and what it costs.
Deterministic: the improvement search is capped by an iteration count and a fixed seed.
"""
import random
import time

from sig_warehouse.sig_warehouse import field_planner as fp
from sig_warehouse.sig_warehouse import town_mesh

SEARCH = {"iters": 4000, "seconds": 3.0, "seed": 20261025}   # seconds is only a safety cap


def _constrained_trip_path(trip, day, hour, days_n, params, work_dates):
    """Return the exact day of each stop and trip end, or None if a scope date is invalid."""
    start = day
    stop_days = []
    for stop in trip["stops"]:
        hour += float(stop.get("leg_km") or 0) / params["speed_kmh"]
        day += int(hour // params["day_hours"])
        hour %= params["day_hours"]
        if day >= days_n:
            return None
        date_text = str(work_dates[day])
        eligible = {str(value)[:10] for value in stop.get("eligible_days") or []}
        if eligible and date_text not in eligible:
            return None
        stop_days.append(day)
        hour += params["scope_hours"]
        day += int(hour // params["day_hours"])
        hour %= params["day_hours"]
    if day > days_n or (day == days_n and hour > 0):
        return None
    end = day if hour > 0 else max(start, day - 1)
    return day, hour, (start, min(end, days_n - 1)), stop_days


def _trip_model(cluster, index, coords, week, days_n, params):
    stops = cluster["stops"]
    inner_km = sum((s.get("leg_km") or 0) for s in stops)
    work = len(stops) * params["scope_hours"] + inner_km / params["speed_kmh"]
    window_stops = [s for s in stops if s.get("win_end")]
    win = None
    if window_stops:
        # A non-TCN filler must not erase the committed trip constraint. When
        # several TCN windows share a route, the route must fit their overlap.
        lo = max(fp._date(s.get("win_start") or s["win_end"]) for s in window_stops)
        hi = min(fp._date(s["win_end"]) for s in window_stops)
        if lo > hi:
            win = (days_n, days_n)
        if hi >= week:
            eligible = [i for i, day in enumerate(fp.planning_days(week, days_n)) if lo <= day <= hi]
            if not eligible:
                eligible = [i for i, day in enumerate(fp.planning_days(week, days_n)) if day >= max(lo, week)]
            if eligible:
                win = (eligible[0], eligible[-1])
    allowed_starts = None
    if all("eligible_days" in s for s in stops):
        work_dates = fp.planning_days(week, days_n)
        allowed_starts = [i for i in range(days_n)
                          if _constrained_trip_path(cluster, i, 0.0, days_n, params, work_dates) is not None]
        # ERP per-stop dates are the authoritative constraint. `win` is retained
        # only for the legacy Excel planner, where stops have no eligible_days.
        win = None
    return {"id": cluster["id"], "cluster": cluster, "stops": stops, "index": index,
            "first": coords[stops[0]["site"]], "last": coords[stops[-1]["site"]], "work": work, "win": win,
            "allowed_starts": allowed_starts,
            "work_dates": fp.planning_days(week, days_n) if allowed_starts is not None else None,
            "value": sum(float(s.get("value") or 0) for s in stops), "cls": max(fp.priority_class(s) for s in stops),
            "must": any(s.get("must") for s in stops)}


def _walk(route, days_n, params, start=None, diagnostics=None, travel_trace=None):
    """Time a route from the team's starting point (None = it starts at its first stop, no drive).

    Returns None if infeasible, else travel/work/relocation, trip spans and exact ERP stop-day indexes.
    """
    day, h = 0, 0.0
    pos = start
    travel = work = reloc = 0.0
    times = []
    stop_days_by_trip = []
    for trip in route:
        tr_h = 0.0
        travel_leg = None
        if pos is not None:                              # drive from the last stop of the previous trip
            mode = str(params.get("travel_mode") or "legacy").lower()
            if mode == "town_mesh":
                travel_leg = town_mesh.estimate(pos, trip["first"], params)
                d = float(travel_leg["km"])
                tr_h = float(travel_leg["hours"])
            else:
                d = fp.haversine_km(pos, trip["first"]) * params["circuity"]
                tr_h = d / params["speed_kmh"]
                travel_leg = {"km": d, "hours": tr_h, "method": "legacy_direct",
                              "origin_towns": [], "destination_towns": [], "fallback_reason": "travel_mode_legacy"}
            reloc += d
        t = h + tr_h
        day += int(t // params["day_hours"])
        h = t % params["day_hours"]
        if trip.get("allowed_starts") is not None:
            path = None
            for candidate_day in (i for i in trip["allowed_starts"] if i >= day):
                candidate_hour = h if candidate_day == day else 0.0
                path = _constrained_trip_path(trip, candidate_day, candidate_hour, days_n, params,
                                              trip["work_dates"])
                if path is not None:
                    day, h, trip_span, stop_days = path
                    break
            if path is None:
                if diagnostics is not None:
                    diagnostics.append({"trip": trip["id"], "reason": "no per-stop eligible date remains after prior route travel/work",
                                       "earliest_reached_day_index": day, "allowed_start_indexes": trip.get("allowed_starts")})
                return None
            times.append(trip_span)
            stop_days_by_trip.append(stop_days)
            travel += tr_h
            work += trip["work"]
            if travel_trace is not None and travel_leg is not None:
                travel_trace.append({"trip": trip["id"], "from": list(pos),
                                     "to": list(trip["first"]), **travel_leg})
            pos = trip["last"]
            continue
        elif trip["win"]:
            lo, hi = trip["win"]
            if day < lo:                                 # arrived early: wait for the window to open
                day, h = lo, 0.0
            if day > hi:                                 # arrived after the window closed
                if diagnostics is not None:
                    diagnostics.append({"trip": trip["id"], "reason": "arrived after the TCN window closed",
                                       "reached_day_index": day, "window_day_indexes": [lo, hi]})
                return None
        start = day
        t = h + trip["work"]
        day += int(t // params["day_hours"])
        h = t % params["day_hours"]
        if day > days_n or (day == days_n and h > 0):   # runs past Thursday
            if diagnostics is not None:
                diagnostics.append({"trip": trip["id"], "reason": "route exceeds the available workday horizon",
                                   "reached_day_index": day, "workday_count": days_n})
            return None
        end = day if h > 0 else max(start, day - 1)
        travel += tr_h
        work += trip["work"]
        if travel_trace is not None and travel_leg is not None:
            travel_trace.append({"trip": trip["id"], "from": list(pos),
                                 "to": list(trip["first"]), **travel_leg})
        pos = trip["last"]
        times.append((start, min(end, days_n - 1)))
        stop_days_by_trip.append([])
    return travel, work, reloc, times, stop_days_by_trip


def _objective(routes, days_n, params, starts):
    """Higher is better, compared in order: Must trips, TCN windows met, class-weighted sites, value, less travel."""
    must = windows = weight = 0
    value = 0.0
    travel = 0.0
    for t, route in enumerate(routes):
        if not route:
            continue
        res = _walk(route, days_n, params, starts[t])
        if res is None:
            return None
        travel += res[0]
        stop_days = res[4]
        for trip, actual_stop_days in zip(route, stop_days):
            must += int(trip["must"])
            if actual_stop_days:
                windows += sum(1 for stop, day_index in zip(trip["stops"], actual_stop_days)
                               if str(trip["work_dates"][day_index]) in
                               {str(value)[:10] for value in stop.get("tcn_days") or []})
            else:
                windows += int(bool(trip["win"]))
            weight += trip["cls"] * len(trip["stops"])
            value += trip["value"]
    return (must, windows, weight, round(value), -round(travel, 3))


def _route_trace_snapshot(routes, days_n, params, starts, work_dates):
    """Compact assignment signature for explaining accepted optimizer changes."""
    snapshot = {}
    for team_index, route in enumerate(routes):
        result = _walk(route, days_n, params, starts[team_index]) if route else (0, 0, 0, [], [])
        for order, (trip, span, stop_indexes) in enumerate(zip(route, result[3], result[4]), 1):
            if stop_indexes and trip.get("work_dates"):
                stop_dates = [str(trip["work_dates"][index]) for index in stop_indexes]
            else:
                stop_dates = []
            snapshot[trip["id"]] = {"team_index": team_index + 1, "order": order,
                                    "trip_days": [str(work_dates[index]) for index in range(span[0], span[1] + 1)],
                                    "stop_dates": stop_dates}
    return snapshot


def _best_insert(routes, trip, teams, days_n, params, starts, trace=None):
    """Cheapest feasible place for one trip: (added_hours, team_index, position) or None."""
    best = None
    alternatives = [] if trace is not None else None
    for t in range(teams):
        base = _walk(routes[t], days_n, params, starts[t])
        base_h = (base[0] + base[1]) if base else 0.0
        for pos in range(len(routes[t]) + 1):
            cand = routes[t][:pos] + [trip] + routes[t][pos:]
            failure = [] if trace is not None else None
            res = _walk(cand, days_n, params, starts[t], diagnostics=failure)
            if res is None:
                if trace is not None:
                    alternatives.append({"team_index": t + 1, "insert_before": routes[t][pos]["id"] if pos < len(routes[t]) else None,
                                         "feasible": False, "reason": failure[-1] if failure else "route constraints fail"})
                continue
            added = (res[0] + res[1]) - base_h
            key = (round(added, 4), t, pos)
            if trace is not None:
                trip_index = next(i for i, item in enumerate(cand) if item["id"] == trip["id"])
                stop_day_indexes = res[4][trip_index]
                stop_dates = ([str(trip["work_dates"][day_index]) for day_index in stop_day_indexes]
                              if stop_day_indexes and trip.get("work_dates") else [])
                alternatives.append({"team_index": t + 1, "insert_before": routes[t][pos]["id"] if pos < len(routes[t]) else None,
                                    "feasible": True, "added_hours": round(added, 4),
                                    "travel_hours": round(res[0], 3), "work_hours": round(res[1], 3),
                                    "relocation_km": round(res[2], 2),
                                    "trip_days": list(res[3][trip_index]), "stop_dates": stop_dates})
            if best is None or key < best:
                best = key
    if trace is not None:
        selected_alt = next((option for option in alternatives
                             if best and option.get("team_index") == best[1] + 1 and
                             option.get("insert_before") == (routes[best[1]][best[2]]["id"]
                                                             if best[2] < len(routes[best[1]]) else None)), None)
        trace.setdefault("initial_placement", []).append({
            "trip": trip["id"], "candidate_order": len(trace.setdefault("initial_placement", [])) + 1,
            "alternatives": alternatives,
            "chosen": ({"team_index": best[1] + 1, "insert_before": routes[best[1]][best[2]]["id"]
                        if best[2] < len(routes[best[1]]) else None, "added_hours": best[0],
                        "trip_days": selected_alt.get("trip_days") if selected_alt else [],
                        "stop_dates": selected_alt.get("stop_dates") if selected_alt else [],
                        "travel_hours": selected_alt.get("travel_hours") if selected_alt else None,
                        "work_hours": selected_alt.get("work_hours") if selected_alt else None,
                        "relocation_km": selected_alt.get("relocation_km") if selected_alt else None,
                        "tie_break_rule": "lowest added travel+work hours, then lowest team index, then earliest route position"
                        } if best else None),
            "result": "placed" if best else "no_feasible_team_order",
        })
    return best


def schedule_continuity(plan, coords, week_start, overrides=None, starts=None, names=None, trace=None,
                        search_seed=None, search_iters=None, search_seconds=None, search_accept_equal=False,
                        search_peer_objective=None, search_peer_travel_allowance_hours=0.0):
    """starts: one (lat, lon) or None per team, where that team stands when the week opens; it also sets the number of
    teams. names: team number (1-based) -> display name (the leader)."""
    params = dict(fp.DEFAULTS)
    params.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    week = fp._date(week_start)
    days_n = int(params["work_days"])
    work_dates = fp.planning_days(week, days_n)
    if starts:
        params["teams"] = len(starts)
    teams = int(params["teams"])
    search = dict(SEARCH)
    if search_seed is not None:
        search["seed"] = int(search_seed)
    if search_iters is not None:
        search["iters"] = max(0, min(int(search_iters), SEARCH["iters"]))
    if search_seconds is not None:
        search["seconds"] = max(0.0, min(float(search_seconds), SEARCH["seconds"]))
    search["accept_equal_scores"] = bool(search_accept_equal)
    peer_objective = tuple(search_peer_objective) if search_peer_objective else None
    peer_travel_allowance = max(0.0, float(search_peer_travel_allowance_hours or 0.0))
    search["accept_bounded_priority_peers"] = bool(search_accept_equal and peer_objective is not None)
    starts = list(starts or []) + [None] * (teams - len(starts or []))
    live = [c for c in plan["clusters"] if c["kind"] != "Deferred"]
    waiting = [c for c in plan["clusters"] if c["kind"] == "Deferred"]
    trips = [_trip_model(c, i, coords, week, days_n, params) for i, c in enumerate(live)]
    by_id = {t["id"]: t for t in trips}

    if trace is not None:
        trace.update({"scheduler": {"algorithm": "continuity-insert-and-improve", "search": search,
                                     "week_start": str(week), "work_dates": [str(day) for day in work_dates],
                                     "teams": teams, "team_names": {str(k): v for k, v in (names or {}).items()},
                                     "starting_positions": [list(pos) if pos else None for pos in starts],
                                     "travel_mode": str(params.get("travel_mode") or "legacy"),
                                     "travel_matrix_version": town_mesh.MATRIX_VERSION if params.get("travel_mode") == "town_mesh" and town_mesh.MATRIX_AVAILABLE else "",
                                     "search_components": ["Must trips", "TCN dates met", "priority-class × sites", "gross value", "lower travel"],
                                     "priority_order": ["Must", "TCN dates met", "priority-class × site count",
                                                        "gross value", "lower travel"],
                                     "search_logging": "All initial team/order insertion alternatives are retained. Search records strict objective improvements and counts optional bounded-priority peer perturbations; rejected randomized trials are not retained.",
                                     "peer_objective": list(peer_objective) if peer_objective else None,
                                     "peer_travel_allowance_hours": peer_travel_allowance},
                      "initial_placement": [], "improvement": {"attempted_moves": 0, "accepted_changes": [],
                                                                  "equal_score_moves": 0,
                                                                  "bounded_priority_peer_moves": 0},
                      "travel_estimates": []})

    routes = [[] for _ in range(teams)]
    lapsed = {}
    anchors = sorted([t for t in trips if t["win"] or any(s.get("tcn_days") for s in t["stops"])],
                     key=lambda t: (str(t["work_dates"][t["win"][1]]) if t["win"] and t.get("work_dates") else
                                    str(t["win"][1]) if t["win"] else min(
                                        str(day) for stop in t["stops"] for day in stop.get("tcn_days") or []),
                                    -t["cls"]))
    rest = sorted([t for t in trips if t not in anchors], key=lambda t: (-t["cls"], -(t["value"] / max(0.5, t["work"]))))
    if trace is not None:
        trace["scheduler"]["initial_trip_order"] = [trip["id"] for trip in anchors + rest]
    for trip in anchors + rest:
        best = _best_insert(routes, trip, teams, days_n, params, starts,
                            trace if trace is not None else None)
        if best is None:
            lapsed[trip["id"]] = ("no eligible day remains before the TCN cutoff" if trip.get("allowed_starts") == []
                                  else "no team can reach it inside its TCN window" if trip["win"]
                                  else "no team-day left this week")
            continue
        _, t, pos = best
        routes[t].insert(pos, trip)

    rng = random.Random(search["seed"])
    current = _objective(routes, days_n, params, starts)
    if trace is not None:
        trace["scheduler"]["initial_objective"] = list(current) if current is not None else None
    started = time.monotonic()
    trace_overhead = 0.0
    evals = 0
    termination_reason = "iteration_limit"
    for _ in range(search["iters"]):
        if time.monotonic() - started - trace_overhead > search["seconds"]:
            termination_reason = "time_limit"
            break
        new = [list(r) for r in routes]
        placed = [(t, trip) for t, r in enumerate(new) for trip in r]
        if not placed and not lapsed:
            termination_reason = "no_remaining_moves"
            break
        if placed and rng.random() < 0.3 and len(placed) > 1:          # swap two placed trips
            (ta, a), (tb, b) = rng.sample(placed, 2)
            ia, ib = new[ta].index(a), new[tb].index(b)
            new[ta][ia], new[tb][ib] = b, a
        else:                                                           # move one trip (placed or lapsed)
            pool = [trip for _, trip in placed] + [by_id[k] for k in lapsed]
            trip = rng.choice(pool)
            for r in new:
                for i, x in enumerate(r):
                    if x is trip:
                        del r[i]
                        break
            t = rng.randrange(teams)
            new[t].insert(rng.randrange(len(new[t]) + 1), trip)
        evals += 1
        score = _objective(new, days_n, params, starts)
        strict_improvement = score is not None and (current is None or score > current)
        equal_move = (search_accept_equal and score is not None and score == current and rng.random() < 0.15)
        peer_move = (search_accept_equal and peer_objective is not None and score is not None
                     and score[:4] == peer_objective[:4]
                     and score[4] >= peer_objective[4] - peer_travel_allowance
                     and score != current and rng.random() < 0.15)
        if strict_improvement or equal_move or peer_move:
            old_routes = routes
            old_score = current
            routes, current = new, score
            if trace is not None:
                if equal_move and not strict_improvement:
                    trace["improvement"]["equal_score_moves"] += 1
                elif peer_move and not strict_improvement:
                    trace["improvement"]["bounded_priority_peer_moves"] += 1
                else:
                    trace_started = time.monotonic()
                    component_labels = ["Must trips", "TCN dates met", "priority-class × sites", "gross value", "lower travel"]
                    first_changed = next((index for index, (before, after) in enumerate(zip(old_score or (), score))
                                          if before != after), None)
                    old_assignment = _route_trace_snapshot(old_routes, days_n, params, starts, work_dates)
                    new_assignment = _route_trace_snapshot(routes, days_n, params, starts, work_dates)
                    trace["improvement"]["accepted_changes"].append({
                        "evaluation": evals, "objective_before": list(old_score) if old_score is not None else None,
                        "objective_after": list(score),
                        "first_improved_component": component_labels[first_changed] if first_changed is not None else "",
                        "trip_changes": [{"trip": trip_id, "before": old_assignment.get(trip_id),
                                          "after": new_assignment.get(trip_id)}
                                         for trip_id in sorted(set(old_assignment) | set(new_assignment))
                                         if old_assignment.get(trip_id) != new_assignment.get(trip_id)],
                    })
                    trace_overhead += time.monotonic() - trace_started
            placed_ids = {x["id"] for r in routes for x in r}
            for k in list(lapsed):
                if k in placed_ids:
                    del lapsed[k]
            for trip in trips:
                if trip["id"] not in placed_ids and trip["id"] not in lapsed:
                    lapsed[trip["id"]] = "no team-day left this week"

    scheduled, team_rows = [], []
    for t, route in enumerate(routes, 1):
        final_legs = [] if trace is not None else None
        res = _walk(route, days_n, params, starts[t - 1], travel_trace=final_legs) if route else (0.0, 0.0, 0.0, [], [])
        if trace is not None:
            trace.setdefault("travel_estimates", []).extend(
                dict(leg, team_index=t) for leg in (final_legs or []))
        if route:
            tr = {"team": t, "leader": (names or {}).get(t, ""), "trips": len(route), "travel_h": round(res[0], 1), "work_h": round(res[1], 1),
                  "reloc_km": round(res[2]), "days": days_n}
            team_rows.append(tr)
        for trip, (start, end), actual_stop_days in zip(route, res[3], res[4]):
            c = dict(trip["cluster"])
            span = end - start + 1
            stops = []
            for k, s in enumerate(trip["stops"]):
                stop_day = actual_stop_days[k] if actual_stop_days else min(
                    start + int((k * params["scope_hours"]) // params["day_hours"]), days_n - 1)
                stops.append(dict(s, day=str(work_dates[stop_day])))
            c.update(stops=stops, status="Scheduled", team=t, days=[work_dates[d] for d in range(start, end + 1)],
                     loaded=True, team_days=span, hours=round(trip["work"], 1), value=round(trip["value"]),
                     priority_label=fp.CLASS_LABEL[trip["cls"]], day_start=str(work_dates[start]))
            scheduled.append(c)
    lapsed_out = []
    for trip in trips:
        if trip["id"] in lapsed:
            c = dict(trip["cluster"])
            c.update(status="Lapsed", team=None, days=[], loaded=False, team_days=0, hours=round(trip["work"], 1),
                     value=round(trip["value"]), priority_label=fp.CLASS_LABEL[trip["cls"]], lapse_reason=lapsed[trip["id"]])
            lapsed_out.append(c)
    waiting_out = []
    for c in waiting:
        c = dict(c, status="Waiting for neighbours", team=None, days=[], loaded=False, team_days=0)
        waiting_out.append(c)

    sched_ids = {c["id"] for c in scheduled}
    windows_total = sum(sum(bool(s.get("tcn_days")) for s in t["stops"])
                        if all("eligible_days" in s for s in t["stops"]) else int(bool(t["win"]))
                        for t in trips)
    windows_met = sum(sum(bool(s.get("day")) and str(s["day"])[:10] in
                           {str(day)[:10] for day in s.get("tcn_days") or []} for s in c["stops"])
                      if all("eligible_days" in s for s in c["stops"]) else int(bool(by_id[c["id"]]["win"]))
                      for c in scheduled)
    summary = dict(plan["summary"])
    summary.update({
        "trips": len(scheduled) + len(lapsed_out) + len(waiting_out), "trips_scheduled": len(scheduled),
        "trips_lapsed": len(lapsed_out), "trips_waiting": len(waiting_out),
        "sites_scheduled": sum(len(c["stops"]) for c in scheduled), "sites_lapsed": sum(len(c["stops"]) for c in lapsed_out),
        "value_scheduled": sum(c["value"] for c in scheduled), "value_lapsed": sum(c["value"] for c in lapsed_out),
        "must_lapsed": sum(1 for c in lapsed_out for s in c["stops"] if s.get("must")),
        "teams": teams, "loaded_team_days": len({(c.get("team"), day) for c in scheduled for day in c.get("days", [])}),
        "capacity_team_days": teams * days_n, "backlog_trips": len(lapsed_out) + len(waiting_out),
        "over_capacity": False, "travel_h": round(sum(r["travel_h"] for r in team_rows), 1),
        "work_h": round(sum(r["work_h"] for r in team_rows), 1), "reloc_km": sum(r["reloc_km"] for r in team_rows),
        "windows_total": windows_total, "windows_met": windows_met,
        "search_evals": evals, "search_seconds": round(time.monotonic() - started - trace_overhead, 2),
    })
    if trace is not None:
        methods = {}
        fallbacks = {}
        for leg in trace.get("travel_estimates", []):
            methods[leg.get("method", "unknown")] = methods.get(leg.get("method", "unknown"), 0) + 1
            if leg.get("fallback_reason"):
                reason = leg["fallback_reason"]
                fallbacks[reason] = fallbacks.get(reason, 0) + 1
        trace["travel_estimate_summary"] = {"mode": str(params.get("travel_mode") or "legacy"),
                                            "matrix_version": town_mesh.MATRIX_VERSION if params.get("travel_mode") == "town_mesh" and town_mesh.MATRIX_AVAILABLE else "",
                                            "final_leg_count": len(trace.get("travel_estimates", [])),
                                            "method_counts": methods, "fallback_counts": fallbacks,
                                            "within_trip_method": "unchanged straight-line circuity estimate"}
        trace["improvement"].update({"attempted_moves": evals, "accepted_count": len(trace["improvement"]["accepted_changes"]),
                                     "final_objective": list(current) if current is not None else None,
                                     "search_seconds": summary["search_seconds"],
                                     "termination_reason": termination_reason})
        trace["final_assignments"] = [
            {"trip": cluster["id"], "kind": cluster.get("kind"), "status": cluster.get("status"),
             "team_index": cluster.get("team"), "team": (names or {}).get(cluster.get("team"), ""),
             "days": [str(day) for day in cluster.get("days", [])],
             "lapse_reason": cluster.get("lapse_reason", ""),
             "stops": [{"cycle": stop.get("cycle"), "site": stop.get("site"), "scheduled_day": stop.get("day") or None,
                        "tcn_days": [str(day)[:10] for day in stop.get("tcn_days") or []],
                        "tcn_met": bool(stop.get("tcn_days") and str(stop.get("day") or "")[:10] in
                                         {str(day)[:10] for day in stop.get("tcn_days") or []}),
                        "provisional_days": [str(day)[:10] for day in stop.get("provisional_days") or []],
                        "tcn_state": ("dated_tcn_evidenced" if str(stop.get("day") or "")[:10] in
                                      {str(day)[:10] for day in stop.get("tcn_days") or []} else
                                      "provisional_tcn_required" if str(stop.get("day") or "")[:10] in
                                      {str(day)[:10] for day in stop.get("provisional_days") or []} else
                                      "not_scheduled"),
                        "tcn_cutoff": str(fp.tcn_cutoff(stop["day"])) if stop.get("day") and
                                      str(stop.get("day"))[:10] in {str(d)[:10] for d in stop.get("provisional_days") or []}
                                      else ""} for stop in cluster.get("stops", [])]}
            for cluster in scheduled + lapsed_out + waiting_out]
        provisional_pending = sum(1 for cluster in scheduled for stop in cluster.get("stops", [])
                                  if str(stop.get("day") or "")[:10] in
                                  {str(day)[:10] for day in stop.get("provisional_days") or []})
        needs_review = bool(lapsed_out or waiting_out or windows_met < windows_total or summary["must_lapsed"])
        no_scheduled_work = not scheduled and not lapsed_out and not waiting_out
        no_candidates = not int(summary.get("candidates") or 0)
        trace["outcome"] = {"scheduled_trips": len(scheduled), "lapsed_trips": len(lapsed_out),
                            "waiting_trips": len(waiting_out), "scheduled_sites": sum(len(c["stops"]) for c in scheduled),
                            "must_sites_scheduled": sum(1 for c in scheduled for s in c["stops"] if s.get("must")),
                            "must_sites_lapsed": summary["must_lapsed"], "tcn_dates_met": windows_met,
                            "provisional_sites_awaiting_tcn": provisional_pending,
                            "tcn_dates_total": windows_total, "loaded_team_days": summary["loaded_team_days"],
                            "capacity_team_days": summary["capacity_team_days"], "over_capacity": summary["over_capacity"],
                            "plan_validity": "review_required" if needs_review else
                                             "no_eligible_candidates" if no_candidates else
                                             "no_trips_in_horizon" if no_scheduled_work else
                                             "provisional_work_pending_tcn" if provisional_pending else "dated_work_tcn_supported",
                            "judgement": "Review required" if needs_review else
                                         "No eligible candidate cycles" if no_candidates else
                                         "No trips scheduled in this horizon" if no_scheduled_work else
                                         "Plan formed; TCN pending" if provisional_pending else "Targets met"}
    return {"clusters": scheduled + lapsed_out + waiting_out, "later": plan["later"], "unplaced": plan["unplaced"],
            "summary": summary, "params": params, "teams": team_rows,
            "objective": list(current) if current is not None else None}
