"""Read-only preflight for an explicitly selected legacy parking manifest."""


def validate_parking_manifest(manifest, live_cycles, *, expected_count=142):
    """Return per-record issues; never changes records or selects candidates.

    The manifest is an independently reviewed selection, with captured modified
    timestamp and a list of the known open successor IDs for each cycle. The
    caller must supply a complete current cycle snapshot. An empty issues list
    does not grant permission to write or prove the snapshot is complete.
    """
    issues = []
    if len(manifest) != expected_count:
        issues.append({"code": "UNEXPECTED_COUNT", "expected": expected_count, "actual": len(manifest)})
    if any(not row.get("name") for row in live_cycles):
        raise ValueError("all current cycles must have a name")
    if any(not {"terminal", "site_key", "po"} <= row.keys() or row["terminal"] not in (0, 1, False, True, "0", "1")
           for row in live_cycles):
        raise ValueError("current snapshot must include scope and terminal state for every cycle")
    names = [row["name"] for row in live_cycles]
    if len(names) != len(set(names)):
        raise ValueError("current snapshot contains duplicate cycle names")
    by_name = {row["name"]: row for row in live_cycles}
    selected = set()
    for item in manifest:
        name = item.get("name")
        if not name or name in selected:
            issues.append({"code": "MISSING_OR_DUPLICATE_NAME", "name": name})
            continue
        selected.add(name)
        row = by_name.get(name)
        if row is None:
            issues.append({"code": "CYCLE_MISSING", "name": name})
            continue
        if row.get("terminal") not in (1, True, "1"):
            issues.append({"code": "CYCLE_NOT_CLOSED", "name": name})
        if not item.get("modified") or item.get("modified") != row.get("modified"):
            issues.append({"code": "CYCLE_CHANGED_OR_VERSION_MISSING", "name": name})
        if not row.get("site_key") or not row.get("po"):
            issues.append({"code": "SCOPE_INCOMPLETE", "name": name})
            continue
        successors = sorted(other["name"] for other in live_cycles
                            if other["name"] != name and other.get("site_key") == row["site_key"]
                            and other.get("po") == row["po"] and other.get("terminal") in (0, False, "0"))
        reviewed = item.get("reviewed_open_cycles")
        if not isinstance(reviewed, list) or sorted(reviewed) != successors:
            issues.append({"code": "OPEN_SCOPE_REVIEW_NEEDED", "name": name,
                           "current_open_cycles": successors})
    return issues
