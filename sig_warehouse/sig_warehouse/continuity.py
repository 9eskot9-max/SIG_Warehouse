"""Continuity scheduler: teams carry on from where they stopped, travel counts, TCN windows are honoured.

Pure Python, no frappe imports. Entry point: schedule_continuity(plan, coords, week_start, overrides).
Every timing rule lives in _walk(); every search step only asks _walk() whether a route is feasible and what it costs.
Deterministic: the improvement search is capped by an iteration count and a fixed seed.
"""
import random
import time
from datetime import timedelta

from sig_warehouse.sig_warehouse import field_planner as fp

SEARCH = {"iters": 4000, "seconds": 3.0, "seed": 20261025}   # seconds is only a safety cap


def _trip_model(cluster, index, coords, week, days_n, params):
    stops = cluster["stops"]
    inner_km = sum((s.get("leg_km") or 0) for s in stops)
    work = len(stops) * params["scope_hours"] + inner_km / params["speed_kmh"]
    windowed = all(s.get("win_end") for s in stops)
    win = None
    if windowed:
        lo = min(fp._date(s.get("win_start") or s["win_end"]) for s in stops)
        hi = max(fp._date(s["win_end"]) for s in stops)
        hi_i = (hi - week).days
        if hi_i >= 0:                       # a window that already passed imposes no day
            win = (max(0, (lo - week).days), min(hi_i, days_n - 1))
    return {"id": cluster["id"], "cluster": cluster, "stops": stops, "index": index,
            "first": coords[stops[0]["site"]], "last": coords[stops[-1]["site"]], "work": work, "win": win,
            "value": sum(float(s.get("value") or 0) for s in stops), "cls": max(fp.priority_class(s) for s in stops),
            "must": any(s.get("must") for s in stops)}


def _walk(route, days_n, params):
    """Time a route. Returns None if it is infeasible, else (travel_h, work_h, reloc_km, [(start_day, end_day)])."""
    day, h = 0, 0.0
    pos = None
    travel = work = reloc = 0.0
    times = []
    for trip in route:
        tr_h = 0.0
        if pos is not None:                              # drive from the last stop of the previous trip
            d = fp.haversine_km(pos, trip["first"]) * params["circuity"]
            tr_h = d / params["speed_kmh"]
            reloc += d
        t = h + tr_h
        day += int(t // params["day_hours"])
        h = t % params["day_hours"]
        if trip["win"]:
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
    return travel, work, reloc, times


def _objective(routes, days_n, params):
    """Higher is better, compared in order: Must trips, TCN windows met, class-weighted sites, value, less travel."""
    must = windows = weight = 0
    value = 0.0
    travel = 0.0
    for route in routes:
        if not route:
            continue
        res = _walk(route, days_n, params)
        if res is None:
            return None
        travel += res[0]
        for trip in route:
            must += int(trip["must"])
            windows += int(bool(trip["win"]))
            weight += trip["cls"] * len(trip["stops"])
            value += trip["value"]
    return (must, windows, weight, round(value), -round(travel, 3))


def _best_insert(routes, trip, teams, days_n, params):
    """Cheapest feasible place for one trip: (added_hours, team_index, position) or None."""
    best = None
    for t in range(teams):
        base = _walk(routes[t], days_n, params)
        base_h = (base[0] + base[1]) if base else 0.0
        for pos in range(len(routes[t]) + 1):
            cand = routes[t][:pos] + [trip] + routes[t][pos:]
            res = _walk(cand, days_n, params)
            if res is None:
                continue
            added = (res[0] + res[1]) - base_h
            key = (round(added, 4), t, pos)
            if best is None or key < best:
                best = key
    return best


def schedule_continuity(plan, coords, week_start, overrides=None):
    params = dict(fp.DEFAULTS)
    params.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    week = fp._date(week_start)
    days_n = int(params["work_days"])
    teams = int(params["teams"])
    started = time.monotonic()

    live = [c for c in plan["clusters"] if c["kind"] != "Deferred"]
    waiting = [c for c in plan["clusters"] if c["kind"] == "Deferred"]
    trips = [_trip_model(c, i, coords, week, days_n, params) for i, c in enumerate(live)]
    by_id = {t["id"]: t for t in trips}

    routes = [[] for _ in range(teams)]
    lapsed = {}
    anchors = sorted([t for t in trips if t["win"]], key=lambda t: (t["win"][1], -t["cls"]))
    rest = sorted([t for t in trips if not t["win"]], key=lambda t: (-t["cls"], -(t["value"] / max(0.5, t["work"]))))
    for trip in anchors + rest:
        best = _best_insert(routes, trip, teams, days_n, params)
        if best is None:
            lapsed[trip["id"]] = ("no team can reach it inside its TCN window" if trip["win"]
                                  else "no team-day left this week")
            continue
        _, t, pos = best
        routes[t].insert(pos, trip)

    rng = random.Random(SEARCH["seed"])
    current = _objective(routes, days_n, params)
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
        score = _objective(new, days_n, params)
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
        res = _walk(route, days_n, params) if route else (0.0, 0.0, 0.0, [])
        if route:
            tr = {"team": t, "trips": len(route), "travel_h": round(res[0], 1), "work_h": round(res[1], 1),
                  "reloc_km": round(res[2]), "days": days_n}
            team_rows.append(tr)
        for trip, (start, end) in zip(route, res[3]):
            c = dict(trip["cluster"])
            span = end - start + 1
            stops = []
            for k, s in enumerate(trip["stops"]):
                stops.append(dict(s, day=str(week + timedelta(days=start + int((k * params["scope_hours"]) // params["day_hours"])))))
            c.update(stops=stops, status="Scheduled", team=t, days=[week + timedelta(days=d) for d in range(start, end + 1)],
                     loaded=True, team_days=span, hours=round(trip["work"], 1), value=round(trip["value"]),
                     priority_label=fp.CLASS_LABEL[trip["cls"]], day_start=str(week + timedelta(days=start)))
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
    windows_total = sum(1 for t in trips if t["win"])
    windows_met = sum(1 for c in scheduled if by_id[c["id"]]["win"])
    summary = dict(plan["summary"])
    summary.update({
        "trips": len(scheduled) + len(lapsed_out) + len(waiting_out), "trips_scheduled": len(scheduled),
        "trips_lapsed": len(lapsed_out), "trips_waiting": len(waiting_out),
        "sites_scheduled": sum(len(c["stops"]) for c in scheduled), "sites_lapsed": sum(len(c["stops"]) for c in lapsed_out),
        "value_scheduled": sum(c["value"] for c in scheduled), "value_lapsed": sum(c["value"] for c in lapsed_out),
        "must_lapsed": sum(1 for c in lapsed_out for s in c["stops"] if s.get("must")),
        "teams": teams, "loaded_team_days": sum(c["team_days"] for c in scheduled),
        "capacity_team_days": teams * days_n, "backlog_trips": len(lapsed_out) + len(waiting_out),
        "over_capacity": False, "travel_h": round(sum(r["travel_h"] for r in team_rows), 1),
        "work_h": round(sum(r["work_h"] for r in team_rows), 1), "reloc_km": sum(r["reloc_km"] for r in team_rows),
        "windows_total": windows_total, "windows_met": windows_met,
        "search_evals": evals, "search_seconds": round(time.monotonic() - started, 2),
    })
    return {"clusters": scheduled + lapsed_out + waiting_out, "later": plan["later"], "unplaced": plan["unplaced"],
            "summary": summary, "params": params, "teams": team_rows}
