"""Offline, non-writing checks of stored cycle summaries against captured records.

This is diagnostic only. A mismatch is not a proposed replacement value: sources
may be incomplete, manually corrected, or governed by historical rules.
"""

from collections import defaultdict
from datetime import datetime, timezone


def _timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def compare_cycles(cycles, events, visits, *, events_complete=False, visits_complete=False):
    """Return candidate discrepancies without mutating the supplied snapshots.

    Complete flags are explicit caller assertions about snapshot coverage; they
    do not establish it. Unknown/malformed inputs suppress dependent comparisons.
    Visit counts distinguish completed and estimated-end visits. No stage or
    historical correction is derived from incomplete evidence.
    """
    by_event = defaultdict(list)
    by_visit = defaultdict(list)
    for event in events:
        if event.get("cycle"):
            by_event[event["cycle"]].append(event)
    for visit in visits:
        if visit.get("cycle"):
            by_visit[visit["cycle"]].append(visit)

    findings = []
    for cycle in cycles:
        name = cycle.get("name")
        if not name:
            raise ValueError("cycle snapshot must include name")
        history = by_event[name]
        if events_complete and "last_event_at" in cycle:
            times = [_timestamp(event.get("occurred_at")) for event in history]
            stored = _timestamp(cycle.get("last_event_at"))
            raw_times = [event.get("occurred_at") for event in history] + [cycle.get("last_event_at")]
            awareness = []
            for value in raw_times:
                try:
                    awareness.append(datetime.fromisoformat(str(value).replace("Z", "+00:00")).utcoffset() is not None)
                except ValueError:
                    awareness.append(None)
            if (history and all(times) and stored and None not in awareness
                    and len(set(awareness)) == 1 and stored < max(times)):
                findings.append({"cycle": name, "check": "last_event_before_latest_occurrence",
                                 "stored": str(stored), "observed": str(max(times)),
                                 "note": "TCN occurrence may be a planned date; review time semantics."})

        if visits_complete:
            records = by_visit[name]
            statuses = [visit.get("status") for visit in records]
            if all(status in ("COMPLETED", "AUTO_CLOSED") for status in statuses):
                for status, field in (("COMPLETED", "sessions_completed"),
                                      ("AUTO_CLOSED", "sessions_auto_closed")):
                    if field in cycle and cycle[field] is not None:
                        try:
                            stored = int(cycle[field])
                        except (TypeError, ValueError):
                            continue
                        observed = statuses.count(status)
                        if stored != observed:
                            findings.append({"cycle": name, "check": field,
                                             "stored": stored, "observed": observed,
                                             "note": "Review record coverage and historical corrections."})
    return findings
