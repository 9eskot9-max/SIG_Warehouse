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
              erp_project="10001134", po="10001134", wo="WO-1", stage="4 - As-Built",  # pre-migration stored label
              terminal=0, ho_at="2026-08-23 14:59:46", asbuilt_at=None,
              stage_due_on="2026-09-06", is_delayed=1, is_aged=1)
    row.update(overrides)
    return row


def _stage_patch():
    frappe = ModuleType("frappe")

    def throw(message):
        raise RuntimeError(message)

    frappe.throw = throw
    sys.modules["frappe"] = frappe
    source = (Path(__file__).resolve().parents[1] / "sig_warehouse" / "patches" / "v1_0"
              / "normalize_invoicing_stage_logic.py")
    spec = importlib.util.spec_from_file_location("normalize_invoicing_stage_logic_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repair_patch():
    frappe = ModuleType("frappe")
    sys.modules["frappe"] = frappe
    source = (Path(__file__).resolve().parents[1] / "sig_warehouse" / "patches" / "v1_0"
              / "repair_invoicing_delay_state.py")
    spec = importlib.util.spec_from_file_location("repair_invoicing_delay_state_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ho_evidence_moves_open_asbuilt_boq_task_to_erp_invoicing_stage():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(), {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    assert cycle["stage"] == "4 - Invoicing"
    assert [(item["key"], item["owner_role"]) for item in cycle["work"]] == [("asbuilt", "pm")]
    pm_tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    assert [(task["kind"], task["stage"], task["status"]) for task in pm_tasks] == [
        ("stage", "4 - Invoicing", "Review due"),
        ("closure", "Cycle closure", "Explicit action"),
    ]
    co_tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "co"}])
    assert [task["kind"] for task in co_tasks] == ["closure"]


def test_invoicing_writer_rewrites_sla_and_delay_keys_idempotently():
    patch = _stage_patch()
    old_script = (
        "if stage == '4 - As-Built':\n"
        "    sla = sla_asbuilt_days\n"
        "current_checkpoint = {'4 - As-Built': 'asbuilt'}\n"
        "checkpoints = 'initial\\nplan\\nhandover\\nasbuilt'\n"
    )
    new_script, changed = patch._rewrite_evidence_writer(old_script)
    assert changed is True
    assert "if stage == '4 - Invoicing':" in new_script
    assert "'4 - Invoicing': 'invoicing'" in new_script
    assert "'initial\\nplan\\nhandover\\ninvoicing'" in new_script
    assert "4 - As-Built" not in new_script
    assert patch._rewrite_evidence_writer(new_script) == (new_script, False)

    class FakeDb:
        saved = None

        def set_single_value(self, doctype, fieldname, value):
            self.saved = (doctype, fieldname, value)

    db = FakeDb()
    normalized, changed = patch._persist_delay_checkpoints(
        db, "initial\nplan\nhandover\nasbuilt")
    assert changed is True
    assert normalized == "initial\nplan\nhandover\ninvoicing"
    assert db.saved == ("SIG Field Ops Settings", "delay_checkpoints", normalized)


def test_invoicing_delay_repair_restores_corrupt_checkpoint_value_without_flattening():
    patch = _repair_patch()
    corrupted = "\n".join(list("initial\nplan\nhandover\ninvoicing"))
    normalized, changed = patch._checkpoint_value(corrupted)
    assert changed is True
    assert normalized == "initial\nplan\nhandover\ninvoicing"
    assert patch._checkpoint_value(normalized) == (normalized, False)
    assert patch._checkpoint_value("initial\nplan\nhandover\nasbuilt") == (
        normalized, True)
    assert len(patch.PREVIOUSLY_DELAYED_CYCLES) == 31
    assert "ZNJ104|WO-SIG-IMP-ZNJ104-11340-Incident-23580|20260726" in patch.PREVIOUSLY_DELAYED_CYCLES


def test_cycle_summary_uses_four_erp_stages_and_closed_is_terminal():
    workbench = _workbench()
    project = {"name": "10001134", "custom_family": "Incident"}
    initial = workbench._cycle_view(_cycle(ho_at=None), project, "2026-10-13")
    plan = workbench._cycle_view(_cycle(ho_at=None, mapping_at="2026-08-19"), project, "2026-10-13")
    handover = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21"),
        project, "2026-10-13")
    invoicing = workbench._cycle_view(_cycle(), project, "2026-10-13")
    closed = workbench._cycle_view(_cycle(terminal=1, ho_at=None), project, "2026-10-13")
    assert [initial["stage"], plan["stage"], handover["stage"], invoicing["stage"]] == [
        "1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing"]
    assert closed["stage"] == "Closed"
    assert closed["terminal"] is True


def test_asbuilt_file_closes_on_its_own_evidence_and_invoicing_stage_keeps_it_visible():
    workbench = _workbench()
    project = {"name": "10001134", "custom_family": "Incident"}
    complete = workbench._cycle_view(_cycle(asbuilt_at="2026-08-24 10:00:00", ho_at=None), project, "2026-10-13")
    assert complete["work"] == []
    assert complete["needs_review"] is False
    pending = workbench._cycle_view(_cycle(invoice_at="2026-08-25 10:00:00", ho_at=None), project, "2026-10-13")
    assert pending["stage"] == "4 - Invoicing"
    assert [(item["key"], item["stage"]) for item in pending["work"]] == [("asbuilt", "4 - Invoicing")]


def test_gcl_keeps_parallel_handover_work_when_preparation_is_evidenced():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert {(item["key"], item["owner_role"]) for item in cycle["work"]} == {
        ("tags", "co"), ("photos", "co"), ("asbuilt_operational", "warehouse"), ("asbuilt", "pm")}
    operational = next(item for item in cycle["work"] if item["key"] == "asbuilt_operational")
    assert operational["stage"] == "3 - Handover"
    assert operational["source_dns"] == ["DN-1"]


def test_ho_moves_only_the_cycle_summary_and_boq_file_to_invoicing():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert cycle["stage"] == "4 - Invoicing"
    stages = {item["key"]: item.get("stage", workbench.TASK_STAGE.get(item["key"]))
              for item in cycle["work"]}
    assert stages == {
        "tags": "3 - Handover", "photos": "3 - Handover",
        "asbuilt_operational": "3 - Handover", "asbuilt": "4 - Invoicing",
    }


def test_missing_permission_to_read_operational_flag_does_not_claim_handover_complete():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21",
              tags_at="2026-08-22", photos_at="2026-08-22", asbuilt_at="2026-08-23"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13", operational=None)
    assert cycle["stage"] == "3 - Handover"
    assert cycle["asbuilt_operational"]["visible"] is False
    assert cycle["asbuilt_operational"]["closed"] is None


def test_age_alone_does_not_create_a_review_task():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, stage="1 - Initial"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    assert cycle["work"] == []
    assert cycle["needs_review"] is False
    tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    assert [task["kind"] for task in tasks] == ["closure"]


def test_asbuilt_operational_closes_only_on_explicit_site_dn_flag():
    workbench = _workbench()
    cycle_row = _cycle(site_key="ZBH874", erp_project="10001134")
    zero_qty_open = {"parent": "DN-1", "custom_site": "ZBH874", "project": "10001134",
                     "custom_return_closed": 0, "custom_qty_returned": 0}
    state = workbench._asbuilt_operational_status(cycle_row, [zero_qty_open])
    assert state == {"applicable": True, "closed": False, "source_dns": ["DN-1"]}
    closed_line = {**zero_qty_open, "parent": "DN-2", "project": "OTHER-PROJECT", "custom_return_closed": 1}
    state = workbench._asbuilt_operational_status(cycle_row, [zero_qty_open, closed_line])
    assert state["closed"] is True
    assert state["source_dns"] == ["DN-1", "DN-2"]


def test_legacy_cycle_project_family_fallback_keeps_warehouse_task_routable():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(erp_project=None, ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20",
              first_visit_at="2026-08-21"), None, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert cycle["family"] == "Incident"
    tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "warehouse"}])
    assert [task["key"] for task in tasks] == ["asbuilt_operational"]


def test_asbuilt_operational_is_not_assigned_to_pm_or_co_and_does_not_close_cycle():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    pm = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    coordinator = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "co"}])
    warehouse = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "warehouse"}])
    assert "asbuilt_operational" not in [task.get("key") for task in pm]
    assert "asbuilt_operational" not in [task.get("key") for task in coordinator]
    assert "asbuilt_operational" in [task.get("key") for task in warehouse]
    assert all(task["kind"] != "closure" for task in warehouse)


def test_cycle_closure_is_limited_to_field_ops_pm_or_co():
    workbench = _workbench()
    fake_frappe = workbench.frappe
    fake_frappe.has_permission = lambda *_args, **_kwargs: True
    fake_frappe.get_roles = lambda user: {
        "pm@example.com": ["Projects Manager", "SIG Field Ops"],
        "co@example.com": ["Projects User", "SIG Field Ops"],
        "warehouse@example.com": ["Projects User", "Stock Manager"],
    }[user]
    assert workbench._can_close_cycles("pm@example.com", [{"scope": "Incident", "role": "pm"}])
    assert workbench._can_close_cycles("co@example.com", [{"scope": "Incident", "role": "co"}])
    assert not workbench._can_close_cycles("warehouse@example.com", [{"scope": "Incident", "role": "warehouse"}])


def test_workbench_does_not_read_return_closed_for_permlevel_zero_stock_viewer():
    workbench = _workbench()
    fake_frappe = workbench.frappe
    detail_meta = type("DetailMeta", (), {
        "has_field": lambda _self, _field: True,
        "get_field": lambda _self, _field: type("Field", (), {"permlevel": 1})(),
    })()
    stock_meta = type("StockMeta", (), {"permissions": [
        type("Perm", (), {"role": "SIG Stock Viewer", "permlevel": 0, "read": 1})(),
        type("Perm", (), {"role": "SIG Stock Viewer", "permlevel": 1, "read": "0"})(),
        type("Perm", (), {"role": "Stock Manager", "permlevel": 1, "read": 1})(),
    ]})()
    fake_frappe.has_permission = lambda *_args, **_kwargs: True
    fake_frappe.get_meta = lambda doctype: detail_meta if doctype == "Stock Entry Detail" else stock_meta
    fake_frappe.get_roles = lambda _user: ["SIG Stock Viewer"]
    fake_frappe.session = type("Session", (), {"user": "viewer@example.com"})()
    assert workbench._warehouse_operational_lines([]) == ([], None)
    fake_frappe.get_roles = lambda _user: ["Stock Manager"]
    assert workbench._warehouse_operational_lines([]) == ([], True)
