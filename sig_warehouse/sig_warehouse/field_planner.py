"""Weekly field planner: pure projection from ERP evidence to tiers, trips and team-day load.

No frappe imports and no writes. The caller supplies cycles, TCN events, field visits and site
coordinates; the result is a proposal for a coordinator, never a task or a stage change.
Tiers come from the cycle's next required action, not from the parsed type of the last visit.
"""
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

DEFAULTS = {
    "circuity": 1.3,          # road km per straight-line km; provisional until calibrated
    "travel_mode": "town_mesh",  # offline reference-town road-time estimate for between-trip travel
    "diameter_km": 150.0,     # largest distance between any two sites of one trip (road estimate)
    "fill_km": 60.0,          # a site may join a committed trip when this close to a member
    "cluster_size": 6,        # soft cap on sites per proposed trip
    "scope_hours": 2.0,       # on-site time per site; one flat default until measured
    "day_start_hour": 8.0,    # planning estimate in Riyadh, not actual attendance
    "day_hours": 11.0,        # productive field hours in a team-day
    "speed_kmh": 60.0,        # travel speed inside a trip
    "inner_daily_km": 900.0,  # owner limit for travel within clusters; relocation is tracked separately
    "teams": 4,               # teams available this week
    "work_days": 5,           # Sunday to Thursday
    "load_target": 0.85,      # share of team-days planned, leaving a buffer
    "max_trip_days": 2,       # longer trips are split
    "tcn_gap_days": 1,        # exports of one site this close together are one TCN window
    "tolerance_before": 1,    # a visit this many days before the window start still counts
    "tolerance_after": 2,     # grace after the window end before a TCN is overdue
    "park_days": 60,          # no evidence for this long: parked for review
    "hold_days": 30,          # a PM Hold keeps the site out of the plan this long
    "must_days": 14,          # a PM Must keeps the site first in the plan this long, or until a visit
    "visit_hold_days": 30,    # a visit without HO/GCL is held this long, then comes back (a new TCN returns it sooner)
    # DC mode excludes Incident scopes. Incident mode explicitly selects those scopes instead.
    "planning_mode": "DC",
    # Retain the legacy non-ERP classifier's prior default behavior.
    "exclude_projects": ("incident",),
}

TIER_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}
TIER_LABEL = {
    "T0": "Committed TCN",
    "T1": "Overdue TCN",
    "T2": "Close to handover",
    "T3": "Ready to batch",
    "T4": "Filler",
    "T5": "TCN needed",
}


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _after(value, reference):
    """Compare timestamps when both have time information; otherwise compare dates."""
    if not value or not reference:
        return False
    def timestamp(v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, date) or len(str(v)) <= 10:
            return None
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            return None
    left, right = timestamp(value), timestamp(reference)
    if left is not None and right is not None and (left.utcoffset() is None) == (right.utcoffset() is None):
        return left > right
    return _date(value) > _date(reference)


def team_positions(leaders, visits, coords, today, max_age_days=14):
    """Where each team (= its leader) stands: the site of the leader's latest check-in or check-out.

    leaders: [{"leader", "team", "phone"}]; visits: rows with employee, site, start_at, end_at, status.
    A position counts for the plan only while it is at most max_age_days old and the site has coordinates.
    state: Current (used as the team's starting point), Stale (too old), or Unknown (no visit or no coordinates).
    Incident teams are not passed in; the API lists them as state "Incident" without a position.
    """
    latest = {}
    for visit in visits:
        seen = visit.get("end_at") or visit.get("start_at")
        if not seen or not visit.get("employee"):
            continue
        stamp = str(seen)[:19]
        current = latest.get(visit["employee"])
        is_posted_visit = (visit.get("source") or "") == "Posted visit"
        current_is_posted_visit = bool(current and (current[1].get("source") or "") == "Posted visit")
        if current is None or stamp > current[0] or (stamp == current[0] and is_posted_visit and not current_is_posted_visit):
            latest[visit["employee"]] = (stamp, visit)
    rows = []
    for item in leaders:
        stamp, visit = latest.get(item["leader"], (None, None))
        site = (visit.get("site") or "").upper() if visit else ""
        row = {"leader": item["leader"], "team": item["team"], "phone": item.get("phone", ""), "site": site,
               "seen_at": stamp or "", "on_site": bool(visit and not visit.get("end_at")), "age_days": None,
               "state": "Unknown", "lat": None, "lon": None,
               "source": (visit.get("source") or "Posted visit") if visit else ""}
        if stamp:
            row["age_days"] = (today - _date(stamp)).days
            if site in coords:
                row["lat"], row["lon"] = coords[site]
                row["state"] = "Current" if row["age_days"] <= max_age_days else "Stale"
        rows.append(row)
    return rows


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


def planning_days(start, count):
    """Upcoming Saudi workdays (Sunday–Thursday), starting on/after `start`."""
    day = _date(start)
    result = []
    while len(result) < int(count):
        if day.weekday() not in (4, 5):  # Friday and Saturday
            result.append(day)
        day += timedelta(days=1)
    return result


def previous_workday(day):
    """Return the preceding Tawal workday (Sunday–Thursday)."""
    day = _date(day) - timedelta(days=1)
    while day.weekday() in (4, 5):
        day -= timedelta(days=1)
    return day


def tcn_cutoff(day):
    """TCN deadline for a proposed field day: 14:00 on the preceding Tawal workday."""
    return datetime.combine(previous_workday(day), datetime.min.time()).replace(hour=14)


def erp_candidate(cycle, window, mark="", schedule_dates=None, now=None, params=None):
    """Classify an ERP field-work scope and calculate the days it can still be planned.

    ERP planning intentionally differs from the legacy Excel choice flow: open Stage 2 work is
    pooled even without MIR/TCN/visits, and Stage 3 stays field-eligible until Tags are complete.
    TCN windows constrain dated work; otherwise each proposed date remains provisional until its
    preceding-workday 14:00 cutoff. ``now`` is a Riyadh-local datetime supplied by the API.
    """
    dates = [_date(d) for d in (schedule_dates or [])]
    stage = str(cycle.get("stage") or "")
    if cycle.get("terminal") in (1, True, "1") or stage.startswith("5"):
        return None, "Closed", [], []
    labels = (str(cycle.get("project") or "") + "|" + str(cycle.get("po") or "") + "|" +
              str(cycle.get("erp_project") or "") + "|" +
              str(cycle.get("project_text") or "")).lower()
    is_incident = "incident" in labels
    mode = str((params or DEFAULTS).get("planning_mode") or "DC").strip().lower()
    if mode == "incident" and not is_incident:
        return None, "Not planned: outside Incident mode", [], []
    if mode != "incident" and is_incident:
        return None, "Not planned: Incident scope; use Incident mode", [], []
    if mark in ("Hold", "Remove"):
        return None, "Held by PM" if mark == "Hold" else "Removed by PM", [], []
    if stage.startswith("1"):
        return None, "Initial: scope and mapping", [], []
    if stage.startswith("4"):
        return None, "Office work", [], []
    if stage.startswith("3") and cycle.get("tags_at"):
        return None, "Tags complete: office handover follow-up", [], []
    if not (stage.startswith("2") or stage.startswith("3")):
        return None, "Outside Stage 2/3", [], []

    tcn_days = [day for day in dates if window_covers(window, day)]
    eligible, provisional = [], []
    if tcn_days:
        # A dated TCN commits this scope to its evidenced workday. Nearby
        # provisional work cannot move it to another date.
        eligible = tcn_days
    else:
        for day in dates:
            if now is not None and now < tcn_cutoff(day):
                eligible.append(day)
                provisional.append(day)
    if not eligible:
        return None, "No eligible workday remains before the TCN cutoff", [], []

    has_dated_tcn = bool(tcn_days)
    if has_dated_tcn:
        tier = "T0"
        reason = "TCN covers proposed workday"
    elif stage.startswith("3"):
        tier = "T2"
        reason = "Handover needs Tags; TCN required for field date"
    else:
        tier = "T5"
        reason = "Stage 2 candidate; TCN needed by 2pm before field date"
    return tier, reason, eligible, provisional


def tcn_windows(events, gap_days=1):
    """Retain every TCN date and its date-runs per cycle; expose the latest run for legacy callers.

    The anchor is the middle calendar day of the window (the earlier one on an even span).
    From 20 Oct 2026 an event's occurred_at is the planned start; before that it is the
    export time, so recorded_at stands in for the date.
    """
    days = {}
    effective = {}
    for event in events:
        if event.get("event_code") not in (None, "TCN_GENERATED"):
            continue
        key = event.get("cycle")
        start_text = str(event.get("tcn_window_start") or "").strip()
        end_text = str(event.get("tcn_window_end") or "").strip()
        if key and start_text and end_text:
            try:
                start_dt = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
                if end_dt > start_dt:
                    last_day = (end_dt - timedelta(microseconds=1)).date()
                    effective.setdefault(key, []).append({"start": start_dt.date(), "end": last_day,
                        "anchor": start_dt.date(), "exports": 1, "source": "rv80_export_v1",
                        "effective_start": start_text, "effective_end": end_text,
                        "kind": event.get("tcn_window_kind") or ""})
                    continue
            except (TypeError, ValueError):
                pass
        occurred, recorded = _date(event.get("occurred_at")), _date(event.get("recorded_at"))
        day = occurred if occurred and recorded and occurred > recorded else (recorded or occurred)
        if key and day:
            days.setdefault(key, set()).add(day)
    result = {}
    for key in days.keys() | effective.keys():
        ordered = sorted(days.get(key, ()))
        precise = effective.get(key, [])
        if not ordered:
            run_rows = sorted(precise, key=lambda row: (row["start"], row["end"]))
            last = run_rows[-1]
            result[key] = {"start": last["start"], "end": last["end"], "anchor": last["anchor"],
                           "exports": len(run_rows), "windows": len(run_rows), "runs": run_rows,
                           "dates": sorted({row["start"] for row in run_rows})}
            continue
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
        run_rows = [{"start": part[0], "end": part[-1],
                     "anchor": part[0] + timedelta(days=(part[-1] - part[0]).days // 2),
                     "exports": len(part)} for part in runs]
        for row in run_rows:
            row["source"] = "legacy_date_only"
        run_rows = sorted(run_rows + precise, key=lambda row: (row["start"], row["end"]))
        latest = run_rows[-1]
        result[key] = {"start": latest["start"], "end": latest["end"], "anchor": latest["anchor"],
                       "exports": latest["exports"], "windows": len(run_rows), "runs": run_rows,
                       "dates": sorted(set(ordered) | {row["start"] for row in precise})}
    return result


def window_covers(window, day):
    """Whether a planned TCN event covers a workday; supports all evidence runs."""
    if not window:
        return False
    day = _date(day)
    return any(_date(run["start"]) <= day <= _date(run["end"])
               for run in (window.get("runs") or [window]))



def critical_visit_plan(stop, day, params):
    """Estimate the first critical visit and compare it with issued TCN evidence.

    Clock times are a proposal in Riyadh; they do not represent attendance,
    a booked shift, or permission to enter a site.
    """
    day_text = str(day or "")[:10]
    if not day_text or day_text not in {str(value)[:10] for value in stop.get("critical_days") or []}:
        return {}
    local = timezone(timedelta(hours=3))
    planned_start = datetime.combine(date.fromisoformat(day_text), datetime.min.time(), tzinfo=local) + timedelta(hours=float(params.get("day_start_hour", 8)))
    planned_end = planned_start + timedelta(hours=2)
    overlap = False
    covered = False
    for item in stop.get("effective_tcn_windows") or []:
        try:
            start = datetime.fromisoformat(str(item["start"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(item["end"]).replace("Z", "+00:00"))
            start = start.replace(tzinfo=local) if start.tzinfo is None else start.astimezone(local)
            end = end.replace(tzinfo=local) if end.tzinfo is None else end.astimezone(local)
            if start.date() <= planned_start.date() <= (end - timedelta(microseconds=1)).date():
                overlap = True
                covered = covered or (start <= planned_start and planned_end <= end)
        except (ValueError, TypeError, KeyError):
            continue
    return {"planned_visit_start": planned_start.strftime("%Y-%m-%d %H:%M"),
            "planned_visit_end": planned_end.strftime("%Y-%m-%d %H:%M"),
            "planned_visit_timezone": "Asia/Riyadh", "planned_visit_is_estimate": True,
            "tcn_time_status": "covered" if covered else "conflict" if overlap else "unverified"}

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

    # A visit without handover documents is held for 30 days; a TCN issued after that visit overrides the hold.
    last_visit = max(visits) if visits else _date(cycle.get("last_visit_at"))
    tcn_day = _date(cycle.get("tcn_at"))
    if last_visit and not cycle.get("ho_at") and (today - last_visit).days < params["visit_hold_days"]             and not (tcn_day and tcn_day > last_visit):
        return None, "Held: visited %s, waiting for HO docs (returns %s)" % (
            last_visit, last_visit + timedelta(days=params["visit_hold_days"]))

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


def _cluster_dates_feasible(items, coords, params):
    """Keep a cluster only when its route order can still honor each scope's workday."""
    if not items or not all("eligible_days" in item for item in items):
        return True
    eligible_sets = [{str(day)[:10] for day in item.get("eligible_days") or []} for item in items]
    common = set.intersection(*eligible_sets) if eligible_sets else set()
    if not common:
        return False
    common_dates = sorted(_date(day) for day in common)
    start_day = common_dates[0]
    horizon = (common_dates[-1] - start_day).days + len(items) + 3
    workdays = planning_days(start_day, horizon)
    start_indexes = {day: index for index, day in enumerate(workdays)}

    sites = [item["site"] for item in items]
    order, legs = _tour(coords, sites, params)
    by_site = defaultdict(list)
    for item in items:
        by_site[item["site"]].append(item)
    for site_items in by_site.values():
        site_items.sort(key=_sort_key)
    ordered = [by_site[site].pop(0) for site in order]
    for start in common_dates:
        start_index = start_indexes[start]
        elapsed = 0.0
        feasible = True
        for item, leg in zip(ordered, legs):
            stop_offset = int((elapsed + leg / params["speed_kmh"]) // params["day_hours"])
            position = start_index + stop_offset
            if position >= len(workdays) or str(workdays[position]) not in eligible_sets[items.index(item)]:
                feasible = False
                break
            elapsed += leg / params["speed_kmh"] + params["scope_hours"]
        if feasible:
            return True
    return False


def _grow(coords, seed, pool, params, member_limit, existing=None, max_km=None, existing_items=None,
          trace=None, phase="cluster"):
    """Greedy diameter-capped growth. `pool` is a list of items; returns chosen items (without seed)."""
    members = list(existing or [seed["site"]])
    chosen = []
    candidates = list(pool)
    while candidates:
        best = None
        checks = [] if trace is not None else None
        for item in candidates:
            current_items = list(existing_items) + chosen if existing_items is not None else [seed] + chosen
            date_ok = _cluster_dates_feasible(current_items + [item], coords, params)
            if trace is None and not date_ok:
                continue
            near = min(_distance(coords, item["site"], member, params) for member in members)
            if trace is None and max_km is not None and near > max_km:
                continue
            diameter = _diameter(coords, members + [item["site"]], params)
            if not date_ok:
                if checks is not None: checks.append({"cycle": item.get("cycle"), "site": item.get("site"), "feasible": False, "rejected_by": "combined per-stop date constraints"})
                continue
            if max_km is not None and near > max_km:
                if checks is not None: checks.append({"cycle": item.get("cycle"), "site": item.get("site"), "feasible": False, "rejected_by": "fill radius", "nearest_km": round(near, 2), "limit_km": max_km})
                continue
            if diameter > params["diameter_km"]:
                if checks is not None: checks.append({"cycle": item.get("cycle"), "site": item.get("site"), "feasible": False, "rejected_by": "cluster diameter", "diameter_km": round(diameter, 2), "limit_km": params["diameter_km"]})
                continue
            if len(members) + 1 > member_limit:
                if checks is not None: checks.append({"cycle": item.get("cycle"), "site": item.get("site"), "feasible": False, "rejected_by": "member limit", "limit": member_limit})
                continue
            rank = (near, TIER_ORDER[item["tier"]], str(item.get("age") or ""))
            if checks is not None:
                checks.append({"cycle": item.get("cycle"), "site": item.get("site"), "feasible": True,
                               "nearest_km": round(near, 2), "resulting_diameter_km": round(diameter, 2),
                               "rank": [round(near, 4), TIER_ORDER[item["tier"]], str(item.get("age") or "")]})
            if best is None or rank < best[0]:
                best = (rank, item)
        if best is None:
            if trace is not None:
                trace.append({"phase": phase, "seed_cycle": seed.get("cycle"),
                              "members_before": [item.get("cycle") for item in (existing_items or [seed]) + chosen],
                              "candidate_checks": checks, "selected_cycle": None, "stop_reason": "no eligible neighbour"})
            break
        item = best[1]
        _, _, _, days = _workload(coords, members + [item["site"]], params)
        if days > params["max_trip_days"]:
            if trace is not None:
                trace.append({"phase": phase, "seed_cycle": seed.get("cycle"),
                              "members_before": [entry.get("cycle") for entry in (existing_items or [seed]) + chosen],
                              "candidate_checks": checks, "selected_cycle": item.get("cycle"),
                              "rejected_by": "maximum trip days", "estimated_team_days": days,
                              "limit": params["max_trip_days"]})
            candidates.remove(item)
            continue
        if trace is not None:
            trace.append({"phase": phase, "seed_cycle": seed.get("cycle"),
                          "members_before": [entry.get("cycle") for entry in (existing_items or [seed]) + chosen],
                          "candidate_checks": checks, "selected_cycle": item.get("cycle"),
                          "selection_stage": "growth shortlist; committed-fill budget checked afterward" if phase == "nearby_fill" else "cluster member selected",
                          "selection_reason": "lowest nearest-distance rank among candidates passing date, radius, diameter and member checks",
                          "estimated_team_days": days})
        members.append(item["site"])
        chosen.append(item)
        candidates.remove(item)
    return chosen


def plan_week(candidates, coords, week_start, overrides=None, schedule_singletons=False, trace=None):
    """candidates: dicts with site, cycle, tier, anchor (date or None), age, reason, project.

    Returns {"clusters": [...], "unplaced": [...], "summary": {...}, "params": {...}}.
    """
    params = dict(DEFAULTS)
    params.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    week_start = _date(week_start)
    week_end = week_start + timedelta(days=6)
    if trace is not None:
        trace.update({"clustering": {"policy": "TCN-anchored trips, nearby candidate fills, then proposed trips",
                                     "candidate_count": len(candidates), "candidates_without_coordinates": [],
                                     "growth_evaluations": [], "trips": [], "capacity_decisions": []}})

    # Keep one work item per cycle. Several scopes can share a physical site, but
    # their readiness and TCN dates must not be discarded by site-level de-duplication.
    placeable, unplaced = [], []
    for item in sorted(candidates, key=_sort_key):
        (placeable if item["site"] in coords else unplaced).append(item)
    for item in unplaced:
        item["kind"] = "No coordinates"
        if trace is not None:
            trace["clustering"]["candidates_without_coordinates"].append(
                {"cycle": item.get("cycle"), "site": item.get("site"), "reason": "no coordinates in ERP Site"})

    # a TCN window that just ended (still inside its grace days) is due now, so it joins the first day of the week
    committed_now = [i for i in placeable if i["tier"] == "T0" and i.get("anchor") and i["anchor"] <= week_end]
    later = [i for i in placeable if i["tier"] == "T0" and i not in committed_now]
    pool = [i for i in placeable if i["tier"] != "T0"]
    clusters = []

    def add_cluster(kind, items, anchor=None):
        sites = [i["site"] for i in items]
        order, legs, hours, days = _workload(coords, sites, params)
        by_site = defaultdict(list)
        for item in items:
            by_site[item["site"]].append(item)
        for site_items in by_site.values():
            site_items.sort(key=_sort_key)
        ordered_items = [by_site[site].pop(0) for site in order]
        clusters.append({"id": None, "kind": kind, "anchor": anchor, "diameter_km": round(_diameter(coords, sites, params)),
                         "hours": round(hours, 1), "team_days": days,
                         "best_tier": min((i["tier"] for i in items), key=TIER_ORDER.get),
                         "stops": [dict(item, leg_km=round(leg)) for item, leg in zip(ordered_items, legs)]})
        if trace is not None:
            trace["clustering"]["trips"].append({"event": "trip_formed", "sequence": len(trace["clustering"]["trips"]) + 1,
                "kind": kind, "anchor": str(anchor) if anchor else None,
                "members": [{"cycle": item.get("cycle"), "site": item.get("site"), "tier": item.get("tier"),
                             "reason": item.get("reason"), "dated_tcn": bool(item.get("dated_tcn")),
                             "priority_class": CLASS_LABEL[priority_class(item)], "must": bool(item.get("must")),
                             "gross_value": item.get("value"), "value_source": item.get("value_source", ""),
                             "tour_leg_km": round(leg, 2)}
                            for item, leg in zip(ordered_items, legs)],
                "diameter_km": round(_diameter(coords, sites, params), 2), "estimated_team_days": days,
                "estimated_work_hours": round(hours, 2)})
        return clusters[-1]

    # 1. committed TCN sites, one trip set per anchor day
    for day in sorted({max(i["anchor"], week_start) for i in committed_now}):
        left = [i for i in committed_now if max(i["anchor"], week_start) == day]
        while left:
            seed = left.pop(0)
            more = _grow(coords, seed, left, params, params["cluster_size"],
                         trace=trace["clustering"]["growth_evaluations"] if trace is not None else None,
                         phase="dated_tcn_cluster")
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
        for item in _grow(coords, cluster["stops"][0], pool, params, params["cluster_size"] + 2,
                          existing=members, max_km=params["fill_km"], existing_items=cluster["stops"],
                          trace=trace["clustering"]["growth_evaluations"] if trace is not None else None,
                          phase="nearby_fill"):
            fill_hours = _workload(coords, members + [f["site"] for f in fills] + [item["site"]], params)[2]
            if fill_hours > budget:
                if trace is not None:
                    trace["clustering"]["growth_evaluations"].append({
                        "phase": "nearby_fill", "seed_cycle": cluster["stops"][0].get("cycle"),
                        "candidate_cycle": item.get("cycle"), "accepted": False,
                        "rejected_by": "committed trip work-hour budget",
                        "resulting_hours": round(fill_hours, 2), "budget_hours": round(budget, 2)})
                continue
            if trace is not None:
                trace["clustering"]["growth_evaluations"].append({
                    "phase": "nearby_fill", "seed_cycle": cluster["stops"][0].get("cycle"),
                    "candidate_cycle": item.get("cycle"), "accepted": True,
                    "resulting_hours": round(fill_hours, 2), "budget_hours": round(budget, 2)})
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
        more = _grow(coords, seed, pool, params, params["cluster_size"],
                     trace=trace["clustering"]["growth_evaluations"] if trace is not None else None,
                     phase="proposed_trip")
        for item in more:
            pool.remove(item)
        items = [seed] + more
        if len(items) == 1 and TIER_ORDER[seed["tier"]] >= TIER_ORDER["T3"] and not schedule_singletons:
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
    if trace is not None:
        trace["clustering"]["preliminary_capacity"] = {"teams_parameter": params["teams"],
            "work_days": params["work_days"], "load_target": params["load_target"],
            "capacity_team_days": round(capacity, 2),
            "committed_team_days": sum(c["team_days"] for c in committed),
            "total_preliminary_loaded_team_days": round(load, 2)}
        trace["clustering"]["capacity_decisions"] = [
            {"trip": cluster["id"], "kind": cluster["kind"], "loaded": bool(cluster.get("loaded")),
             "team_days": cluster["team_days"],
             "reason": "TCN-anchored trip retained" if cluster["kind"] == "Committed" else
                       "singleton deferred by the lower-priority deferral rule" if cluster["kind"] == "Deferred" else
                       "within preliminary load target" if cluster.get("loaded") else
                       "preliminary load target exceeded"}
            for cluster in ordered]
        for event in trace["clustering"]["trips"]:
            member_cycles = {member.get("cycle") for member in event["members"]}
            match = next((cluster for cluster in ordered
                          if member_cycles <= {stop.get("cycle") for stop in cluster["stops"]}), None)
            event["final_trip"] = match["id"] if match else None
            event["superseded_by_fill"] = bool(match and len(member_cycles) < len(match["stops"]))

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
    if item.get("dated_tcn"):
        return 2
    if item["tier"] == "T2" or (item["tier"] in ("T0", "T1", "T3") and item.get("has_mir")):
        return 2
    return 1


def active_decision(entries, cycle, last_visit, today, params):
    """The PM decision that applies today, or None. entries are the cycle's log lines, newest first.

    A Clear or legacy blank line clears. Hold and Remove are cancelled by a TCN issued after the decision (PMs request TCNs on
    purpose). Must ends after must_days, on a reported visit after the decision, or when HO documents exist.
    """
    today = _date(today)
    if not entries:
        return None
    latest = entries[0]
    action = latest.get("action") or ""
    if action in ("", "Blank", "Clear"):
        return None
    created = _date(latest.get("created"))
    tcn = _date(cycle.get("tcn_at"))
    if action == "Must":
        visits = last_visit if isinstance(last_visit, (list, tuple, set)) else [last_visit]
        if (today - created).days >= params["must_days"] or cycle.get("ho_at") or any(_after(v, latest.get("created")) for v in visits):
            return None
        return {"action": "Must", "reason": latest.get("reason") or "", "until": ""}
    if tcn and _after(cycle.get("tcn_at"), latest.get("created")):
        return None
    until = _date(latest.get("until")) or created + timedelta(days=params["hold_days"])
    if action == "Hold":
        if today >= until:
            return None
        return {"action": "Hold", "reason": latest.get("reason") or "", "until": str(until)}
    return {"action": "Remove", "reason": latest.get("reason") or "", "until": ""}


def build_candidates(cycles, windows, visit_days, today, params, project_index=None, mark_field="plan_hold", decisions=None,
                     erp_policy=False, schedule_dates=None, now=None, visit_times=None):
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
        last_visit = list((visit_times or {}).get(c["name"], ()))
        last_visit.extend(visit_days.get(c["name"], ()))
        last_visit.append(c.get("last_visit_at"))
        dec = active_decision((decisions or {}).get(c["name"], []), c, last_visit, today, params)
        if dec and dec["action"] in ("Hold", "Remove"):
            why = "PM Hold until %s" % dec["until"] if dec["action"] == "Hold" else "PM Remove"
            excluded.append({"cycle": c, "reason": why + (" - " + dec["reason"] if dec["reason"] else "")})
            continue
        # the PM log is authoritative when it has entries; the cycle's Planner Mark is only a mirror
        has_log = c["name"] in (decisions or {})
        mark = "" if has_log else (c.get(mark_field) or "")
        eligible_days, provisional_days = [], []
        if erp_policy:
            tier, reason, eligible_days, provisional_days = erp_candidate(c, win, mark, schedule_dates, now, params)
            # A dated PM Must raises priority; it never changes the TCN cutoff.
            if dec and dec["action"] == "Must" and tier:
                reason = "PM Must · " + reason
        else:
            tier, reason = classify(c, win, visit_days.get(c["name"], ()), today, params, mark)
        if not tier:
            excluded.append({"cycle": c, "reason": reason})
            continue
        dated_days = [day for day in (schedule_dates or []) if erp_policy and window_covers(win, day)]
        anchor = (min(dated_days) if erp_policy and dated_days else
                  win["anchor"] if win else (_date(c["planned_start"]) if c.get("planned_start") else None))
        window_label = ", ".join(str(day) for day in dated_days) if erp_policy and dated_days else (
            ("%s to %s" % (win["start"], win["end"])) if win else "")
        effective_runs = [run for run in (win or {}).get("runs", []) if run.get("effective_start") and run.get("effective_end")]
        if erp_policy and dated_days and effective_runs:
            window_label = "; ".join("%s to %s" % (run["effective_start"], run["effective_end"]) for run in effective_runs)
        value = float(c["gross_value"]) if c.get("gross_value") else None
        rows.append({
            "site": (c.get("site_id") or c.get("site") or "").upper(), "cycle": c["name"], "tier": tier,
            "reason": reason, "project": c.get("project") or "", "stage": c.get("stage") or "", "anchor": anchor,
            "window": window_label,
            "win_start": win["start"] if win else None, "win_end": win["end"] if win else None,
            "age": str(c.get("last_event_at") or "")[:10],
            "value": value if value is not None else median,
            "value_source": "ERP" if value is not None else "estimated (median)",
            "has_mir": bool(c.get("mir_at")),
            "must": bool(dec and dec["action"] == "Must") if has_log else (c.get(mark_field) or "") == "Must",
            "decision": dec["action"] if dec else "", "_c": c,
        })
        if erp_policy:
            item = rows[-1]
            item["effective_tcn_windows"] = [{"start": run["effective_start"], "end": run["effective_end"], "kind": run.get("kind") or ""} for run in effective_runs]
            item["eligible_days"] = eligible_days
            critical_kind = "Critical Incident" if str(params.get("planning_mode") or "DC").lower() == "incident" else "Critical Project"
            critical_windows = [run for run in (win or {}).get("runs", []) if run.get("kind") == critical_kind]
            site_is_critical = c.get("planner_critical_status") == "Critical"
            item["critical_days"] = [day for day in eligible_days if site_is_critical or any(
                _date(run["start"]) <= day <= _date(run["end"]) for run in critical_windows)]
            item["critical_source"] = "site list" if site_is_critical else ("verified TCN" if critical_windows else "unknown")
            # The scheduler assigns dates, not clock times. Non-default normal
            # windows require a PM to check the actual hours before dispatch.
            item["tcn_time_review"] = any(run.get("kind") == "Normal" and
                any(_date(run["start"]) <= day <= _date(run["end"]) for day in dated_days) and
                (datetime.fromisoformat(run["effective_end"].replace("Z", "+00:00")) -
                 datetime.fromisoformat(run["effective_start"].replace("Z", "+00:00"))) != timedelta(hours=71)
                for run in effective_runs)
            item["provisional_days"] = provisional_days
            item["needs_tcn"] = bool(provisional_days)
            item["tcn_days"] = dated_days
            item["dated_tcn"] = bool(dated_days)
            provisional_day = provisional_days[0] if provisional_days else None
            item["tcn_due_at"] = str(tcn_cutoff(provisional_day)) if provisional_day else ""
            item["tcn_due_for"] = str(provisional_day) if provisional_day else ""
            item["has_tags"] = bool(c.get("tags_at"))
            item["visit_count"] = max(len(visit_days.get(c["name"], ())), int(c.get("impl_visits") or 0))
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
