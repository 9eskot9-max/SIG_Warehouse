import importlib.util
import sys
import types
from pathlib import Path

import pytest


def load(monkeypatch, anomalous):
    calls = []
    fake = types.ModuleType("frappe")
    def sql(query, values):
        calls.append((query, values))
        return [(anomalous,)] if query.startswith("SELECT") else []
    fake.db = types.SimpleNamespace(sql=sql)
    fake.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
    monkeypatch.setitem(sys.modules, "frappe", fake)
    path = Path(__file__).parents[1] / "sig_warehouse/patches/v1_0/repair_router_legacy_reference_type.py"
    spec = importlib.util.spec_from_file_location("router_reference_patch_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, calls


def test_repairs_only_legacy_value_with_empty_reference(monkeypatch):
    patch, calls = load(monkeypatch, 0)
    patch.execute()
    assert len(calls) == 2
    assert calls[1][1] == (r"\nPurchase Order\nPurchase Invoice",)
    assert "COALESCE(payment_reference, '') = ''" in calls[1][0]


def test_refuses_to_change_a_linked_reference(monkeypatch):
    patch, calls = load(monkeypatch, 1)
    with pytest.raises(ValueError, match="linked records"):
        patch.execute()
    assert len(calls) == 1
