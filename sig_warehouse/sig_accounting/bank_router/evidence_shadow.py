"""Read-only comparison of bank evidence with the counterparty registry."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .adapters.snb import narrative, parse
from .text import hint_key, normalize_text

STRONG = {"ACCOUNT", "IBAN", "BEN_ID", "DEP_ID"}


def _date(value):
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _amount(value):
    try:
        result = Decimal(str(value).replace(",", ""))
        return abs(result) if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def build_registry(counterparties, identifiers, beneficiaries=()):
    """Build indexes without collapsing shared identifiers into one owner."""
    active = {str(c["name"]): c for c in counterparties if c.get("status") == "ACTIVE" and c.get("name")}
    indexes = defaultdict(set)
    suggested_ids = defaultdict(set)
    names = defaultdict(set)
    keys = defaultdict(set)
    for name, cp in active.items():
        key = str(cp.get("am_key") or "").strip()
        if key:
            keys[key].add(name)
        label = normalize_text(cp.get("display_name"))
        if len(label.replace(" ", "")) >= 6:
            names[label].add(name)
    for item in identifiers:
        cp, kind = str(item.get("counterparty") or ""), str(item.get("kind") or "").upper()
        if cp not in active or item.get("status") not in ("ACTIVE", "SUGGESTED"):
            continue
        value = hint_key(kind, item.get("value") or item.get("normalized"))
        if not value:
            continue
        if kind.startswith("NAME"):
            if len(value.replace(" ", "")) >= 6:
                names[value].add(cp)
        else:
            (indexes if item.get("status") == "ACTIVE" else suggested_ids)[(kind, value)].add(cp)
    # Preserve collisions visible in the source registry even where the
    # existing identifier table could store only one owner for a key.
    for row in beneficiaries:
        owners = keys.get(str(row.get("idempotency_key") or row.get("source_key") or "").strip(), set())
        if str(row.get("status") or "").strip().lower() != "active" or len(owners) != 1:
            continue
        cp = next(iter(owners))
        for kind, raw in (("ACCOUNT", row.get("account_number")), ("IBAN", row.get("iban"))):
            value = hint_key(kind, raw)
            if value and ((kind == "ACCOUNT" and value.isdigit() and len(value) >= 8) or
                          (kind == "IBAN" and value.startswith("sa") and len(value) == 24)):
                suggested_ids[(kind, value)].add(cp)
        for raw in (row.get("beneficiary_name"), row.get("nickname")):
            label = normalize_text(raw)
            if len(label.replace(" ", "")) >= 6:
                names[label].add(cp)
    return {"active": active, "ids": indexes, "suggested_ids": suggested_ids, "names": names, "keys": keys}


def propose(source, registry):
    """Strong identifiers identify a unique counterparty; names only suggest."""
    signals = parse(source)
    if signals.get("own_account"):
        return {"status": "OWN_ACCOUNT", "candidates": []}
    hits, weak_ids = defaultdict(set), set()
    for kind, raw in signals.get("identifiers", []):
        if kind not in STRONG:
            continue
        for cp in registry["ids"].get((kind, hint_key(kind, raw)), set()):
            hits[cp].add(kind)
        weak_ids.update(registry["suggested_ids"].get((kind, hint_key(kind, raw)), set()))
    if hits and weak_ids.difference(hits):
        return {"status": "CONFLICT", "candidates": sorted(set(hits) | weak_ids)}
    if len(hits) > 1:
        return {"status": "CONFLICT", "candidates": sorted(hits)}
    if len(hits) == 1:
        cp = next(iter(hits))
        return {"status": "IDENTIFIED", "counterparty": cp, "candidates": [cp], "evidence": sorted(hits[cp])}
    text = " " + normalize_text(narrative(source)) + " "
    names = set(weak_ids)
    for label, owners in registry["names"].items():
        if " " + label + " " in text:
            names.update(owners)
    if names:
        return {"status": "SUGGESTED", "candidates": sorted(names), "evidence": ["NARRATIVE_NAME"]}
    return {"status": "NONE", "candidates": []}


def compare_requests(movements, requests, registry):
    """Return only one-to-one candidate request matches; never infer execution."""
    options = defaultdict(list)
    reverse = defaultdict(list)
    for i, movement in enumerate(movements):
        source = movement.get("source") or {}
        if str(source.get("direction") or "").upper() != "DEBIT":
            continue
        proposal = propose(source, registry)
        if proposal.get("status") != "IDENTIFIED":
            continue
        day, amount = _date(source.get("event_date")), _amount(source.get("signed_amount"))
        if day is None or amount is None:
            continue
        for j, request in enumerate(requests):
            if str(request.get("execution_status") or "") != "MAKER_READBACK":
                continue
            tail = str(request.get("source_account_tail") or "").strip()
            if tail and (not tail.isdigit() or not str(source.get("account_tail") or "").endswith(tail)):
                continue
            owners = registry["keys"].get(str(request.get("beneficiary_key") or ""), set())
            request_day, request_amount = _date(request.get("initiated_at")), _amount(request.get("amount"))
            if len(owners) != 1 or proposal["counterparty"] not in owners or request_day is None or request_amount != amount:
                continue
            if 0 <= (day - request_day).days <= 2:
                options[i].append(j)
                reverse[j].append(i)
    result = []
    for i, indexes in options.items():
        if len(indexes) == 1 and len(reverse[indexes[0]]) == 1:
            result.append({"movement_index": i, "request_index": indexes[0], "status": "CANDIDATE_IN_BATCH"})
        else:
            result.append({"movement_index": i, "request_indexes": indexes, "status": "AMBIGUOUS_IN_BATCH"})
    return result


def score(predictions, confirmed):
    """Count only explicit human-confirmed counterparties as ground truth."""
    counts = {"confirmed": 0, "correct": 0, "wrong": 0, "ambiguous": 0, "no_suggestion": 0}
    for prediction, actual in zip(predictions, confirmed):
        if not actual:
            continue
        counts["confirmed"] += 1
        candidates = prediction.get("candidates") or []
        if len(candidates) > 1:
            counts["ambiguous"] += 1
        elif not candidates:
            counts["no_suggestion"] += 1
        elif candidates[0] == actual:
            counts["correct"] += 1
        else:
            counts["wrong"] += 1
    return counts
