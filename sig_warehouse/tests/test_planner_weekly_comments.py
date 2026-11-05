from datetime import date, datetime
import importlib.util
from pathlib import Path
from contextlib import nullcontext
import sys
import types

import pytest


@pytest.fixture
def api(monkeypatch):
    frappe = types.ModuleType("frappe")
    frappe.whitelist = lambda **kwargs: lambda fn: fn
    frappe._ = lambda text: text
    frappe.PermissionError = PermissionError
    frappe.throw = lambda message, exc=ValueError: (_ for _ in ()).throw(exc(message))
    frappe.session = types.SimpleNamespace(user="pm@example.com")
    frappe.has_permission = lambda *args: True
    frappe.get_list = lambda *args, **kwargs: [types.SimpleNamespace(name="EMP-1", employee_name="PM")]
    frappe.db = types.SimpleNamespace(exists=lambda *args: False, commit=lambda: None)
    frappe.get_all = lambda *args, **kwargs: []
    monkeypatch.setitem(sys.modules, "frappe", frappe)
    planner = types.ModuleType("sig_warehouse.sig_warehouse.field_planner_api")
    planner._require_access = lambda: None
    planner._riyadh_now = lambda: datetime(2026, 11, 8, 19, 0)
    monkeypatch.setitem(sys.modules, planner.__name__, planner)
    path = Path(__file__).parents[1] / "sig_operations" / "planner_weekly_comments.py"
    spec = importlib.util.spec_from_file_location("planner_comments_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sunday_riyadh_cutoff_keeps_prior_week_until_7pm(api):
    assert api.period_start(datetime(2026, 11, 8, 18, 59, 59)) == date(2026, 11, 1)
    assert api.period_start(datetime(2026, 11, 8, 19, 0, 0)) == date(2026, 11, 8)
    assert api.period_start(datetime(2026, 11, 9, 9, 0, 0)) == date(2026, 11, 8)


def test_no_record_returns_empty_comments_without_creating_one(api):
    result = api.get_comments()
    assert result["comments"] == {"last_week": "", "this_week": "", "erp_plan": ""}
    assert result["period_start"] == "2026-11-08"
    assert result["next_reset"] == "2026-11-15 19:00"


def test_rejects_stale_period_and_oversized_text_before_write(api):
    with pytest.raises(ValueError, match="period has changed"):
        api.save_comments("2026-11-01", last_week="old")
    with pytest.raises(ValueError, match="4,000"):
        api.save_comments("2026-11-08", last_week="x" * 4001)


def test_rejects_missing_or_ambiguous_employee_link(api):
    api.frappe.get_list = lambda *args, **kwargs: []
    with pytest.raises(PermissionError, match="unique active Employee"):
        api.get_comments()
    api.frappe.get_list = lambda *args, **kwargs: [object(), object()]
    with pytest.raises(PermissionError, match="unique active Employee"):
        api.get_comments()


def test_rejects_a_record_with_another_employee_identity(api):
    api.frappe.db.exists = lambda *args: True
    api.frappe.get_doc = lambda *args: types.SimpleNamespace(employee="EMP-OTHER", period_start="2026-11-08")
    with pytest.raises(PermissionError, match="identity mismatch"):
        api.get_comments()


def test_save_is_scoped_to_employee_and_rejects_stale_write(api):
    records = {}

    class Doc:
        def __init__(self, values):
            self.__dict__.update(values)
            self.modified = ""

        def get(self, key):
            return getattr(self, key, "")

        def update(self, values):
            self.__dict__.update(values)

        def save(self, ignore_permissions=False):
            assert ignore_permissions
            self.modified = str(int(self.modified or 0) + 1)
            records[self.entry_key] = self

    api.frappe.get_list = lambda *args, **kwargs: [types.SimpleNamespace(
        name=api.frappe.session.user, employee_name=api.frappe.session.user)]
    api.frappe.db.exists = lambda doctype, name: name in records
    api.frappe.get_doc = lambda doctype, name=None: Doc(doctype) if isinstance(doctype, dict) else records[name]
    api.frappe.cache = lambda: types.SimpleNamespace(lock=lambda *args, **kwargs: nullcontext())
    first = api.save_comments("2026-11-08", last_week="Finished A", this_week="Plan B", erp_plan="Move C")
    assert first["comments"] == {"last_week": "Finished A", "this_week": "Plan B", "erp_plan": "Move C"}
    with pytest.raises(ValueError, match="another session"):
        api.save_comments("2026-11-08", last_week="stale")
    second = api.save_comments("2026-11-08", last_week="Updated", modified=first["modified"])
    assert second["comments"]["last_week"] == "Updated"
    api.frappe.session.user = "other@example.com"
    assert api.get_comments()["comments"]["last_week"] == ""
