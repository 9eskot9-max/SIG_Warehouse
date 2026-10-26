"""Continuity scheduler: teams carry on from where they stopped, travel counts, TCN windows are honoured.

Pure Python, no frappe imports. Entry point: schedule_continuity(plan, coords, week_start, overrides).
Every timing rule lives in _walk(); every search step only asks _walk() whether a route is feasible and what it costs.
Deterministic: the improvement search is capped by an iteration count and a fixed seed.
"""
import random
import time

from sig_warehouse.sig_warehouse import field_planner as fp

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


def _walk(route, days_n, params, start=None):
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
        if pos is not None:                              # drive from the last stop of the previous trip
            d = fp.haversine_km(pos, trip["first"]) * params["circuity"]
            tr_h = d / params["speed_kmh"]
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
                return None
            times.append(trip_span)
            stop_days_by_trip.append(stop_days)
            travel += tr_h
            work += trip["work"]
            pos = trip["last"]
            continue
        elif trip["win"]:
            lo, hi = trip["win"]
            if day < lo:                                 # arrived early: wait for the window to open
                day, h = lo, 0.0
            if day > hi:                                 # arrived after the window closed
                return None
        start = day
        t = h + trip["work"]
        day += int(t // params["day_hours"])
        h = t % params["day_hours"]
        if day > days_n or (day == days_n and h > 0):   # runs past Thursday
            return None
        end = day if h > 0 else max(start, day - 1)
        travel += tr_h
        work += trip["work"]
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


def _best_insert(routes, trip, teams, days_n, params, starts):
    """Cheapest feasible place for one trip: (added_hours, team_index, position) or None."""
    best = None
    for t in range(teams):
        base = _walk(routes[t], days_n, params, starts[t])
        base_h = (base[0] + base[1]) if base else 0.0
        for pos in range(len(routes[t]) + 1):
            cand = routes[t][:pos] + [trip] + routes[t][pos:]
            res = _walk(cand, days_n, params, starts[t])
            if res is None:
                continue
            added = (res[0] + res[1]) - base_h
            key = (round(added, 4), t, pos)
            if best is None or key < best:
                best = key
    return best


def schedule_continuity(plan, coords, week_start, overrides=None, starts=None, names=None):
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
    starts = list(starts or []) + [None] * (teams - len(starts or []))
    started = time.monotonic()

    live = [c for c in plan["clusters"] if c["kind"] != "Deferred"]
    waiting = [c for c in plan["clusters"] if c["kind"] == "Deferred"]
    trips = [_trip_model(c, i, coords, week, days_n, params) for i, c in enumerate(live)]
    by_id = {t["id"]: t for t in trips}

    routes = [[] for _ in range(teams)]
    lapsed = {}
    anchors = sorted([t for t in trips if t["win"] or any(s.get("tcn_days") for s in t["stops"])],
                     key=lambda t: (str(t["work_dates"][t["win"][1]]) if t["win"] and t.get("work_dates") else
                                    str(t["win"][1]) if t["win"] else min(
                                        str(day) for stop in t["stops"] for day in stop.get("tcn_days") or []),
                                    -t["cls"]))
    rest = sorted([t for t in trips if t not in anchors], key=lambda t: (-t["cls"], -(t["value"] / max(0.5, t["work"]))))
    for trip in anchors + rest:
        best = _best_insert(routes, trip, teams, days_n, params, starts)
        if best is None:
            lapsed[trip["id"]] = ("no eligible day remains before the TCN cutoff" if trip.get("allowed_starts") == []
                                  else "no team can reach it inside its TCN window" if trip["win"]
                                  else "no team-day left this week")
            continue
        _, t, pos = best
        routes[t].insert(pos, trip)

    rng = random.Random(SEARCH["seed"])
    current = _objective(routes, days_n, params, starts)
    evals = 0
    for _ in range(SEARCH["iters"]):
        if time.monotonic() - started > SEARCH["seconds"]:
            break
        new = [list(r) for r in routes]
        placed = [(t, trip) for t, r in enumerate(new) for trip in r]
        if not placed and not lapsed:
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
        if score is not None and (current is None or score > current):
            routes, current = new, score
            placed_ids = {x["id"] for r in routes for x in r}
            for k in list(lapsed):
                if k in placed_ids:
                    del lapsed[k]
            for trip in trips:
                if trip["id"] not in placed_ids and trip["id"] not in lapsed:
                    lapsed[trip["id"]] = "no team-day left this week"

    scheduled, team_rows = [], []
    for t, route in enumerate(routes, 1):
        res = _walk(route, days_n, params, starts[t - 1]) if route else (0.0, 0.0, 0.0, [], [])
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
        "search_evals": evals, "search_seconds": round(time.monotonic() - started, 2),
    })
    return {"clusters": scheduled + lapsed_out + waiting_out, "later": plan["later"], "unplaced": plan["unplaced"],
            "summary": summary, "params": params, "teams": team_rows}
