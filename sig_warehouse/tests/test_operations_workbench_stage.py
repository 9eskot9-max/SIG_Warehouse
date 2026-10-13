"""Evidence-stage regressions for the Operations Workbench read model."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _workbench():
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda: lambda function: function
    sys.modules["frappe"] = frappe
    source = Path(__file__).resolve().parents[1] / "sig_warehouse" / "operations_workbench.py"
    spec = importlib.util.spec_from_file_location("operations_workbench_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Row(dict):
    __getattr__ = dict.get


def _cycle(**overrides):
    row = Row(name="ZBH874|WO-1|20260823", site_key="ZBH874", project="Incident",
              erp_project="10001134", po="10001134", wo="WO-1", stage="4 - As-Built",
              terminal=0, ho_at="2026-08-23 14:59:46", asbuilt_at=None,
              stage_due_on="2026-09-06", is_delayed=1, is_aged=1)
    row.update(overrides)
    return row


def test_gcl_opens_asbuilt_without_earlier_imported_evidence():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(), {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    assert cycle["stage"] == "As-Built BOQ"
    assert [(item["key"], item["owner_role"]) for item in cycle["work"]] == [("asbuilt", "pm")]
    pm_tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    assert [(task["kind"], task["stage"], task["status"]) for task in pm_tasks] == [
        ("stage", "As-Built BOQ", "Review due"),
        ("closure", "Cycle closure", "Explicit action"),
    ]
    co_tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "co"}])
    assert [task["kind"] for task in co_tasks] == ["closure"]


def test_completed_asbuilt_or_invoice_does_not_create_review_work():
    workbench = _workbench()
    project = {"name": "10001134", "custom_family": "Incident"}
    for row in (_cycle(asbuilt_at="2026-08-24 10:00:00"),
                _cycle(invoice_at="2026-08-25 10:00:00")):
        cycle = workbench._cycle_view(row, project, "2026-10-13")
        assert cycle["work"] == []
        assert cycle["needs_review"] is False
        tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
        assert [task["kind"] for task in tasks] == ["closure"]


def test_gcl_keeps_parallel_handover_work_when_preparation_is_evidenced():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    assert {(item["key"], item["owner_role"]) for item in cycle["work"]} == {
        ("tags", "co"), ("photos", "co"), ("asbuilt", "pm")}


def test_age_alone_does_not_create_a_review_task():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, stage="1 - Initial"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    assert cycle["work"] == []
    assert cycle["needs_review"] is False
    tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    assert [task["kind"] for task in tasks] == ["closure"]
