import importlib.util
import sys
import types
from pathlib import Path

import pytest


def load(monkeypatch, rows):
    state = {"rows": list(rows), "clears": 0}
    fake = types.ModuleType("frappe")
    fake.get_all = lambda *a, **k: list(state["rows"])
    fake.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
    fake.clear_cache = lambda **kwargs: state.update(clears=state["clears"] + 1)
    fake.get_doc = lambda d: types.SimpleNamespace(insert=lambda **kwargs: state["rows"].append(d))
    monkeypatch.setitem(sys.modules, "frappe", fake)
    path = Path(__file__).parents[1] / "sig_warehouse/patches/v1_0/preserve_payment_entry_admin_delete.py"
    spec = importlib.util.spec_from_file_location("pe_grant_patch_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, state


def test_existing_grant_is_repeatable(monkeypatch):
    patch, state = load(monkeypatch, [])
    state["rows"] = list(patch.BASELINE) + [patch.GRANT]
    patch.execute()
    assert state["clears"] == 0 and len(state["rows"]) == 6


def test_adds_only_reviewed_grant_to_full_baseline(monkeypatch):
    patch, state = load(monkeypatch, [])
    state["rows"] = list(patch.BASELINE)
    patch.execute()
    assert patch.normalized(state["rows"]) == patch.normalized(patch.BASELINE + [patch.GRANT])
    assert state["clears"] == 1


def test_refuses_unknown_matrix(monkeypatch):
    patch, state = load(monkeypatch, [])
    state["rows"] = list(patch.BASELINE) + [patch.row("Unreviewed", read=1)]
    with pytest.raises(ValueError, match="differs"):
        patch.execute()
    assert len(state["rows"]) == 6 and state["clears"] == 0
