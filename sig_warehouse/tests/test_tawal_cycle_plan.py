import pytest

from sig_warehouse.sig_warehouse.tawal_cycle_plan import plan_site_cycles


def test_shortage_creates_missing_and_defers_all_closure():
    plan = plan_site_cycles(["row-1", "row-2"], ["cycle-1"])
    assert plan.assignments == (("row-1", "cycle-1"), ("row-2", None))
    assert plan.missing == 1
    assert plan.defer_closure


def test_extra_cycles_are_distinct_and_only_two_are_assigned():
    plan = plan_site_cycles(["row-1", "row-2"], ["a", "b", "c"])
    assert plan.assignments == (("row-1", "a"), ("row-2", "b"))
    assert plan.missing == 0
    assert not plan.defer_closure


def test_deferred_shortage_survives_retry_after_cycle_creation():
    plan = plan_site_cycles(["row-1", "row-2"], ["a", "b"],
                            {"row-1": "a", "row-2": "b"}, shortage_deferred=True)
    assert plan.assignments == (("row-1", "a"), ("row-2", "b"))
    assert plan.defer_closure


def test_conflicting_historical_links_are_not_reassigned():
    with pytest.raises(ValueError, match="manual reconciliation"):
        plan_site_cycles(["row-1", "row-2"], ["open"],
                         {"row-1": "closed", "row-2": "closed"})


def test_single_missing_cycle_is_recorded_as_shortage():
    plan = plan_site_cycles(["row-1"], [])
    assert plan.assignments == (("row-1", None),)
    assert plan.defer_closure
