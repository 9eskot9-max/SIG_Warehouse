"""Business transition cases and migration replay safety."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from sig_warehouse.sig_warehouse.cycle_rules import derive_cycle_state


@pytest.mark.parametrize("extra,expected", [
    ({}, "2 - Plan"),
    ({"tags_at": "2026-10-04"}, "3 - Handover"),
    ({"tags_at": "2026-10-04", "first_visit_at": None, "sessions_auto_closed": 1}, "3 - Handover"),
    ({"sessions_completed": 2, "last_visit_at": "2026-10-04"}, "3 - Handover"),
    ({"sessions_completed": 1, "sessions_auto_closed": 1, "last_visit_at": "2026-10-04"}, "3 - Handover"),
    ({"mir_at": None, "tags_at": "2026-10-04", "sessions_completed": 2}, "2 - Plan"),
    ({"tcn_at": None, "tags_at": "2026-10-04", "sessions_completed": 2}, "2 - Plan"),
    ({"first_visit_at": None, "tags_at": "2026-10-04"}, "2 - Plan"),
    ({"ho_at": "2026-10-05"}, "4 - Invoicing"),
    ({"terminal": 1}, "5 - Closed"),
])
def test_handover_requires_four_milestones_or_two_visits(extra, expected):
    row = dict(stage="2 - Plan", tcn_at="2026-10-01", mir_at="2026-10-02", first_visit_at="2026-10-03")
    row.update(extra)
    assert derive_cycle_state(row)[0] == expected


def test_second_visit_anchor_does_not_reset_on_third_visit():
    row = dict(tcn_at="2026-10-01", mir_at="2026-10-02", first_visit_at="2026-10-03",
               sessions_completed=3, second_visit_at="2026-10-05", last_visit_at="2026-10-18")
    assert derive_cycle_state(row) == ("3 - Handover", "2026-10-05")


def test_invoicing_decision_is_preserved_but_handover_requires_current_evidence():
    assert derive_cycle_state(dict(stage="4 - Invoicing", stage_anchor_at="2026-09-01")) == (
        "4 - Invoicing", "2026-09-01")
    assert derive_cycle_state(dict(stage="3 - Handover", tcn_at="2026-09-01"))[0] == "2 - Plan"
    assert derive_cycle_state(dict(stage="3 - Handover", mapping_at="2026-09-01"))[0] == "1 - Initial"
    assert derive_cycle_state(dict(stage="3 - Handover", tcn_at="2026-09-01", mir_at="2026-09-02",
                                   first_visit_at="2026-09-03", sessions_completed=1,
                                   tags_at="2026-09-04"))[0] == "3 - Handover"
    assert derive_cycle_state(dict(stage="5 - Closed", terminal=0, tcn_at="2026-09-01"))[0] == "2 - Plan"
    assert derive_cycle_state(dict(stage="1 - Initial", mapping_at="2026-09-01"))[0] == "1 - Initial"


def _patch():
    frappe = ModuleType("frappe")
    frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
    sys.modules["frappe"] = frappe
    source = Path(__file__).resolve().parents[1] / "sig_warehouse/patches/v1_0/align_operations_cycle_evidence.py"
    spec = importlib.util.spec_from_file_location("cycle_evidence_patch_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_patch_embeds_canonical_rule_and_is_idempotent_without_replacing_other_writer_logic():
    patch = _patch()
    old = ("def handle(cycdoc, occurred, cyc, frappe):\n"
           "    stage = '1 - Initial'\n"
           "    stage = '3 - Handover'\n"
           "    stage = '4 - Invoicing'\n"
           "    cycdoc.set('stage', stage)\n"
           "    return stage, anchor\n")
    new = patch.rewrite_evidence_writer(old)
    assert patch.rewrite_evidence_writer(new) == new
    scope = {}
    exec(new, scope)

    class Doc(dict):
        as_dict = dict.copy

        def set(self, key, value):
            self[key] = value

    row = dict(stage="2 - Plan", tcn_at="2026-10-01", mir_at="2026-10-02", first_visit_at="2026-10-03",
               last_visit_at="2026-10-18", sessions_completed=3)
    visits = [SimpleNamespace(start_at="2026-10-03"), SimpleNamespace(start_at="2026-10-05")]
    result = scope["handle"](Doc(row), "2026-10-18", "CYCLE", SimpleNamespace(get_all=lambda *a, **k: visits))
    assert result == derive_cycle_state({**row, "second_visit_at": "2026-10-05"})
    assert result == ("3 - Handover", "2026-10-05")
    with pytest.raises(RuntimeError):
        patch.rewrite_evidence_writer("unrecognized writer")


def test_evidence_gated_handover_patch_is_registered_and_reconciles_existing_cycles(monkeypatch):
    patch = _patch()
    source = Path(__file__).resolve().parents[1] / "patches.txt"
    assert "sig_warehouse.sig_warehouse.patches.v1_0.reconcile_evidence_gated_handover" in source.read_text()

    class DB:
        scripts = {"register_evidence_event": "event script", "sig_field_ops_daily": "daily script"}
        writes = {}

        def exists(self, doctype, name):
            return name in self.scripts

        def get_value(self, doctype, name, field):
            return self.scripts[name]

        def set_value(self, doctype, name, field, value):
            self.writes[name] = value

    db = DB()
    frappe = sys.modules["frappe"]
    frappe.db = db
    frappe.clear_cache = lambda **kwargs: None
    frappe.logger = lambda name: SimpleNamespace(info=lambda *args: None)
    migration = Path(__file__).resolve().parents[1] / "sig_warehouse/patches/v1_0/reconcile_evidence_gated_handover.py"
    spec = importlib.util.spec_from_file_location("reconcile_evidence_gated_handover_test", migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "rewrite_evidence_writer", lambda text: text + " updated")
    monkeypatch.setattr(module, "rewrite_daily_flags", lambda text: text + " updated")
    reconciled = []
    monkeypatch.setattr(module, "reconcile_open_cycles", lambda: reconciled.append(True) or 26)

    module.execute()

    assert db.writes == {name: text + " updated" for name, text in db.scripts.items()}
    assert reconciled == [True]


def test_daily_writer_keeps_invoice_delay_checkpoint_and_other_settings():
    patch = _patch()
    source = "stage_checkpoint = {'3 - Handover': 'handover', '4 - As-Built': 'asbuilt'}\n# unchanged\n"
    result = patch.rewrite_daily_flags(source)
    assert "'4 - Invoicing': 'invoicing'" in result
    assert "# unchanged" in result
    assert patch.rewrite_daily_flags(result) == result

