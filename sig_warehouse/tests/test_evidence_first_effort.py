"""Regress the actual sandbox failure and new feed/task boundaries."""
import importlib.util
import inspect
from datetime import datetime
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins, safer_getattr

ROOT = Path(__file__).resolve().parents[1] / "sig_warehouse"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage_rule_executes_in_sandbox_without_unpack_guard():
    rule = load("sandbox_rule", ROOT / "cycle_rules.py")
    namespace = {"__builtins__": {**safe_builtins, "min": min, "max": max},
                 "_getattr_": safer_getattr, "_getiter_": iter,
                 "_getitem_": lambda obj, key: obj[key]}
    assert "_unpack_sequence_" not in namespace
    exec(compile_restricted(inspect.getsource(rule.derive_cycle_state), "stage_rule", "exec"), namespace)
    cases = [
        {}, {"terminal": 1}, {"tcn_at": "2026-10-20 10:00:00"},
        {"ho_at": "2026-10-20 11:00:00"},
        {"tcn_at": "2026-10-18", "mir_at": "2026-10-18", "first_visit_at": "2026-10-19",
         "sessions_completed": 2, "last_visit_at": "2026-10-20"},
    ]
    for row in cases:
        assert namespace["derive_cycle_state"](row) == rule.derive_cycle_state(row)


def feed_module():
    fake = ModuleType("frappe")
    fake.whitelist = lambda: lambda fn: fn
    sys.modules["frappe"] = fake
    return load("feed_first_effort", ROOT / "field_feed.py"), fake


def test_post_failure_keeps_original_trace_and_continues_next_record():
    feed, fake = feed_module()
    logs, rollbacks = [], []
    long_key = "Capex2|" + "x" * 170
    fake.get_all = lambda *args, **kwargs: [long_key, "good-session"]
    fake.db = SimpleNamespace(rollback=lambda: rollbacks.append(True))
    fake.log_error = lambda **kwargs: logs.append(kwargs)

    def post(name):
        if name == long_key:
            raise NameError("original evidence failure")
        return {"result": "created", "site_created": False}

    feed.post_session = post
    assert feed._post_pending() == {"posted": 1, "failed": 1, "sites_created": 0}
    assert len(rollbacks) == 1
    assert len(logs[0]["title"]) <= 140
    assert long_key in logs[0]["message"]
    assert "NameError: original evidence failure" in logs[0]["message"]


def test_capex2_keeps_discussion_identity_and_uses_capex_family():
    sessions = load("session_first_effort", ROOT / "field_sessions.py")
    feed, _fake = feed_module()
    assert sessions.STREAM_BY_GROUP["120363025557580310@g.us"] == "ticpx2"
    assert feed.STREAM_PROJECT["ticpx2"] == "Capex"
    # These suffixes are actual existing Capex cycle keys, not base-site aliases.
    assert sessions.classify_text("ZMK549R11 Start")[:2] == ("START", "ZMK549R11")
    assert sessions.classify_text("ZMK549R12 End")[:2] == ("END", "ZMK549R12")


def test_capex2_does_not_silently_adopt_incident_cycle():
    feed, fake = feed_module()
    fake.get_all = lambda *args, **kwargs: [SimpleNamespace(
        name="INC-1", project="incident", erp_project="INC-PROJECT")]
    fake.db = SimpleNamespace(get_value=lambda *args: "Incident")
    try:
        feed._check_capex2_scope("ZAB123")
    except ValueError as exc:
        assert "scope review" in str(exc) and "INC-1" in str(exc)
    else:
        raise AssertionError("Capex2 must not be merged into Incident")


def test_capex2_import_defaults_to_preview_without_writes():
    feed, fake = feed_module()
    fake.get_roles = lambda: ["System Manager"]
    feed._now = lambda: datetime(2026, 10, 20, 0, 0)
    group = "120363025557580310@g.us"
    raw = [["2026-10-19 " + time, json.dumps({"message": {"text": text},
                                            "user": {"phone": "test-reporter"}}), key, group, "text"]
           for time, text, key in (("08:00:00", "ZAB123 Start", "start-key"),
                                  ("10:00:00", "ZAB123 End", "end-key"))]
    original = feed.fs._gviz
    feed.fs._gviz = lambda query: raw
    try:
        result = feed.sig_field_feed_import_capex2()
        assert result["result"] == "preview"
        assert result["sessions"][0]["site"] == "ZAB123"
        assert result["sessions"][0]["status"] == "COMPLETED"
        # No db/get_doc/get_all on this fake: a write or posting would fail.
    finally:
        feed.fs._gviz = original


def test_feed_failure_is_persisted_and_raised_for_scheduler():
    feed, fake = feed_module()
    fake.get_single = lambda dt: {"feed_mode": "Live", "feed_cursor": 1}
    writes, logs = [], []
    fake.db = SimpleNamespace(rollback=lambda: None, commit=lambda: None,
                             set_value=lambda *args: writes.append(args))
    fake.log_error = lambda **kwargs: logs.append(kwargs)
    feed._alert = lambda *args: None
    original = feed.fs.fetch_rows

    def unavailable(cursor):
        raise RuntimeError("Inbox unavailable")

    feed.fs.fetch_rows = unavailable
    try:
        try:
            feed.run_feed()
        except RuntimeError as exc:
            assert str(exc) == "Inbox unavailable"
        else:
            raise AssertionError("Scheduler must not report successful completion")
        assert writes[-1][2]["feed_status"] == "ERROR"
        assert "Inbox unavailable" in logs[-1]["message"]
    finally:
        feed.fs.fetch_rows = original


def test_tags_is_ongoing_for_capex_and_colocation_but_not_a_new_initial_task():
    existing = load("stage_fixture_first_effort", Path(__file__).with_name("test_operations_workbench_stage.py"))
    workbench = existing._workbench()
    for family in ("Capex", "Colocation"):
        project = {"name": "PROJECT", "custom_family": family}
        plan = workbench._cycle_view(existing._cycle(ho_at=None, tcn_at="2026-10-20"), project, "2026-10-20")
        assert "tags" in [x["key"] for x in plan["work"]]
        initial = workbench._cycle_view(existing._cycle(ho_at=None), project, "2026-10-20")
        assert "tags" not in [x["key"] for x in initial["work"]]
        invoice = workbench._cycle_view(existing._cycle(), project, "2026-10-20")
        assert "tags" not in [x["key"] for x in invoice["work"]]
        closed = workbench._cycle_view(existing._cycle(terminal=1, ho_at=None), project, "2026-10-20")
        assert closed["work"] == []


if __name__ == "__main__":
    for name, function in list(globals().items()):
        if name.startswith("test_"):
            function()
            print("PASS", name)
