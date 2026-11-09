"""Pure allocation logic used by the TAWAL invoice evidence handler.

The caller serializes allocation and persists each reservation before emitting
evidence events, because the shared writer may commit one event at a time.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CyclePlan:
    assignments: tuple[tuple[str, str | None], ...]
    missing: int
    defer_closure: bool


def plan_site_cycles(row_keys, open_cycles, existing=None, shortage_deferred=False):
    """Allocate distinct open cycle IDs to invoice row keys in stable order.

    ``None`` indicates a cycle that must be created. Existing reservations
    must refer to a distinct currently open cycle. An existing closed-cycle
    link needs explicit reconciliation and must not be silently reassigned.
    ``shortage_deferred`` must be durably preserved across draft/submission.
    """
    rows = tuple(row_keys)
    cycles = tuple(open_cycles)
    existing = dict(existing or {})
    if not rows or any(not x for x in rows) or len(set(rows)) != len(rows):
        raise ValueError("Invoice row keys must be nonempty and unique")
    if any(not x for x in cycles) or len(set(cycles)) != len(cycles):
        raise ValueError("Open cycle IDs must be nonempty and unique")
    if not set(existing).issubset(rows):
        raise ValueError("A reservation refers to an unrelated row")
    reserved = tuple(existing.values())
    if (len(set(reserved)) != len(reserved)
            or any(not value or value not in cycles for value in reserved)):
        raise ValueError("Existing reservations require manual reconciliation")

    available = iter(x for x in cycles if x not in reserved)
    assigned = []
    for row in rows:
        selected = existing[row] if row in existing else next(available, None)
        assigned.append((row, selected))
    missing = sum(value is None for _, value in assigned)
    return CyclePlan(tuple(assigned), missing, bool(shortage_deferred or missing))
