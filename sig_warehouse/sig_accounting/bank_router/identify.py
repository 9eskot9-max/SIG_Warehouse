"""Stage 2: who is on the other side of this line? Pure: the registry lookup is passed in."""

STRONG = ("IBAN", "ACCOUNT", "BEN_ID", "DEP_ID")


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
            bucket = active if status == "ACTIVE" else suggested if status == "SUGGESTED" else None
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
    if suggested:
        return {"status": "SUGGESTED", "counterparty": "", "candidates": sorted(suggested), "via": ""}
    return {"status": "NONE", "counterparty": "", "candidates": [], "via": ""}
