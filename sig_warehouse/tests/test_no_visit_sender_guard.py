import importlib.util
import sys
import types
from datetime import date, datetime
from pathlib import Path

import pytest


@pytest.fixture
def sender(monkeypatch):
    frappe = types.ModuleType("frappe")
    frappe._ = lambda text: text
    frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
    frappe.whitelist = lambda *a, **kw: lambda fn: fn
    utils = types.ModuleType("frappe.utils")
    utils.getdate = lambda value: date.fromisoformat(str(value))
    utils.now_datetime = datetime.now
    utils.get_datetime_in_timezone = lambda tz: datetime(2026, 11, 15, 19)
    monkeypatch.setitem(sys.modules, "frappe", frappe)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    path = Path(__file__).resolve().parents[1] / "sig_operations" / "no_visit_nudge.py"
    spec = importlib.util.spec_from_file_location("no_visit_sender_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "build", lambda day, mode: (day, [{"employee": "E", "employee_name": "E", "phone": "966500000000", "decision": "send", "reason": ""}], False))
    return module


@pytest.mark.parametrize("day", ["2026-11-13", "2026-11-14"])
@pytest.mark.parametrize("mode", ["preview", "test", "live"])
def test_weekend_never_sends(sender, day, mode):
    result = sender.run(mode, day)
    assert result["would_send"] == 0
    assert result["rows"][0]["reason"] == "Friday or Saturday"


def test_manual_live_cannot_bypass_off_setting(sender, monkeypatch):
    monkeypatch.setattr(sender, "_setting", lambda key, default=None: "Off")
    with pytest.raises(ValueError, match="must be Live"):
        sender.run("live", "2026-11-15")
