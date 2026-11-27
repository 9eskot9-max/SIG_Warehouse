"""Runs the exact block the staged patch inserts into register_evidence_event, with a fake cycle table."""
import sys
import textwrap
import types

sys.modules.setdefault("frappe", types.ModuleType("frappe"))
from sig_warehouse.sig_warehouse.patches.v1_0 import tcn_scope_guard_staged as G  # noqa: E402


def run(code, cycles, target="A", wo="", cycle_hint="", po="10001045", event="TCN_GENERATED"):
    """cycles: {name: planned_activity or (planned_activity, stage, lifecycle)} in creation order -> (cycle, write_scope, flag)."""
    full = {n: v if isinstance(v, tuple) else (v, "2 - Plan", None) for n, v in cycles.items()}
    cycles = {n: v[0] for n, v in full.items()}
    rows = [types.SimpleNamespace(name=n, planned_activity=a, stage=s, sig_lifecycle=l) for n, (a, s, l) in full.items()]
    frappe = types.SimpleNamespace(
        form_dict={"planned_activity": code},
        db=types.SimpleNamespace(get_value=lambda dt, name, field: cycles.get(name)),
        get_all=lambda *a, **k: rows)
    scope = {"frappe": frappe, "event_code": event, "cyc": target, "wo": wo, "cycle_hint": cycle_hint, "po": po, "sk": "SITE"}
    exec(textwrap.dedent(G.GUARD), scope)
    return scope["cyc"], scope["tcn_write_scope"], scope["tcn_scope_flag"]


def test_undecided_survey_unknown_or_same_scope_behaves_as_today():
    for current in ("", None, "Survey", "1082", "CB", "cb"):
        assert run("CB", {"A": current}) == ("A", True, ""), current
    assert run("LifeLoadDC", {"A": "LiveLoadDC"}) == ("A", True, "")       # the sheet's misspelling is the same work


def test_cb_never_overwrites_hvac_and_moves_to_the_undecided_cycle():
    assert run("CB", {"A": "HVAC", "B": ""}) == ("B", True, "TCN_SCOPE_MOVED")
    assert run("CB", {"A": "HVAC", "B": "Survey"}) == ("B", True, "TCN_SCOPE_MOVED")


def test_a_cycle_already_on_the_same_scope_wins_over_an_undecided_one():
    assert run("CB", {"A": "HVAC", "B": "", "C": "CB"}) == ("C", True, "TCN_SCOPE_MOVED")


def test_conflict_without_a_free_cycle_adds_nothing():
    assert run("CB", {"A": "HVAC"}) == ("A", False, "TCN_SCOPE_CONFLICT")
    assert run("CB", {"A": "HVAC", "B": "FF"}) == ("A", False, "TCN_SCOPE_CONFLICT")    # never onto another filled cycle
    assert run("CB", {"A": "PAT"}) == ("A", False, "TCN_SCOPE_CONFLICT")                # finished work is decided too
    assert run("DMHVAC", {"A": "HVAC"}) == ("A", False, "TCN_SCOPE_CONFLICT")


def test_a_wo_or_explicit_cycle_is_never_moved():
    assert run("CB", {"A": "HVAC", "B": ""}, wo="WO-1") == ("A", False, "TCN_SCOPE_CONFLICT")
    assert run("CB", {"A": "HVAC", "B": ""}, cycle_hint="A") == ("A", False, "TCN_SCOPE_CONFLICT")
    assert run("CB", {"A": "HVAC", "B": ""}, po="") == ("A", False, "TCN_SCOPE_CONFLICT")


def test_survey_pat_and_unknown_codes_do_not_replace_a_decided_scope_and_raise_no_flag():
    for code in ("Survey", "PAT", "1082"):
        assert run(code, {"A": "HVAC", "B": ""}) == ("A", False, ""), code
    assert run("PAT", {"A": ""}) == ("A", True, "")


def test_blank_tcn_type_and_other_events_change_nothing():
    assert run("", {"A": "HVAC"}) == ("A", True, "")
    assert run("CB", {"A": "HVAC", "B": ""}, event="MIR_CONFIRMED") == ("A", True, "")


def test_rewrite_inserts_once_and_refuses_a_changed_script():
    source = "x = 1\n" + G.SELECT_ANCHOR + "    if True:\n" + G.WRITE_ANCHOR + G.FLAG_ANCHOR
    once = G.rewrite(source)
    assert once.count(G.MARKER) == 1 and "if pact and tcn_write_scope:" in once and G.rewrite(once) == once
    import pytest
    with pytest.raises(ValueError, match="missing or ambiguous"):
        G.rewrite(source.replace(G.FLAG_ANCHOR, ""))


def test_an_empty_cycle_that_is_parked_or_past_field_work_is_not_a_target():
    assert run("CB", {"A": "HVAC", "B": ("", "2 - Plan", "Parked")}) == ("A", False, "TCN_SCOPE_CONFLICT")
    assert run("CB", {"A": "HVAC", "B": ("", "4 - Invoicing", None)}) == ("A", False, "TCN_SCOPE_CONFLICT")
    assert run("CB", {"A": "HVAC", "B": ("", "3 - Handover", None), "C": ("", "1 - Initial", None)}) == ("C", True, "TCN_SCOPE_MOVED")
