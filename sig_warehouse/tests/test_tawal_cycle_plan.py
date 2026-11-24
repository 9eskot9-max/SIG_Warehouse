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


def test_submitted_invoice_closes_as_completed_with_one_event_per_row():
    from sig_warehouse.sig_warehouse.tawal_cycle_plan import invoice_close_event_id, invoice_close_fields
    fields = invoice_close_fields("2026-11-24 11:04:00", "finance@example.com")
    assert (fields["terminal"], fields["sig_lifecycle"], fields["sig_close_outcome"], fields["stage"]) == (1, "Closed", "Completed", "5 - Closed")
    assert fields["closed_on"] == "2026-11-24" and fields["last_event_code"] == "SITE_CLOSED"
    key = "TWAL-12-10001274-2611180895-Z95003-PO1000155097"
    assert invoice_close_event_id("SIG-SINV-26-164", key) == invoice_close_event_id("SIG-SINV-26-164", key)
    assert invoice_close_event_id("SIG-SINV-26-164", key) != invoice_close_event_id("SIG-SINV-26-165", key)


def test_close_invoice_cycle_closes_once_and_leaves_closed_cycles_alone(monkeypatch):
    import sys
    import types
    cycles = {"C1": types.SimpleNamespace(terminal=0, site_id="Z95003", site_key="Z95003", project="TAWAL", po="10001274", wo="", name="C1"),
              "C2": types.SimpleNamespace(terminal=1, site_id="Z1", site_key="Z1", project="TAWAL", po="1", wo="", name="C2")}
    for c in cycles.values():
        c.update = lambda values, c=c: c.__dict__.update(values)
        c.save = lambda **kw: None
    events = []
    fake = types.ModuleType("frappe")
    fake.get_doc = lambda first, name=None: cycles[name] if first == "SIG Site Cycle" else types.SimpleNamespace(insert=lambda **kw: events.append(first))
    fake.db = types.SimpleNamespace(exists=lambda doctype, filters: any(e["event_id"] == filters["event_id"] for e in events))
    fake.whitelist = lambda *a, **k: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, "frappe", fake)
    sys.modules.pop("sig_warehouse.sig_warehouse.tawal_invoice_evidence", None)
    from sig_warehouse.sig_warehouse.tawal_invoice_evidence import close_invoice_cycle
    assert close_invoice_cycle("C1", "SIG-SINV-26-164", "ROW-1", 1, 100, "u", "2026-11-24 11:00:00", "B")
    assert cycles["C1"].terminal == 1 and cycles["C1"].sig_close_outcome == "Completed" and len(events) == 1
    assert events[0]["source_sub"] == "TAWAL_INVOICE_ROW_CLOSE" and events[0]["event_code"] == "SITE_CLOSED"
    assert not close_invoice_cycle("C1", "SIG-SINV-26-164", "ROW-1", 1, 100, "u", "2026-11-24 11:05:00", "B")   # retry
    assert not close_invoice_cycle("C2", "SIG-SINV-26-164", "ROW-2", 2, 100, "u", "2026-11-24 11:00:00", "B")   # already closed
    assert len(events) == 1
    sys.modules.pop("sig_warehouse.sig_warehouse.tawal_invoice_evidence", None)
