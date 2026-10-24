"""Weekly field planner: pure projection from ERP evidence to tiers, trips and team-day load.

No frappe imports and no writes. The caller supplies cycles, TCN events, field visits and site
coordinates; the result is a proposal for a coordinator, never a task or a stage change.
Tiers come from the cycle's next required action, not from the parsed type of the last visit.
"""
import math
from datetime import date, datetime, timedelta

DEFAULTS = {
    "circuity": 1.3,          # road km per straight-line km; provisional until calibrated
    "diameter_km": 150.0,     # largest distance between any two sites of one trip (road estimate)
    "fill_km": 60.0,          # a site may join a committed trip when this close to a member
    "cluster_size": 6,        # soft cap on sites per proposed trip
    "scope_hours": 2.0,       # on-site time per site; one flat default until measured
    "day_hours": 11.0,        # productive field hours in a team-day
    "speed_kmh": 60.0,        # travel speed inside a trip
    "teams": 4,               # teams available this week
    "work_days": 5,           # Sunday to Thursday
    "load_target": 0.85,      # share of team-days planned, leaving a buffer
    "max_trip_days": 2,       # longer trips are split
    "tcn_gap_days": 1,        # exports of one site this close together are one TCN window
    "tolerance_before": 1,    # a visit this many days before the window start still counts
    "tolerance_after": 2,     # grace after the window end before a TCN is overdue
    "park_days": 60,          # no evidence for this long: parked for review
}

TIER_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}
TIER_LABEL = {
    "T0": "Committed TCN",
    "T1": "Overdue TCN",
    "T2": "Close to handover",
    "T3": "Ready to batch",
    "T4": "Filler",
}


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def week_start_for(today):
    """The Sunday starting the planning week: the current week, or the next one from Friday."""
    today = _date(today)
    back = (today.weekday() + 1) % 7            # Monday=0 -> Sunday is 1 day back
    start = today - timedelta(days=back)
    return start + timedelta(days=7) if today.weekday() in (4, 5) else start


def tcn_windows(events, gap_days=1):
    """Latest TCN window per cycle. Exports of one site on consecutive days are one window.

    The anchor is the middle calendar day of the window (the earlier one on an even span).
    From 20 Oct 2026 an event's occurred_at is the planned start; before that it is the
    export time, so recorded_at stands in for the date.
    """
    days = {}
    for event in events:
        if event.get("event_code") not in (None, "TCN_GENERATED"):
            continue
        key = event.get("cycle")
        occurred, recorded = _date(event.get("occurred_at")), _date(event.get("recorded_at"))
        day = occurred if occurred and recorded and occurred > recorded else (recorded or occurred)
        if key and day:
            days.setdefault(key, set()).add(day)
    result = {}
    for key, values in days.items():
        ordered = sorted(values)
        runs, run = [], [ordered[0]]
        for day in ordered[1:]:
            if (day - run[-1]).days <= gap_days:
                run.append(day)
            else:
                runs.append(run)
                run = [day]
        runs.append(run)
        last = runs[-1]
        start, end = last[0], last[-1]
        result[key] = {"start": start, "end": end, "anchor": start + timedelta(days=(end - start).days // 2),
                       "exports": len(last), "windows": len(runs)}
    return result


def classify(cycle, window, visit_days, today, params, mark=""):
    """Return (tier or None, reason). None means the cycle is not field work this week."""
    today = _date(today)
    stage = str(cycle.get("stage") or "")
    if cycle.get("terminal") in (1, True, "1") or stage.startswith("5"):
        return None, "Closed"
    if mark == "Hold":
        return None, "Held by PM"
    if mark == "Visited":
        return None, "Marked visited by PM"
    if stage.startswith("1"):
        return None, "Initial: scope and mapping"
    if stage.startswith("4"):
        return None, "Invoicing: office work"
    last_event = _date(cycle.get("last_event_at"))
    visits = sorted(visit_days)
    visit_count = max(len(visits), int(cycle.get("impl_visits") or 0), 1 if cycle.get("first_visit_at") else 0)
    has_mir, has_tcn, has_tags = bool(cycle.get("mir_at")), bool(cycle.get("tcn_at")), bool(cycle.get("tags_at"))
    if window is None and cycle.get("planned_start"):
        planned = _date(cycle["planned_start"])
        window = {"start": planned, "end": planned, "anchor": planned}

    if stage.startswith("3"):
        if has_tags:
            return None, "Handover documents only"
        return "T2", "Handover needs Tags"

    quiet = last_event is not None and (today - last_event).days >= params["park_days"]
    if window:
        visited = any(day >= window["start"] - timedelta(days=params["tolerance_before"]) for day in visits)
        if not visited:
            if today <= window["end"] + timedelta(days=params["tolerance_after"]):
                return "T0", "TCN window %s to %s" % (window["start"], window["end"])
            return ("T1", "TCN window ended %s with no visit" % window["end"]) if not quiet else (None, "Parked: no evidence for %s days" % params["park_days"])
    if quiet:
        return None, "Parked: no evidence for %s days" % params["park_days"]
    if has_mir and has_tcn and visit_count >= 1 and not has_tags:
        return "T2", "Visited; Tags or a second visit needed"
    if has_mir and not visit_count:
        return "T3", "MIR ready, no current TCN" if not window else "MIR ready"
    if has_tcn and not has_mir and not visit_count:
        return "T4", "TCN without MIR (survey or access)"
    return None, "Not ready"


def _distance(coords, a, b, params):
    return haversine_km(coords[a], coords[b]) * params["circuity"]


def _diameter(coords, members, params):
    return max([0.0] + [_distance(coords, a, b, params) for i, a in enumerate(members) for b in members[i + 1:]])


def _tour(coords, members, params):
    """Nearest-neighbour order from the first member; returns (order, legs_km)."""
    left, order, legs = list(members[1:]), [members[0]], [0.0]
    while left:
        nxt = min(left, key=lambda site: _distance(coords, order[-1], site, params))
        legs.append(_distance(coords, order[-1], nxt, params))
        order.append(nxt)
        left.remove(nxt)
    return order, legs


def _workload(coords, members, params):
    order, legs = _tour(coords, members, params)
    hours = len(members) * params["scope_hours"] + sum(legs) / params["speed_kmh"]
    days = max(1, math.ceil(hours / params["day_hours"] - 1e-9))
    return order, legs, hours, days


def _sort_key(item):
    return (TIER_ORDER[item["tier"]], str(item.get("age") or ""), item["site"])


def _grow(coords, seed, pool, params, member_limit, existing=None, max_km=None):
    """Greedy diameter-capped growth. `pool` is a list of items; returns chosen items (without seed)."""
    members = list(existing or [seed["site"]])
    chosen = []
    candidates = list(pool)
    while candidates:
        best = None
        for item in candidates:
            near = min(_distance(coords, item["site"], member, params) for member in members)
            if max_km is not None and near > max_km:
                continue
            if _diameter(coords, members + [item["site"]], params) > params["diameter_km"]:
                continue
            if len(members) + 1 > member_limit:
                continue
            rank = (near, TIER_ORDER[item["tier"]], str(item.get("age") or ""))
            if best is None or rank < best[0]:
                best = (rank, item)
        if best is None:
            break
        item = best[1]
        _, _, _, days = _workload(coords, members + [item["site"]], params)
        if days > params["max_trip_days"]:
            candidates.remove(item)
            continue
        members.append(item["site"])
        chosen.append(item)
        candidates.remove(item)
    return chosen


def plan_week(candidates, coords, week_start, overrides=None):
    """candidates: dicts with site, cycle, tier, anchor (date or None), age, reason, project.

    Returns {"clusters": [...], "unplaced": [...], "summary": {...}, "params": {...}}.
    """
    params = dict(DEFAULTS)
    params.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    week_start = _date(week_start)
    week_end = week_start + timedelta(days=6)

    placeable, unplaced = [], []
    for item in sorted(candidates, key=_sort_key):
        (placeable if item["site"] in coords else unplaced).append(item)
    for item in unplaced:
        item["kind"] = "No coordinates"

    committed_now = [i for i in placeable if i["tier"] == "T0" and i.get("anchor") and week_start <= i["anchor"] <= week_end]
    later = [i for i in placeable if i["tier"] == "T0" and i not in committed_now]
    pool = [i for i in placeable if i["tier"] != "T0"]
    clusters = []

    def add_cluster(kind, items, anchor=None):
        sites = [i["site"] for i in items]
        order, legs, hours, days = _workload(coords, sites, params)
        by_site = {i["site"]: i for i in items}
        clusters.append({"id": None, "kind": kind, "anchor": anchor, "diameter_km": round(_diameter(coords, sites, params)),
                         "hours": round(hours, 1), "team_days": days,
                         "best_tier": min((i["tier"] for i in items), key=TIER_ORDER.get),
                         "stops": [dict(by_site[s], leg_km=round(l)) for s, l in zip(order, legs)]})
        return clusters[-1]

    # 1. committed TCN sites, one trip set per anchor day
    for day in sorted({i["anchor"] for i in committed_now}):
        left = [i for i in committed_now if i["anchor"] == day]
        while left:
            seed = left.pop(0)
            more = _grow(coords, seed, left, params, params["cluster_size"])
            for item in more:
                left.remove(item)
            for item in [seed] + more:
                item["kind"] = "Committed"
            add_cluster("Committed", [seed] + more, day)

    # 2. anchor fill: nearby ready sites ride along with a committed trip
    for cluster in [c for c in clusters if c["kind"] == "Committed"]:
        members = [s["site"] for s in cluster["stops"]]
        budget = cluster["team_days"] * params["day_hours"]
        fills = []
        for item in _grow(coords, cluster["stops"][0], pool, params, params["cluster_size"] + 2, existing=members, max_km=params["fill_km"]):
            if _workload(coords, members + [f["site"] for f in fills] + [item["site"]], params)[2] > budget:
                continue
            fills.append(item)
        if fills:
            for item in fills:
                item["kind"] = "Fill"
                pool.remove(item)
            clusters.remove(cluster)
            add_cluster("Committed", list(cluster["stops"]) + fills, cluster["anchor"])

    # 3. proposed trips from what is left, seeded by tier then age
    while pool:
        seed = pool.pop(0)
        more = _grow(coords, seed, pool, params, params["cluster_size"])
        for item in more:
            pool.remove(item)
        items = [seed] + more
        if len(items) == 1 and TIER_ORDER[seed["tier"]] >= TIER_ORDER["T3"]:
            seed["kind"] = "Deferred"
            add_cluster("Deferred", items)
            continue
        kind = "Lone trip" if len(items) == 1 else "Proposed"
        for item in items:
            item["kind"] = kind
        add_cluster(kind, items)

    # 4. load against team capacity; committed first, then proposed by best tier and age
    capacity = params["teams"] * params["work_days"] * params["load_target"]
    committed = [c for c in clusters if c["kind"] == "Committed"]
    movable = sorted([c for c in clusters if c["kind"] in ("Proposed", "Lone trip")],
                     key=lambda c: (TIER_ORDER[c["best_tier"]], str(c["stops"][0].get("age") or "")))
    deferred = [c for c in clusters if c["kind"] == "Deferred"]
    load = sum(c["team_days"] for c in committed)
    for cluster in movable:
        if load + cluster["team_days"] <= capacity:
            load += cluster["team_days"]
            cluster["loaded"] = True
        else:
            cluster["loaded"] = False
    for cluster in committed:
        cluster["loaded"] = True
    for cluster in deferred:
        cluster["loaded"] = False
    ordered = committed + movable + deferred
    for number, cluster in enumerate(ordered, 1):
        cluster["id"] = "C%02d" % number
        for position, stop in enumerate(cluster["stops"], 1):
            stop["order"] = position
            stop["cluster"] = cluster["id"]
            stop["loaded"] = cluster["loaded"]

    summary = {
        "week_start": str(week_start),
        "committed_sites": len(committed_now), "committed_later": len(later),
        "overdue": sum(1 for i in candidates if i["tier"] == "T1"),
        "close_to_handover": sum(1 for i in candidates if i["tier"] == "T2"),
        "ready_to_batch": sum(1 for i in candidates if i["tier"] == "T3"),
        "filler": sum(1 for i in candidates if i["tier"] == "T4"),
        "candidates": len(candidates), "no_coordinates": len(unplaced),
        "trips": len(ordered), "loaded_team_days": load, "capacity_team_days": round(capacity, 1),
        "committed_team_days": sum(c["team_days"] for c in committed),
        "backlog_trips": sum(1 for c in ordered if not c["loaded"]),
        "over_capacity": load > capacity,
    }
    return {"clusters": ordered, "later": later, "unplaced": unplaced, "summary": summary, "params": params}
