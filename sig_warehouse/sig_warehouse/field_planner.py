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
    # Civil work is not planned here. A cycle is left out when the text of its project (label, PO, and the ERP
    # Project it resolves to: name, family) contains one of these.
    "exclude_projects": ("incident",),
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


def index_projects(projects):
    """Index ERP Project records by name and by agreement (PO) number for project_text()."""
    index = {}
    for project in projects or []:
        for key in (project.get("name"), project.get("custom_agreement_no"), project.get("project_name")):
            if key:
                index.setdefault(str(key).strip().lower(), []).append(project)
    return index


def project_text(cycle, index):
    """Lower-case text describing the ERP Project(s) a cycle belongs to: name, family and agreement number.

    A cycle reaches its Project through erp_project, its PO, or a project label that is itself a PO number.
    """
    seen, parts = set(), []
    for key in (cycle.get("erp_project"), cycle.get("po"), cycle.get("project")):
        for project in index.get(str(key or "").strip().lower(), []):
            if project.get("name") in seen:
                continue
            seen.add(project.get("name"))
            parts += [project.get("name"), project.get("project_name"), project.get("custom_project_family"),
                      project.get("custom_family"), project.get("custom_agreement_no")]
    return " ".join(str(p) for p in parts if p).lower()


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
    labels = (str(cycle.get("project") or "") + "|" + str(cycle.get("po") or "") + "|" + str(cycle.get("project_text") or "")).lower()
    if any(key and key in labels for key in params.get("exclude_projects") or ()):
        return None, "Not planned: Incident (civil work)"
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

    # One site is one stop: a second cycle (another WO) at the same site rides along on the first one.
    placeable, unplaced, first_at = [], [], {}
    for item in sorted(candidates, key=_sort_key):
        if item["site"] in first_at:
            first_at[item["site"]].setdefault("also", []).append(item["cycle"])
            continue
        first_at[item["site"]] = item
        (placeable if item["site"] in coords else unplaced).append(item)
    for item in unplaced:
        item["kind"] = "No coordinates"

    # a TCN window that just ended (still inside its grace days) is due now, so it joins the first day of the week
    committed_now = [i for i in placeable if i["tier"] == "T0" and i.get("anchor") and i["anchor"] <= week_end]
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
    for day in sorted({max(i["anchor"], week_start) for i in committed_now}):
        left = [i for i in committed_now if max(i["anchor"], week_start) == day]
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


def schedule_week(plan, week_start, teams=None, work_days=None):
    """Place the loaded trips of plan_week() on team slots (Team 1..N, Sunday to Thursday).

    Committed trips are pinned to their anchor day; the other loaded trips take the earliest slot where a
    team is free for all the trip's team-days. Returns a list of placements:
    {"trip", "team", "start", "days": [dates], "status"} where status is Scheduled, Over capacity
    (committed but no team free that day) or No free slot (loaded but the week is full).
    """
    params = plan["params"]
    teams = int(teams or params["teams"])
    work_days = int(work_days or params["work_days"])
    week_start = _date(week_start)
    days = [week_start + timedelta(days=i) for i in range(work_days)]
    busy = {(t, d): None for t in range(1, teams + 1) for d in days}
    placements = []

    def free_team(day_index, length):
        for t in range(1, teams + 1):
            if day_index + length <= len(days) and all(busy[(t, days[day_index + k])] is None for k in range(length)):
                return t
        return None

    ordered = [c for c in plan["clusters"] if c["kind"] == "Committed"] +               [c for c in plan["clusters"] if c["kind"] != "Committed" and c["loaded"]]
    for trip in ordered:
        length = trip["team_days"]
        if trip["kind"] == "Committed" and trip["anchor"] and trip["anchor"] in days:
            first, last = days.index(trip["anchor"]), days.index(trip["anchor"])
            team = free_team(first, length)
            status = "Scheduled"
            if team is None:
                # no team free on the anchor day: keep the anchor, add a team beyond the pool
                team, status = teams + 1 + sum(1 for p in placements if p["status"] == "Over capacity"), "Over capacity"
                busy.update({(team, days[first + k]): trip["id"] for k in range(min(length, len(days) - first))})
            else:
                for k in range(length):
                    busy[(team, days[first + k])] = trip["id"]
            placements.append({"trip": trip["id"], "team": team, "start": days[first],
                               "days": days[first:first + length], "status": status})
            continue
        slot = next(((i, free_team(i, length)) for i in range(len(days)) if free_team(i, length)), None)
        if slot is None:
            placements.append({"trip": trip["id"], "team": None, "start": None, "days": [], "status": "No free slot"})
            continue
        i, team = slot
        for k in range(length):
            busy[(team, days[i + k])] = trip["id"]
        placements.append({"trip": trip["id"], "team": team, "start": days[i], "days": days[i:i + length], "status": "Scheduled"})
    return placements


CLASS_LABEL = {3: "Must", 2: "Priority", 1: "Normal"}


def priority_class(item):
    """3 = Must (PM mark), 2 = close to handover, or a TCN/ready site that already has a MIR, 1 = everything else."""
    if item.get("must"):
        return 3
    if item["tier"] == "T2" or (item["tier"] in ("T0", "T1", "T3") and item.get("has_mir")):
        return 2
    return 1


def build_candidates(cycles, windows, visit_days, today, params, project_index=None, mark_field="plan_hold"):
    """Classify open Plan/Handover cycles into candidate rows, shared by the ERP page and the Excel export.

    Returns (candidates, excluded). Each candidate carries the value the choice uses: the SAR gross value of the
    cycle, or the median of known values when the cycle has none (value_source says which).
    """
    today = _date(today)
    known = sorted(float(c["gross_value"]) for c in cycles if c.get("gross_value"))
    median = known[len(known) // 2] if known else 0.0
    rows, excluded = [], []
    for raw in cycles:
        c = dict(raw)
        if project_index is not None:
            c["project_text"] = project_text(c, project_index)
        win = windows.get(c["name"])
        tier, reason = classify(c, win, visit_days.get(c["name"], ()), today, params, c.get(mark_field) or "")
        if not tier:
            excluded.append({"cycle": c, "reason": reason})
            continue
        anchor = win["anchor"] if win else (_date(c["planned_start"]) if c.get("planned_start") else None)
        value = float(c["gross_value"]) if c.get("gross_value") else None
        rows.append({
            "site": (c.get("site_id") or c.get("site") or "").upper(), "cycle": c["name"], "tier": tier,
            "reason": reason, "project": c.get("project") or "", "stage": c.get("stage") or "", "anchor": anchor,
            "window": ("%s to %s" % (win["start"], win["end"])) if win else "",
            "win_start": win["start"] if win else None, "win_end": win["end"] if win else None,
            "age": str(c.get("last_event_at") or "")[:10],
            "value": value if value is not None else median,
            "value_source": "ERP" if value is not None else "estimated (median)",
            "has_mir": bool(c.get("mir_at")), "must": (c.get(mark_field) or "") == "Must", "_c": c,
        })
    return rows, excluded


def choose_week(candidates, coords, week_start, overrides=None):
    """Option-based choice of this week's trips.

    A TCN window is an opportunity, not a commitment. Trips are ranked by priority class (Must, then Priority, then
    Normal), then by SAR value per team-day, then by the earliest window end. Each trip takes the earliest free slot
    on one of the teams that exist, on any day inside its window; no extra teams are invented. A trip that finds no
    slot is Lapsed: shown for review, not scheduled. A trip with a site that has no TCN window may go on any day.
    """
    params = dict(DEFAULTS)
    params.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    week_start = _date(week_start)
    plan = plan_week(candidates, coords, week_start, overrides)
    days = [week_start + timedelta(days=i) for i in range(int(params["work_days"]))]
    teams = int(params["teams"])
    busy = {(t, i): False for t in range(1, teams + 1) for i in range(len(days))}

    def window(cluster):
        stops = cluster["stops"]
        if any(not s.get("win_end") for s in stops):
            return 0, len(days) - 1
        lo_date = min(_date(s.get("win_start") or s["win_end"]) for s in stops)
        hi_date = max(_date(s["win_end"]) for s in stops)
        if hi_date < days[0]:                           # the window has already passed: as soon as possible
            return 0, len(days) - 1
        lo = next((i for i, d in enumerate(days) if d >= lo_date), 0)
        hi = max((i for i, d in enumerate(days) if d <= hi_date), default=len(days) - 1)
        return lo, hi

    def value(cluster):
        return sum(float(s.get("value") or 0) for s in cluster["stops"])

    def rank(cluster):
        cls = max(priority_class(s) for s in cluster["stops"])
        per = value(cluster) / max(1, cluster["team_days"])
        ends = [_date(s["win_end"]) for s in cluster["stops"] if s.get("win_end")]
        return (-cls, -per, min(ends) if ends else date.max, cluster["stops"][0]["site"])

    active = [c for c in plan["clusters"] if c["kind"] != "Deferred"]
    waiting = [c for c in plan["clusters"] if c["kind"] == "Deferred"]
    for c in sorted(active, key=rank):
        n = c["team_days"]
        lo, hi = window(c)
        slot = None
        for i in range(lo, hi + 1):
            if i + n - 1 > hi:
                break
            for t in range(1, teams + 1):
                if all(not busy[(t, i + k)] for k in range(n)):
                    slot = (t, i)
                    break
            if slot:
                break
        if slot:
            t, i = slot
            for k in range(n):
                busy[(t, i + k)] = True
            c.update(status="Scheduled", team=t, days=days[i:i + n], loaded=True)
        else:
            c.update(status="Lapsed", team=None, days=[], loaded=False)
    for c in waiting:
        c.update(status="Waiting for neighbours", team=None, days=[], loaded=False)
    for c in plan["clusters"]:
        cls = max(priority_class(s) for s in c["stops"])
        c.update(priority=cls, priority_label=CLASS_LABEL[cls], value=round(value(c)),
                 per_team_day=round(value(c) / max(1, c["team_days"])))
    scheduled = [c for c in plan["clusters"] if c["status"] == "Scheduled"]
    lapsed = [c for c in plan["clusters"] if c["status"] == "Lapsed"]
    clusters = scheduled + lapsed + waiting
    summary = dict(plan["summary"])
    summary.update({
        "trips": len(clusters), "trips_scheduled": len(scheduled), "trips_lapsed": len(lapsed), "trips_waiting": len(waiting),
        "sites_scheduled": sum(len(c["stops"]) for c in scheduled), "sites_lapsed": sum(len(c["stops"]) for c in lapsed),
        "value_scheduled": round(sum(c["value"] for c in scheduled)), "value_lapsed": round(sum(c["value"] for c in lapsed)),
        "must_lapsed": sum(1 for c in lapsed for s in c["stops"] if s.get("must")),
        "teams": teams, "loaded_team_days": sum(c["team_days"] for c in scheduled),
        "capacity_team_days": teams * len(days), "backlog_trips": len(lapsed) + len(waiting), "over_capacity": False,
    })
    return {"clusters": clusters, "later": plan["later"], "unplaced": plan["unplaced"], "summary": summary, "params": params}
