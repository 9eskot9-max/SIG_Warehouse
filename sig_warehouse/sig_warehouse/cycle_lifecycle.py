"""Shared lifecycle interpretation for cycle records."""

from datetime import datetime


def effective_lifecycle(lifecycle, terminal):
    """Interpret pre-migration rows without modifying their stored state."""
    if terminal in (1, True, "1", "Yes", "yes"):
        return "Closed"
    if lifecycle == "Parked":
        return "Parked"
    return "Open"


def parking_transition(cycle, *, actor, parked_at, reason):
    """Prepare a parking change; the caller must enforce permissions and save atomically."""
    if not actor or not isinstance(parked_at, datetime) or not str(reason or "").strip():
        raise ValueError("Parking requires an actor, timestamp and reason")
    if effective_lifecycle(cycle.get("sig_lifecycle"), cycle.get("terminal")) != "Open":
        raise ValueError("Only an open cycle can be parked")
    return {"sig_lifecycle": "Parked", "sig_parked_at": parked_at,
            "sig_parked_by": actor, "sig_park_reason": str(reason).strip()}
