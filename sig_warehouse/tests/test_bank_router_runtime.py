"""Transaction boundaries in the Frappe adapter around each draft insert."""
import importlib
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "sig_accounting"))


@pytest.fixture
def runtime(monkeypatch):
    frappe = types.ModuleType("frappe")
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda value: int(value or 0)
    utils.flt = lambda value: float(value or 0)
    utils.getdate = lambda value: value
    utils.now_datetime = lambda: None
    frappe.utils = utils
    monkeypatch.setitem(sys.modules, "frappe", frappe)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    sys.modules.pop("bank_router.runtime", None)
    module = importlib.import_module("bank_router.runtime")
    yield module, frappe
    sys.modules.pop("bank_router.runtime", None)


def test_failed_main_draft_insert_rolls_back_before_error_escapes(runtime):
    module, frappe = runtime
    db_calls = []
    frappe.db = types.SimpleNamespace(
        savepoint=lambda name: db_calls.append(("savepoint", name)),
        rollback=lambda **kwargs: db_calls.append(("rollback", kwargs["save_point"])),
        release_savepoint=lambda name: db_calls.append(("release", name)),
    )
    class PartialDraft:
        name = "PE-PARTIAL"
        def insert(self):
            raise RuntimeError("validation failed after partial write")
    frappe.get_doc = lambda body: PartialDraft()
    registered = []
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "bank"}, draft_fees=False,
                                         fee_account="", vat_account="")
    ctx.ledger = types.SimpleNamespace(register=lambda *args: registered.append(args))
    ctx._existing = lambda *args: None
    mv = {"key": "K1", "amount": -10, "date": "2026-11-09", "scope": "scope", "source": {}}
    with pytest.raises(RuntimeError, match="partial write"):
        ctx.create("EXPENSE_PAYMENT", mv, {"expense_account": "Travel", "label": "Person"}, [])
    assert db_calls == [("savepoint", "bank_router_main_draft"), ("rollback", "bank_router_main_draft"),
                        ("release", "bank_router_main_draft")]
    assert registered == []


def test_failed_fee_draft_insert_rolls_back_its_own_savepoint(runtime):
    module, frappe = runtime
    db_calls = []
    frappe.db = types.SimpleNamespace(
        savepoint=lambda name: db_calls.append(("savepoint", name)),
        rollback=lambda **kwargs: db_calls.append(("rollback", kwargs["save_point"])),
        release_savepoint=lambda name: db_calls.append(("release", name)),
    )
    class PartialDraft:
        def insert(self):
            raise RuntimeError("fee validation failed")
    frappe.get_doc = lambda body: PartialDraft()
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "bank"}, fee_account="Fees", vat_account="")
    ctx._existing = lambda *args: None
    mv = {"key": "K1", "amount": -10, "date": "2026-11-09", "scope": "scope", "source": {}}
    with pytest.raises(RuntimeError, match="fee validation"):
        ctx.create_fee_journal(mv, [{"amount": -1, "family": "BANK_FEE"}])
    assert db_calls == [("savepoint", "bank_router_fee_draft"), ("rollback", "bank_router_fee_draft"),
                        ("release", "bank_router_fee_draft")]
