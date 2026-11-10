"""Shadow matching must preserve ambiguity and never count guesses as truth."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "sig_accounting"))
from bank_router.evidence_shadow import build_registry, compare_requests, propose, score
from bank_router.engine import remembered_account
from bank_router.seed import unique_names


def fixture():
    cps = [{"name": "A", "status": "ACTIVE", "am_key": "BEN-A", "display_name": "Acme Building Company"},
           {"name": "B", "status": "ACTIVE", "am_key": "BEN-B", "display_name": "Another Company"}]
    ids = [{"counterparty": "A", "kind": "ACCOUNT", "value": "38759875000102", "status": "ACTIVE"}]
    return cps, ids


def movement():
    return {"direction": "DEBIT", "event_date": "2026-11-09", "signed_amount": -1500,
            "parser_family": "INTERNAL_BEN_ID", "detail_description": "38759875000102 BEN ID:123456"}


def test_exact_account_and_duplicate_account_conflict():
    cps, ids = fixture()
    assert propose(movement(), build_registry(cps, ids))["counterparty"] == "A"
    ids.append({"counterparty": "B", "kind": "ACCOUNT", "value": "0038759875000102", "status": "ACTIVE"})
    assert propose(movement(), build_registry(cps, ids))["status"] == "CONFLICT"


def test_name_is_a_suggestion_and_names_obey_word_boundaries():
    cps, ids = fixture()
    registry = build_registry(cps, ids)
    source = {"direction": "DEBIT", "detail_description": "Payment to Acme Building Company"}
    assert propose(source, registry) == {"status": "SUGGESTED", "candidates": ["A"], "evidence": ["NARRATIVE_NAME"]}
    source["detail_description"] = "Acme Building Companywide"
    assert propose(source, registry)["status"] == "NONE"


def test_request_matching_requires_confirmed_status_key_and_unique_movement():
    cps, ids = fixture()
    registry = build_registry(cps, ids)
    rows = [{"source": movement()}]
    req = {"beneficiary_key": "BEN-A", "amount": "1500", "initiated_at": "08/11/2026 10:30", "execution_status": "MAKER_READBACK"}
    assert compare_requests(rows, [req], registry)[0]["status"] == "CANDIDATE_IN_BATCH"
    assert not compare_requests(rows, [{**req, "execution_status": "OUTCOME_UNKNOWN"}], registry)
    assert compare_requests(rows * 2, [req], registry)[0]["status"] == "AMBIGUOUS_IN_BATCH"


def test_score_excludes_unconfirmed_decisions():
    predictions = [{"candidates": ["A"]}, {"candidates": ["B"]}, {"candidates": ["A", "B"]}]
    assert score(predictions, ["A", "", "A"]) == {"confirmed": 2, "correct": 1, "wrong": 0, "ambiguous": 1, "no_suggestion": 0}


def test_registry_source_collision_is_not_hidden_by_unique_identifier_table():
    cps, ids = fixture()
    beneficiaries = [{"idempotency_key": "BEN-B", "status": "Active", "account_number": "38759875000102"}]
    assert propose(movement(), build_registry(cps, ids, beneficiaries))["status"] == "CONFLICT"


def test_expense_defaults_follow_purpose_and_old_generic_is_not_reused():
    facts = {"expense_account": "GENERIC", "purpose_defaults_json": '{"XXSC":{"treatment":"JOURNAL_ENTRY","account":"SUBCON"},"XXMR":"PAYMENT_ENTRY"}'}
    assert remembered_account(facts, "XXSC") == "SUBCON"
    assert remembered_account(facts, "XXMT") == ""
    assert remembered_account(facts, "XXMR") == ""
    assert remembered_account(facts, "") == "GENERIC"


def test_shared_party_display_name_is_not_resolved_arbitrarily():
    assert unique_names({"a": "Shared", "b": "Shared", "c": "Unique"}) == {"Unique": "c"}
