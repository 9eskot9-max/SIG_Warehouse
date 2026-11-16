"""Preflight and apply the reviewed legacy site-cycle parking conversion."""

from __future__ import annotations


MIGRATION_REASON = "Legacy in-progress work; original closure retained in history."


def _is_terminal(value):
    return value in (1, True, "1", "Yes", "yes")


def _key(row):
    return str(row.get("site_key") or ""), str(row.get("po") or "")


def validate(manifest, cycles, events, *, expected_count=136):
    """Return all preflight errors; no writes occur until this returns empty."""
    errors = []
    if len(manifest) != expected_count:
        errors.append({"code": "UNEXPECTED_MANIFEST_COUNT", "expected": expected_count, "actual": len(manifest)})
    cycle_names = [row.get("name") for row in cycles]
    if not all(cycle_names) or len(cycle_names) != len(set(cycle_names)):
        raise ValueError("cycle snapshot must contain unique names")
    event_names = [row.get("name") for row in events]
    if not all(event_names) or len(event_names) != len(set(event_names)):
        raise ValueError("event snapshot must contain unique names")
    by_cycle = {row["name"]: row for row in cycles}
    by_event = {row["name"]: row for row in events}
    selected = set()
    for item in manifest:
        name = item.get("name")
        if not name or name in selected:
            errors.append({"code": "MISSING_OR_DUPLICATE_MANIFEST_NAME", "name": name})
            continue
        selected.add(name)
        cycle = by_cycle.get(name)
        if cycle is None:
            errors.append({"code": "CYCLE_MISSING", "name": name})
            continue
        for field in ("modified", "site_key", "po", "wo", "sig_lifecycle", "sig_parked_at"):
            if str(cycle.get(field) or "") != str(item.get(field) or ""):
                errors.append({"code": "CYCLE_CHANGED", "name": name, "field": field})
        if not _is_terminal(cycle.get("terminal")):
            errors.append({"code": "CYCLE_NO_LONGER_CLOSED", "name": name})
        for field in ("sig_parked_by", "sig_park_reason"):
            if cycle.get(field):
                errors.append({"code": "CYCLE_ALREADY_HAS_PARK_DATA", "name": name, "field": field})
        closure_event = item.get("closure_event")
        event = by_event.get(closure_event)
        if not event or event.get("event_code") != "SITE_CLOSED" or event.get("cycle") != name:
            errors.append({"code": "CLOSURE_EVENT_MISSING_OR_MISLINKED", "name": name, "event": closure_event})

    # A scope collision would make the preserved scope ambiguous in live routing.
    selected_cycles = [by_cycle[name] for name in selected if name in by_cycle]
    open_scopes = {
        _key(row): row["name"] for row in cycles
        if row.get("name") not in selected
        and not _is_terminal(row.get("terminal"))
        and row.get("sig_lifecycle") != "Parked"
    }
    for row in selected_cycles:
        scope = _key(row)
        if scope in open_scopes:
            errors.append({"code": "OPEN_SCOPE_CONFLICT", "name": row["name"], "other": open_scopes[scope]})
    return errors


def parked_values(*, actor, parked_at):
    if not actor:
        raise ValueError("parking actor is required")
    return {
        "terminal": 0,
        "sig_lifecycle": "Parked",
        "sig_parked_at": parked_at,
        "sig_parked_by": actor,
        "sig_park_reason": MIGRATION_REASON,
    }
