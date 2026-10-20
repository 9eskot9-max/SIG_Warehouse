"""Read-only site-cycle KPI reconstruction from accepted evidence.

No KPI rows are written. Stage movement remains governed by cycle_rules; this
module replays the immutable evidence stream through that same projection.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sig_warehouse.sig_warehouse.cycle_rules import derive_cycle_state

STAGES = ("1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing")
EVENT_FIELDS = {
    "MAPPING_GENERATED": "mapping_at", "MAPPING_SHEET_EXPORTED": "mapping_at",
    "BOQ_GENERATED": "boq_at", "PIMP_GENERATED": "pimp_at", "TCN_GENERATED": "tcn_at",
    "MIR_CONFIRMED": "mir_at", "TAGS_COLLECTED": "tags_at", "PHOTOS_FINALIZED": "photos_at",
    "WARRANTY_GENERATED": "warranty_at", "ASBUILT_BOQ_GENERATED": "asbuilt_at",
    "GCL_GENERATED": "ho_at", "FIS_GENERATED": "ho_at", "MGCL_GENERATED": "ho_at",
    "HOGCL_GENERATED": "ho_at", "INVOICE_GENERATED": "invoice_at",
}


def _datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone(timedelta(hours=3))).replace(tzinfo=None) if value.tzinfo else value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone(timedelta(hours=3))).replace(tzinfo=None) if parsed.tzinfo else parsed
    except (TypeError, ValueError):
        return None


def closure_disposition(event):
    """Only the exact owner-approved business outcome counts as completion."""
    reason = (event.get("artifact_ref") or "").split("|", 3)[-1]
    if event.get("source_sub") == "operations_workbench":
        if reason == "PM confirms invoice submitted":
            return "completed"
        if reason in ("PM cancellation: budget issue", "PM note: cancelled", "PM note: site cancelled"):
            return "cancelled"
        if reason == "Mock placeholder site - PM confirmed invalid site ID":
            return "invalid"
        if reason == "User triage: retain the 23 recent multi-TCN cycles; close remaining review cycles.":
            return "cleanup"
    return "unclassified"


def replay_cycles(cycles, events, as_of=None, period_days=10):
    """Return per-cycle timing facts and 10-completed-day aggregate inputs.

    Unknown stage entries and intermediate stages skipped by the shared rule
    remain unknown; they are never filled from a later event.
    """
    as_of = _datetime(as_of) or datetime.now()
    period_end = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
    period_start = period_end - timedelta(days=int(period_days))
    by_cycle = defaultdict(list)
    for event in events:
        at = _datetime(event.get("occurred_at"))
        if at and event.get("cycle"):
            by_cycle[event["cycle"]].append((at, event))

    results = {}
    for cycle in cycles:
        name = cycle.get("name")
        history = sorted(by_cycle.get(name, []), key=lambda item: (
            item[0], str(item[1].get("recorded_at") or ""), str(item[1].get("name") or "")))
        # Replay begins from the original state, not today's denormalized cycle
        # snapshot; preloading final fields would move old evidence dates forward.
        state = {"stage": STAGES[0], "sessions_completed": 0, "sessions_auto_closed": 0}
        entries, exits, seen = {}, {}, set()
        previous_rank = 1
        closed_event = None
        for at, event in history:
            event_key = event.get("event_id") or event.get("name")
            if event_key in seen:
                continue
            seen.add(event_key)
            code = event.get("event_code")
            if code in ("MAPPING_GENERATED", "MAPPING_SHEET_EXPORTED", "BOQ_GENERATED"):
                if previous_rank == 1 and 1 not in entries:
                    entries[1] = at
            if code == "FIELD_VISIT_COMPLETED":
                state["sessions_completed"] = int(state.get("sessions_completed") or 0) + 1
                state.setdefault("first_visit_at", str(at))
                state["last_visit_at"] = str(at)
                if state["sessions_completed"] == 2:
                    state["second_visit_at"] = str(at)
            elif code == "SITE_CLOSED":
                state["terminal"] = 1
                closed_event = event
            elif code in EVENT_FIELDS:
                state.setdefault(EVENT_FIELDS[code], str(at))
            stage, _anchor = derive_cycle_state(state)
            if code == "SITE_CLOSED":
                if previous_rank in entries and closure_disposition(event) == "completed":
                    # Closure is a real pipeline departure. If evidence never
                    # entered Invoicing, count the stage actually being left.
                    exits.setdefault(previous_rank, at)
                state["stage"] = stage
                continue
            rank = int(stage[0]) if stage[:1].isdigit() else previous_rank
            if rank > previous_rank:
                if previous_rank in entries and (code != "SITE_CLOSED" or closure_disposition(event) == "completed"):
                    exits.setdefault(previous_rank, at)
                entries.setdefault(rank, at)
                previous_rank = rank
            state["stage"] = stage

        stored_closed = cycle.get("terminal") in (1, True, "1", "Yes", "yes")
        closure_at = _datetime((closed_event or {}).get("occurred_at")) or _datetime(cycle.get("closed_on"))
        current_stage, _ = derive_cycle_state({**cycle, "terminal": int(stored_closed)})
        current_rank = int(current_stage[0]) if current_stage[:1].isdigit() else 1
        initial = entries.get(1)
        disposition = closure_disposition(closed_event) if closed_event else "unclassified"
        total_days = _days(initial, closure_at if stored_closed else as_of)
        stage_rows = []
        for rank, label in enumerate(STAGES, start=1):
            start_at = entries.get(rank)
            end_at = exits.get(rank)
            elapsed = _days(start_at, end_at) if end_at else None
            running = not stored_closed and rank == current_rank and bool(start_at)
            stage_rows.append({
                "stage": label,
                "entry_at": _iso(start_at),
                "exit_at": _iso(end_at),
                "days": elapsed,
                "elapsed_days": _days(start_at, as_of) if running else None,
                "running": running,
                "unknown": not bool(start_at),
            })
        business_completed = stored_closed and disposition == "completed"
        results[name] = {
            "stage_timings": stage_rows,
            "elapsed_days": total_days,
            "closed_at": _iso(closure_at),
            "closure_disposition": disposition,
            "business_completed": business_completed,
            "completion_in_period": bool(business_completed and closure_at and period_start <= closure_at < period_end),
            "stage_exits_in_period": [
                {"stage": STAGES[rank - 1], "at": _iso(at), "days": _days(entries.get(rank), at)}
                for rank, at in exits.items() if period_start <= at < period_end
            ],
        }
    return {"cycles": results, "period_start": period_start, "period_end": period_end, "as_of": as_of}


def _days(start, end):
    if not start or not end or end < start:
        return None
    return round((end - start).total_seconds() / 86400, 3)


def _iso(value):
    return value.isoformat(sep=" ") if value else None


def summarize(cycle_metrics):
    completed = [m for m in cycle_metrics.values() if m["completion_in_period"]]
    overall = [m["elapsed_days"] for m in completed if m["elapsed_days"] is not None]
    stages = {}
    for stage in STAGES:
        movements = [x for m in cycle_metrics.values() for x in m["stage_exits_in_period"] if x["stage"] == stage]
        durations = [x["days"] for x in movements if x["days"] is not None]
        stages[stage] = {
            "completed": len(movements), "average_days": _mean(durations), "n": len(durations),
            "excluded": len(movements) - len(durations),
        }
    return {
        "completed_cycles": len(completed), "average_cycle_days": _mean(overall),
        "average_cycle_n": len(overall), "average_cycle_excluded": len(completed) - len(overall),
        "stages": stages,
    }


def _mean(values):
    return round(sum(values) / len(values), 3) if values else None
