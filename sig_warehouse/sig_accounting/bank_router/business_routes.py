"""Resolve a review suggestion from already identified bank evidence.

This module does not create documents or change saved decisions. Callers supply
verified identity and confirmed memories separately from mined suggestions.
"""

import json

PURPOSES = {
    "XXPC": "custody_topup",
    "XXSL": "employee_salary",
    "XXHR": "employee_advance",
    "XXSC": "person_work",
    "XXMT": "person_work",
    "XXMR": "supplier",
}

ROUTES = {
    "custody_topup": "DEBIT",
    "employee_salary": "DEBIT",
    "employee_advance": "DEBIT",
    "employee_expense": "DEBIT",
    "own_ledger": "DEBIT",
    "bill": "DEBIT",
    "supplier": "DEBIT",
    "person_work": "DEBIT",
    "client_payout": "DEBIT",
    "bank_service": "DEBIT",
    "other_out": "DEBIT",
    "client_receipt": "CREDIT",
    "other_in": "CREDIT",
}


def legacy_route_proposals(counterparty):
    """Propose only explicit purpose-specific legacy decisions with complete targets."""
    raw = counterparty.get("purpose_defaults_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return {"proposals": [], "held": ["invalid legacy defaults"]}
    if not isinstance(raw, dict):
        return {"proposals": [], "held": ["invalid legacy defaults"]}
    proposals, held = [], []
    for purpose, value in raw.items():
        purpose = str(purpose).upper()
        if not isinstance(value, dict):
            held.append(purpose)
            continue
        treatment = str(value.get("treatment") or "").upper()
        account = str(value.get("account") or "").strip()
        route = PURPOSES.get(purpose, "")
        party_type, party = "", ""
        if treatment == "PAYMENT_ENTRY" and purpose in ("XXMR", "XXSC", "XXMT"):
            party_type, party = "Supplier", str(counterparty.get("supplier") or "").strip()
            route = "supplier" if purpose == "XXMR" else "person_work"
            account = ""
        elif treatment == "JOURNAL_ENTRY" and purpose in ("XXSC", "XXMT"):
            route = "person_work"
        elif treatment != "JOURNAL_ENTRY" or purpose not in ("XXPC", "XXSL", "XXHR"):
            held.append(purpose)
            continue
        if purpose in ("XXPC", "XXSL", "XXHR") and not counterparty.get("employee"):
            held.append(purpose)
            continue
        if purpose == "XXPC":
            account = str(counterparty.get("custody_account") or "").strip()
        if not route or (not account and not party):
            held.append(purpose)
            continue
        proposals.append({"route": route, "purpose": purpose, "direction": "DEBIT", "account": account,
                          "party_type": party_type, "party": party, "petty_cash": purpose == "XXPC"})
    return {"proposals": proposals, "held": held}


def resolve_route(movement, counterparty=None, memories=()):
    """Return a suggestion and the evidence that supports it for one line."""
    party = counterparty or {}
    direction = str(movement.get("direction") or "").upper()
    category = str(movement.get("category") or "").upper()
    result = {"route": "", "account": "", "state": "ASK", "evidence": []}

    if movement.get("erp_document"):
        return {**result, "state": "LINKED", "evidence": ["existing_document"]}
    if movement.get("paired_transfer"):
        return {**result, "route": "own_transfer", "state": "CONFIRM", "evidence": ["paired_transfer"]}
    if movement.get("is_tawal"):
        return {**result, "route": "tawal", "state": "SPECIALIST", "evidence": ["tawal"]}
    if movement.get("is_sadad") and direction == "DEBIT":
        account = movement.get("biller_account") or ""
        return {**result, "route": "bill", "account": account,
                "state": "CONFIRM" if account else "ASK", "evidence": ["sadad"]}

    if direction not in ("CREDIT", "DEBIT"):
        return result
    confirmed = [m for m in memories if m.get("confirmed") is True
                 and ROUTES.get(m.get("route")) == direction
                 and (not m.get("direction") or m.get("direction") == direction)]
    matching = [m for m in confirmed if category and m.get("purpose") == category]
    if category and not matching and category in ("XXSL", "XXHR", "XXMR"):
        route = PURPOSES[category]
        matching = [m for m in confirmed if m.get("route") == route and m.get("purpose") == route.upper()]
    if not category:
        matching = confirmed if len(confirmed) == 1 else []
        if party.get("employee") and matching and matching[0].get("route") == "custody_topup":
            matching = []
    if len(matching) == 1:
        memory = matching[0]
        return {**result, "route": memory["route"], "account": memory.get("account") or "",
                "party_type": memory.get("party_type") or "", "party": memory.get("party") or "",
                "petty_cash": bool(memory.get("petty_cash")),
                "state": "ASK", "evidence": ["confirmed_memory"]}

    if direction == "CREDIT":
        route = "client_receipt" if party.get("customer") else "other_in"
    elif party.get("company_ledger"):
        route = "own_ledger"
    elif party.get("employee"):
        route = PURPOSES.get(category, "") if category in ("XXPC", "XXSL", "XXHR") else ""
    elif category in ("XXSC", "XXMT", "XXMR"):
        route = PURPOSES[category]
    elif party.get("supplier"):
        route = "supplier"
    else:
        route = ""
    if route:
        result.update(route=route, evidence=["tx_category" if category in PURPOSES else "party_type"])
        if route == "own_ledger":
            result["account"] = party.get("company_ledger") or ""
            result["evidence"] = ["sheet_label"]
        elif route == "custody_topup":
            result["account"] = party.get("custody_account") or ""
    return result
