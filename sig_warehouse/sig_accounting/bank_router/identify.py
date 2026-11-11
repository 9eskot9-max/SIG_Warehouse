"""Stage 2: who is on the other side of this line? Pure: the registry lookup is passed in."""

STRONG = ("IBAN", "ACCOUNT", "BEN_ID", "DEP_ID", "SADAD_CODE")


def identify(identifiers, lookup):
    """Resolve identifiers to a Counterparty.

    `lookup(kind, value)` returns [(counterparty, status)] with status ACTIVE or SUGGESTED.
    Returns {status, counterparty, candidates, via}. status is one of
    IDENTIFIED, CONFLICT, SUGGESTED, NONE.
    """
    active = {}
    suggested = {}
    for kind, value in identifiers:
        for counterparty, status in lookup(kind, value):
            # Names can be truncated or shared, so a name only suggests, until Finance has confirmed that exact statement name
            # (format-scoped, from the router) for one payee: then the same name next time is the same payee.
            confirmed_name = status == "CONFIRMED" and kind.startswith("NAME_")
            bucket = (active if (status == "ACTIVE" and kind in STRONG) or confirmed_name
                      else suggested if status in ("ACTIVE", "SUGGESTED", "CONFIRMED") else None)
            if bucket is None:
                continue
            bucket.setdefault(counterparty, set()).add(kind)
    strong_hits = {cp: kinds for cp, kinds in active.items() if kinds & set(STRONG)}
    if len(strong_hits) > 1:
        return {"status": "CONFLICT", "counterparty": "", "candidates": sorted(strong_hits), "via": ""}
    if len(strong_hits) == 1:
        cp, kinds = next(iter(strong_hits.items()))
        return {"status": "IDENTIFIED", "counterparty": cp, "candidates": [cp], "via": sorted(kinds)[0]}
    if len(active) == 1:
        cp, kinds = next(iter(active.items()))
        return {"status": "IDENTIFIED", "counterparty": cp, "candidates": [cp], "via": sorted(kinds)[0]}
    if len(active) > 1:
        return {"status": "CONFLICT", "counterparty": "", "candidates": sorted(active), "via": ""}
    # Prefer format-specific name hints. Older generic name hints remain
    # usable as suggestions when no specific hint exists.
    scoped = {cp: kinds for cp, kinds in suggested.items() if any(kind.startswith("NAME_") for kind in kinds)}
    if scoped:
        return {"status": "SUGGESTED", "counterparty": "", "candidates": sorted(scoped), "via": ""}
    if suggested:
        return {"status": "SUGGESTED", "counterparty": "", "candidates": sorted(suggested), "via": ""}
    return {"status": "NONE", "counterparty": "", "candidates": [], "via": ""}
