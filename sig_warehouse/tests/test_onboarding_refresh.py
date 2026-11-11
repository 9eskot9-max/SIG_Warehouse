"""Focused coverage for the HR onboarding daily refresh migration."""

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


APP = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeDB:
    def __init__(self, employees, controls):
        self.employees = employees
        self.controls = controls
        self.savepoints = {}
        self.events = []

    def get_value(self, doctype, filters, field):
        assert doctype == "SIG Employee Onboarding"
        assert set(filters) == {"employee"}
        assert field == "name"
        row = next((r for r in self.controls.values() if r["employee"] == filters["employee"]), None)
        return row["name"] if row else None

    def savepoint(self, name):
        self.savepoints[name] = copy.deepcopy(self.controls)
        self.events.append(("savepoint", name))

    def rollback(self, save_point):
        self.controls.clear()
        self.controls.update(self.savepoints[save_point])
        self.events.append(("rollback", save_point))

    def release_savepoint(self, name):
        self.savepoints.pop(name)


class FakeDoc:
    def __init__(self, fake, values):
        self.fake = fake
        self.values = dict(values)

    def save(self, **kwargs):
        assert kwargs == {"ignore_permissions": True}
        self.fake.refresh(self.values["employee"])

    def insert(self, **kwargs):
        assert kwargs == {"ignore_permissions": True}
        self.fake.refresh(self.values["employee"], create=True)


class FakeFrappe:
    def __init__(self, employees, controls, fail_employee=None):
        self.db = FakeDB(employees, controls)
        self.error_logs = []
        self.processed = []
        self.fail_employee = fail_employee

    def get_all(self, doctype, **kwargs):
        assert doctype == "Employee"
        assert kwargs["filters"] == {"status": "Active"}
        assert kwargs["pluck"] == "name"
        assert kwargs["limit_page_length"] == 0
        return list(self.db.employees)

    def get_doc(self, spec, name=None):
        if isinstance(spec, str):
            assert spec == "SIG Employee Onboarding"
            return FakeDoc(self, self.db.controls[name])
        assert spec["doctype"] == "SIG Employee Onboarding"
        return FakeDoc(self, spec)

    def refresh(self, employee, create=False):
        self.processed.append(employee)
        if create:
            name = "ONB-" + employee
            self.db.controls[name] = {"name": name, "employee": employee, "refreshed": True}
        else:
            row = next(r for r in self.db.controls.values() if r["employee"] == employee)
            row["refreshed"] = True
        if employee == self.fail_employee:
            raise RuntimeError("simulated mid-refresh failure")

    def log_error(self, **kwargs):
        self.db.events.append(("log_error", kwargs["title"]))
        self.error_logs.append(kwargs)


def test_refresh_uses_linked_employee_for_existing_and_missing_controls(monkeypatch):
    fake = FakeFrappe(
        ["EMP-1", "EMP-2"],
        {"custom-name-1": {"name": "custom-name-1", "employee": "EMP-1"}},
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    module = _load("onboarding_refresh", APP / "sig_hr" / "onboarding_refresh.py")

    module.run_daily_refresh()

    assert fake.db.controls["custom-name-1"]["refreshed"] is True
    assert fake.db.controls["ONB-EMP-2"]["employee"] == "EMP-2"
    assert fake.error_logs == []


def test_failed_employee_rolls_back_only_its_writes_and_continues(monkeypatch):
    fake = FakeFrappe(
        ["EMP-1", "EMP-2", "EMP-3"],
        {"ONB-EMP-1": {"name": "ONB-EMP-1", "employee": "EMP-1"}},
        fail_employee="EMP-2",
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    module = _load("onboarding_refresh", APP / "sig_hr" / "onboarding_refresh.py")

    module.run_daily_refresh()

    assert fake.db.controls["ONB-EMP-1"]["refreshed"] is True
    assert "ONB-EMP-2" not in fake.db.controls
    assert "ONB-EMP-3" in fake.db.controls
    assert fake.processed == ["EMP-1", "EMP-2", "EMP-3"]
    assert fake.db.events.index(("rollback", "sig_hr_onboarding_2")) < fake.db.events.index(
        ("log_error", "SIG HR daily refresh failed for EMP-2")
    )


def test_migration_disables_only_named_scheduler_script_and_is_repeatable(monkeypatch):
    script = SimpleNamespace(script_type="Scheduler Event", disabled=0)
    fake = SimpleNamespace(
        db=SimpleNamespace(
            exists=lambda doctype, name: doctype == "Server Script" and name == "SIG HR Onboarding - Daily refresh",
            get_value=lambda doctype, name, field: script.disabled,
        ),
        get_doc=lambda doctype, name: script,
        clear_cache=lambda **_: None,
        throw=lambda message: (_ for _ in ()).throw(RuntimeError(message)),
    )
    saves = []
    script.save = lambda **kwargs: saves.append(kwargs)
    monkeypatch.setitem(sys.modules, "frappe", fake)
    patch = _load(
        "onboarding_refresh_patch",
        APP / "sig_warehouse" / "patches" / "v1_0" / "move_hr_onboarding_daily_refresh_to_app.py",
    )

    patch.execute()
    patch.execute()

    assert script.disabled == 1
    assert saves == [{"ignore_permissions": True}]


def test_migration_refuses_unexpected_script_type(monkeypatch):
    fake = SimpleNamespace(
        db=SimpleNamespace(exists=lambda *_: True),
        get_doc=lambda *_: SimpleNamespace(script_type="API", disabled=0),
        clear_cache=lambda **_: None,
        throw=lambda message: (_ for _ in ()).throw(RuntimeError(message)),
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    patch = _load(
        "onboarding_refresh_patch_type_guard",
        APP / "sig_warehouse" / "patches" / "v1_0" / "move_hr_onboarding_daily_refresh_to_app.py",
    )

    with pytest.raises(RuntimeError, match="not a Scheduler Event"):
        patch.execute()
