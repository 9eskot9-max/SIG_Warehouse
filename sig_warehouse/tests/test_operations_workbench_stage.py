"""Evidence-stage regressions for the Operations Workbench read model."""
import importlib.util
from datetime import datetime
from io import BytesIO

import pytest
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _workbench():
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda **kwargs: lambda function: function
    frappe.DoesNotExistError = type("DoesNotExistError", (Exception,), {})
    frappe.db = SimpleNamespace(get_single_value=lambda *args: "{}")
    frappe.utils = SimpleNamespace(nowdate=lambda: "2026-11-16")
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
              erp_project="10001134", po="10001134", wo="WO-1", stage="1 - Initial",  # stage must follow fixture evidence
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
    ]
    co_tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "co"}])
    assert co_tasks == []


def test_a_filed_asbuilt_boq_makes_invoice_the_next_task_until_it_is_invoiced():
    workbench = _workbench()
    project = {"name": "10001134", "custom_family": "Incident"}
    filed = workbench._cycle_view(_cycle(asbuilt_at="2026-10-01 10:00:00"), project, "2026-10-13")
    assert [(i["key"], i["label"], i["stage"], i["owner_role"]) for i in filed["work"]] == [
        ("invoice", "Invoice", "4 - Invoicing", "pm")]
    tasks = workbench._stage_tasks_for_user([filed], [{"scope": "Incident", "role": "pm"}])
    assert [(t["task"] if "task" in t else t["label"], t["stage"]) for t in tasks] == [("Invoice", "4 - Invoicing")]
    invoiced = workbench._cycle_view(_cycle(asbuilt_at="2026-10-01 10:00:00", invoice_at="2026-10-05 09:00:00"), project, "2026-10-13")
    assert all(i["key"] != "invoice" for i in invoiced["work"])
    closed = workbench._cycle_view(_cycle(asbuilt_at="2026-10-01 10:00:00", terminal=1), project, "2026-10-13")
    assert closed["work"] == []


def test_cycle_response_preserves_evidence_derived_gross_value():
    workbench = _workbench()
    project = {"name": "10001134", "custom_family": "Incident"}
    cycle = workbench._cycle_view(_cycle(gross_value=39693.91), project, "2026-10-19")
    assert cycle["gross_value"] == 39693.91

    cycle_without_value = workbench._cycle_view(_cycle(gross_value=None), project, "2026-10-19")
    assert cycle_without_value["gross_value"] is None


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
    plan = workbench._cycle_view(_cycle(ho_at=None, tcn_at="2026-08-19"), project, "2026-10-13")
    handover = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"),
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
    # the As-Built task is done; billing is now the open step, so an overdue cycle stays in review until it is invoiced
    assert [(item["key"], item["stage"]) for item in complete["work"]] == [("invoice", "4 - Invoicing")]
    assert complete["needs_review"] is True
    pending = workbench._cycle_view(_cycle(invoice_at="2026-08-25 10:00:00", ho_at=None), project, "2026-10-13")
    assert pending["stage"] == "4 - Invoicing"
    assert [(item["key"], item["stage"]) for item in pending["work"]] == [("asbuilt", "4 - Invoicing")]


def test_handover_keeps_only_handover_work_when_preparation_is_evidenced():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert {(item["key"], item["owner_role"]) for item in cycle["work"]} == {
        ("tags", "co"), ("asbuilt_operational", "warehouse"), ("handover_documents", "either")}
    operational = next(item for item in cycle["work"] if item["key"] == "asbuilt_operational")
    assert operational["stage"] == "3 - Handover"
    assert operational["source_dns"] == ["DN-1"]


def test_ho_moves_cycle_to_invoicing_and_removes_all_handover_work():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert cycle["stage"] == "4 - Invoicing"
    stages = {item["key"]: item.get("stage", workbench.TASK_STAGE.get(item["key"]))
              for item in cycle["work"]}
    assert stages == {"asbuilt": "4 - Invoicing"}
    assert cycle["asbuilt_operational"]["display"] is False


def test_asbuilt_operational_status_is_only_displayed_during_handover():
    workbench = _workbench()
    operational = {"applicable": True, "closed": False, "source_dns": ["DN-1"]}
    plan = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13", operational)
    invoicing = workbench._cycle_view(
        _cycle(tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21",
               sessions_completed=2, last_visit_at="2026-08-22"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13", operational)
    assert plan["stage"] == "2 - Plan"
    assert plan["asbuilt_operational"]["display"] is False
    assert invoicing["stage"] == "4 - Invoicing"
    assert invoicing["asbuilt_operational"]["display"] is False


def test_asbuilt_boq_never_appears_as_handover_work():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20",
               first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert cycle["stage"] == "3 - Handover"
    assert "asbuilt" not in [item["key"] for item in cycle["work"]]
    assert all(item["stage"] == "3 - Handover" for item in cycle["work"])


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
    assert tasks == []


def test_cycle_closure_is_not_projected_as_a_duplicate_queue_row():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(), {"name": "10001134", "custom_family": "Incident"}, "2026-10-13")
    tasks = workbench._stage_tasks_for_user(
        [cycle], [{"scope": "Incident", "role": "pm"}])
    assert [task["key"] for task in tasks] == ["asbuilt"]
    assert all(task["kind"] == "stage" for task in tasks)


def test_site_cycles_dashboard_is_one_open_cycle_row_per_cycle_and_scoped_by_project_family():
    workbench = _workbench()
    incident = _cycle(name="INC-1", family="Incident", work=[
        {"key": "tags", "label": "Tags", "owner_role": "co", "stage": "3 - Handover"},
        {"key": "asbuilt", "label": "As-Built BOQ file", "owner_role": "pm", "stage": "4 - Invoicing"},
    ])
    capex = _cycle(name="CAP-1", family="Capex", site_key="CAPEX9")
    closed_incident = _cycle(name="INC-CLOSED", family="Incident", terminal=1)

    rows = workbench._cycles_for_user(
        [incident, capex, closed_incident], [{"scope": "Incident", "role": "pm"}])

    assert [row["name"] for row in rows] == ["INC-1"]
    assert [item["key"] for item in rows[0]["work"]] == ["tags", "asbuilt"]


def test_site_cycles_dashboard_system_manager_sees_all_open_projects_without_closed_rows():
    workbench = _workbench()
    cycles = [
        _cycle(name="INC-1", family="Incident"),
        _cycle(name="CAP-1", family="Capex", site_key="CAPEX9"),
        _cycle(name="CLOSED-1", family="Incident", terminal=1),
    ]

    rows = workbench._cycles_for_user(cycles, [], can_see_all=True)

    assert [row["name"] for row in rows] == ["INC-1", "CAP-1"]


def test_site_cycles_dashboard_endpoint_returns_all_project_scopes_for_page_roles():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.get_roles = lambda _user: ["Projects Manager"]
    frappe.has_permission = lambda doctype, ptype: doctype == "SIG Site Cycle" and ptype == "read"
    frappe.PermissionError = RuntimeError
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))
    captured = {}
    source_cycles = [
        _cycle(name="INC-1", family="Incident"),
        _cycle(name="CAP-1", family="Capex", site_key="CAPEX9"),
        _cycle(name="CLOSED-1", family="Incident", terminal=1),
    ]

    def overview(all_project_cycles=False):
        captured["all_project_cycles"] = all_project_cycles
        return {"cycles": source_cycles, "task_route": {"memberships": []},
                "complete": {"cycles": True}, "can_export": True}

    workbench._get_overview = overview
    workbench._all_visible = lambda *args, **kwargs: (source_cycles, True)
    frappe.db.sql = lambda *args, **kwargs: []
    frappe.utils.now_datetime = lambda: datetime(2026, 11, 16)
    result = workbench.get_cycle_dashboard()

    assert captured["all_project_cycles"] is True
    assert result["scope"] == "all"
    assert [cycle["name"] for cycle in result["cycles"]] == ["INC-1", "CAP-1"]


def test_site_cycles_dashboard_endpoint_rejects_users_outside_page_roles():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="viewer@example.com")
    frappe.get_roles = lambda _user: ["Accounts User"]
    frappe.has_permission = lambda *_args: True
    frappe.PermissionError = RuntimeError
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))

    try:
        workbench.get_cycle_dashboard()
    except RuntimeError as error:
        assert "Operations page role" in str(error)
    else:
        raise AssertionError("a non-page role received the all-project cycle dashboard")


def test_site_cycles_dashboard_warehouse_only_sees_cycles_with_routed_warehouse_work():
    workbench = _workbench()
    cycles = [
        _cycle(name="INC-DN", family="Incident", work=[
            {"key": "asbuilt_operational", "label": "As-Built Operational", "owner_role": "warehouse"},
            {"key": "asbuilt", "label": "As-Built BOQ file", "owner_role": "pm"},
        ]),
        _cycle(name="INC-NO-DN", family="Incident", work=[
            {"key": "asbuilt", "label": "As-Built BOQ file", "owner_role": "pm"},
        ]),
    ]

    rows = workbench._cycles_for_user(cycles, [{"scope": "Incident", "role": "warehouse"}])

    assert [row["name"] for row in rows] == ["INC-DN"]
    assert [item["key"] for item in rows[0]["work"]] == ["asbuilt_operational"]


def test_site_cycles_dashboard_unrouted_user_gets_no_cycle_rows():
    workbench = _workbench()
    rows = workbench._cycles_for_user([_cycle(name="INC-1", family="Incident")], [])
    assert rows == []


def _configured(workbench, rows):
    import json
    workbench.frappe.db = SimpleNamespace(get_single_value=lambda *args: json.dumps({"ops_team_members": rows}))


def _ops(employee, role, family="Capex", **extra):
    return {"id": employee + role + family, "employee": employee, "role": role, "family": family, "project": "",
            "effective_from": "2026-11-05", "effective_to": "", "enabled": True, **extra}


def test_configured_roles_decide_task_audience_strictly():
    workbench = _workbench()
    _configured(workbench, [_ops("PM1", "pm"), _ops("CO1", "coordinator"), _ops("WH1", "warehouse", family="")])
    pm = workbench._operations_team_memberships("PM1")
    co = workbench._operations_team_memberships("CO1")
    wh = workbench._operations_team_memberships("WH1")
    assert [(m["scope"], m["role"]) for m in pm] == [("Capex", "pm")]
    assert [(m["scope"], m["role"]) for m in co] == [("Capex", "co")]
    assert {(m["scope"], m["role"]) for m in wh} == {(f, "warehouse") for f in ("Capex", "Incident", "Colocation")}
    # the As-Built BOQ file is PM only, Tags coordinator only, a shared task is for both
    assert workbench._task_audience("Capex", "pm", pm) and not workbench._task_audience("Capex", "pm", co)
    assert workbench._task_audience("Capex", "co", co) and not workbench._task_audience("Capex", "co", pm)
    assert workbench._task_audience("Capex", "either", pm) and workbench._task_audience("Capex", "either", co)
    assert not workbench._task_audience("Capex", "either", wh) and workbench._task_audience("Incident", "warehouse", wh)
    assert not workbench._task_audience("Incident", "pm", pm)


def test_project_row_replaces_the_family_team_for_that_role_only():
    workbench = _workbench()
    _configured(workbench, [_ops("PM1", "pm"), _ops("PM2", "pm", project="P-9"), _ops("CO1", "coordinator")])
    pm1, pm2, co = (workbench._operations_team_memberships(e) for e in ("PM1", "PM2", "CO1"))
    assert not workbench._task_audience("Capex", "pm", pm1, "P-9") and workbench._task_audience("Capex", "pm", pm1, "P-1")
    assert workbench._task_audience("Capex", "pm", pm2, "P-9") and not workbench._task_audience("Capex", "pm", pm2, "P-1")
    assert workbench._task_audience("Capex", "co", co, "P-9")


def test_expired_or_disabled_rows_give_no_membership():
    workbench = _workbench()
    _configured(workbench, [_ops("A", "pm", effective_to="2026-11-10"), _ops("B", "pm", enabled=False), _ops("C", "pm", effective_from="2026-12-01")])
    assert workbench._operations_team_memberships() == []


def test_removed_hardcoded_rosters_stay_removed():
    workbench = _workbench()
    for name in ("OPS_ROSTER", "WAREHOUSE_USERS", "OPS_OWNER_NAMES", "WAREHOUSE_OWNER_NAMES", "PEOPLE_MODEL_ACTIVE"):
        assert not hasattr(workbench, name)


def test_cycle_export_includes_named_owners_and_keeps_late_columns_aligned():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.has_permission = lambda *_args, **_kwargs: True
    frappe.local = SimpleNamespace(response=SimpleNamespace())
    workbench.get_overview = lambda: {
        "complete": {"cycles": True, "asbuilt_operational": True},
        "cycles": [{
            "name": "INC-1", "site": "ZBH874", "wo": "WO-1", "ba": "10001134",
            "alias": "Incident", "project_id": "10001134", "family": "Incident",
            "stage": "4 - Invoicing", "terminal": False,
            "work": [{"label": "As-Built BOQ file", "owner_names": ["Sohil", "Raheem"]}],
            "needs_review": False, "is_delayed": False, "is_aged": False,
            "stage_due_on": "", "delay_reason": "", "delay_note": "",
            "closed_on": "", "closed_by": "",
            "events": {"mapping_at": "MAPPING", "boq_at": "BOQ", "tcn_at": "TCN",
                       "mir_at": "MIR", "first_visit_at": "VISIT", "tags_at": "TAGS",
                       "photos_at": "PHOTOS", "asbuilt_at": "ASBUILT",
                       "warranty_at": "WARRANTY", "ho_at": "HO", "invoice_at": "INVOICE"},
            "asbuilt_operational": {"visible": True, "applicable": True,
                                    "closed": True, "source_dns": ["DN-1"]},
        }],
        "stage_tasks": [{
            "id": "INC-1::asbuilt", "cycle": "INC-1", "stage": "4 - Invoicing",
            "label": "As-Built BOQ file", "owner_names": ["Sohil", "Raheem"],
            "status": "Pending evidence", "expected_evidence": "ASBUILT_BOQ_GENERATED",
            "review_reason": "",
        }],
    }

    workbench.export_workbook(filter="cycles")

    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(frappe.local.response.filecontent), data_only=True)
    cycles = workbook["Cycles"]
    tasks = workbook["Stage tasks"]
    assert cycles.cell(1, 11).value == "Pending item owners"
    assert cycles.cell(2, 11).value == "As-Built BOQ file: Sohil / Raheem"
    assert cycles.cell(1, 28).value == "As-Built Operational status"
    assert cycles.cell(2, 28).value == "Closed"
    assert cycles.cell(2, 29).value == "DN-1"
    assert cycles.cell(2, 30).value == "WARRANTY"
    assert cycles.cell(2, 31).value == "HO"
    assert cycles.cell(2, 32).value == "INVOICE"
    assert tasks.cell(1, 10).value == "Owner(s)"
    assert tasks.cell(2, 10).value == "Sohil / Raheem"


def test_site_cycles_export_uses_the_all_project_pool_only_for_cycle_reports():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.get_roles = lambda _user: ["Projects Manager"]
    frappe.has_permission = lambda *_args: True
    frappe.PermissionError = RuntimeError
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))
    frappe.local = SimpleNamespace(response=SimpleNamespace())
    captured = {}
    cycle = {
        "name": "INC-1", "site": "ZBH874", "wo": "WO-1", "ba": "10001134",
        "alias": "Incident", "project_id": "10001134", "family": "Incident",
        "stage": "4 - Invoicing", "terminal": False, "work": [], "needs_review": False,
        "is_delayed": False, "is_aged": False, "stage_due_on": "", "delay_reason": "",
        "delay_note": "", "closed_on": "", "closed_by": "", "events": {},
        "asbuilt_operational": {"closed": True, "source_dns": []},
    }

    def overview(all_project_cycles=False):
        captured["all_project_cycles"] = all_project_cycles
        return {"complete": {"cycles": True, "asbuilt_operational": True},
                "cycles": [cycle], "stage_tasks": []}

    workbench._get_overview = overview
    workbench.get_overview = lambda: (_ for _ in ()).throw(AssertionError("personal overview used"))
    workbench.export_workbook(filter="cycles", scope="all")

    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(frappe.local.response.filecontent), data_only=True)
    assert captured["all_project_cycles"] is True
    assert workbook["Cycles"].cell(2, 1).value == "INC-1"
    assert workbook["Stage tasks"].max_row == 1


def test_site_cycles_export_keeps_cycle_workbook_when_warehouse_coverage_is_unavailable():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.get_roles = lambda _user: ["Projects Manager"]
    frappe.has_permission = lambda *_args: True
    frappe.PermissionError = RuntimeError
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))
    frappe.local = SimpleNamespace(response=SimpleNamespace())
    cycle = {
        "name": "INC-1", "site": "ZBH874", "wo": "WO-1", "ba": "10001134",
        "alias": "Incident", "project_id": "10001134", "family": "Incident",
        "stage": "4 - Invoicing", "terminal": False, "work": [], "needs_review": False,
        "is_delayed": False, "is_aged": False, "stage_due_on": "", "events": {},
        "asbuilt_operational": {"visible": False, "applicable": None,
                                 "closed": None, "source_dns": []},
    }
    workbench._get_overview = lambda all_project_cycles=False: {
        "complete": {"cycles": True, "asbuilt_operational": None},
        "operational_access": "unavailable", "cycles": [cycle], "stage_tasks": [],
    }

    workbench.export_workbook(filter="cycles", scope="all")

    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(frappe.local.response.filecontent), data_only=True)
    assert workbook["Cycles"].cell(2, 1).value == "INC-1"
    assert workbook["Cycles"].cell(2, 28).value == "Coverage could not be verified"
    assert workbook["Cycles"].cell(2, 29).value in (None, "")
    assert "Warehouse tasks may be missing" in workbook["Export notes"].cell(2, 2).value


def test_site_cycles_export_shows_open_status_without_stock_entry_read_access():
    workbench = _workbench()
    frappe = sys.modules["frappe"]
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.get_roles = lambda _user: ["Projects Manager"]
    frappe.has_permission = lambda doctype, _ptype: doctype == "SIG Site Cycle"
    frappe.PermissionError = RuntimeError
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))
    frappe.local = SimpleNamespace(response=SimpleNamespace())
    cycle = {
        "name": "INC-1", "site": "ZBH874", "wo": "WO-1", "ba": "10001134",
        "alias": "Incident", "project_id": "10001134", "family": "Incident",
        "stage": "4 - Invoicing", "terminal": False, "work": [], "needs_review": False,
        "is_delayed": False, "is_aged": False, "stage_due_on": "", "events": {},
        "asbuilt_operational": {"visible": True, "applicable": True,
                                 "closed": False, "source_dns": []},
    }
    workbench._get_overview = lambda all_project_cycles=False: {
        "complete": {"cycles": True, "asbuilt_operational": True},
        "operational_access": "available", "cycles": [cycle], "stage_tasks": [],
    }

    workbench.export_workbook(filter="cycles", scope="all")

    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(frappe.local.response.filecontent), data_only=True)
    assert workbook["Cycles"].cell(2, 28).value == "Open"
    assert workbook["Cycles"].cell(2, 29).value in (None, "")
    assert "Export notes" not in workbook.sheetnames


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
              first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"), None, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    assert cycle["family"] == "Incident"
    tasks = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "warehouse"}])
    assert [task["key"] for task in tasks] == ["asbuilt_operational"]


def test_asbuilt_operational_is_not_assigned_to_pm_or_co_and_does_not_close_cycle():
    workbench = _workbench()
    cycle = workbench._cycle_view(
        _cycle(ho_at=None, tcn_at="2026-08-20", mir_at="2026-08-20", first_visit_at="2026-08-21", sessions_completed=2, last_visit_at="2026-08-22"),
        {"name": "10001134", "custom_family": "Incident"}, "2026-10-13",
        {"applicable": True, "closed": False, "source_dns": ["DN-1"]})
    pm = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "pm"}])
    coordinator = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "co"}])
    warehouse = workbench._stage_tasks_for_user([cycle], [{"scope": "Incident", "role": "warehouse"}])
    assert "asbuilt_operational" not in [task.get("key") for task in pm]
    assert "asbuilt_operational" not in [task.get("key") for task in coordinator]
    assert "asbuilt_operational" in [task.get("key") for task in warehouse]
    assert all(task["kind"] == "stage" for task in warehouse)


def test_cycle_closure_is_limited_to_field_ops_pm_or_co():
    workbench = _workbench()
    fake_frappe = workbench.frappe
    fake_frappe.has_permission = lambda *_args, **_kwargs: True
    fake_frappe.get_roles = lambda user: {
        "pm@example.com": ["Projects Manager", "SIG Field Ops"],
        "co@example.com": ["Projects User", "SIG Field Ops"],
        "warehouse@example.com": ["Projects User", "Stock Manager"],
    }[user]
    fake_frappe.get_list = lambda doctype, filters, **kwargs: [
        Row(employee_name={"pm@example.com": "Mohammed Sohail Mohammed Ilyas",
                           "co@example.com": "Arshad ahmed abdulhameed",
                           "warehouse@example.com": "Ramzan"}[filters["user_id"]])
    ]
    assert workbench._can_close_cycles("pm@example.com", [{"scope": "Incident", "role": "pm"}])
    assert workbench._can_close_cycles("co@example.com", [{"scope": "Incident", "role": "co"}])
    assert not workbench._can_close_cycles("warehouse@example.com", [{"scope": "Incident", "role": "warehouse"}])


def test_workbench_exposes_only_cycle_status_without_stock_entry_field_access():
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
    fake_frappe.has_permission = lambda doctype, ptype, **_kwargs: (
        doctype == "SIG Site Cycle" and ptype == "read"
    )
    fake_frappe.get_meta = lambda doctype: detail_meta if doctype == "Stock Entry Detail" else stock_meta
    fake_frappe.get_roles = lambda _user: ["SIG Stock Viewer"]
    fake_frappe.session = type("Session", (), {"user": "viewer@example.com"})()
    query_log = {}

    def read_scoped_lines(query, params, as_dict):
        query_log.update({"query": query, "params": params, "as_dict": as_dict})
        return [Row(custom_site="ZBH874", custom_return_closed=1)]

    fake_frappe.db = SimpleNamespace(sql=read_scoped_lines)
    cycle = Row(name="INC-1", site_key="ZBH874", site="ZBH874", terminal=0)

    lines, complete = workbench._warehouse_operational_lines([cycle])
    state = workbench._asbuilt_operational_status(cycle, lines)

    assert complete is True
    assert state == {"applicable": True, "closed": True, "source_dns": []}
    assert "ZBH874" in query_log["params"]
    assert "UPPER(IFNULL(sed.custom_site" in query_log["query"]
    assert "Material Issue" in query_log["params"]
    assert "SELECT sed.parent" not in query_log["query"]
    assert "MAX(CASE WHEN IFNULL(sed.custom_return_closed" in query_log["query"]
    assert "GROUP BY UPPER(IFNULL(sed.custom_site" in query_log["query"]
    assert query_log["as_dict"] is True
    assert "DN-1" not in str(lines)


def test_source_dn_names_are_limited_to_stock_entries_visible_to_the_user():
    workbench = _workbench()
    fake_frappe = workbench.frappe
    detail_meta = type("DetailMeta", (), {
        "has_field": lambda _self, _field: True,
        "get_field": lambda _self, _field: type("Field", (), {"permlevel": 1})(),
    })()
    stock_meta = type("StockMeta", (), {"permissions": [
        type("Perm", (), {"role": "Stock Manager", "permlevel": 1, "read": 1})(),
    ]})()
    fake_frappe.has_permission = lambda doctype, ptype, **_kwargs: (
        (doctype, ptype) in {("SIG Site Cycle", "read"), ("Stock Entry", "read")}
    )
    fake_frappe.get_roles = lambda _user: ["Stock Manager"]
    fake_frappe.session = type("Session", (), {"user": "warehouse@example.com"})()
    fake_frappe.get_meta = lambda doctype: detail_meta if doctype == "Stock Entry Detail" else stock_meta
    fake_frappe.get_list = lambda doctype, **_kwargs: (
        [Row(name="DN-ALLOWED")] if doctype == "Stock Entry" else []
    )
    queries = []

    def read_lines(query, params, as_dict):
        queries.append((query, params))
        if "GROUP BY" in query:
            return [Row(custom_site="ZBH874", custom_return_closed=1)]
        return [Row(parent="DN-ALLOWED", custom_site="ZBH874", custom_return_closed=1)]

    fake_frappe.db = SimpleNamespace(sql=read_lines)
    cycle = Row(name="INC-1", site_key="ZBH874", site="ZBH874", terminal=0)

    lines, complete = workbench._warehouse_operational_lines([cycle])
    state = workbench._asbuilt_operational_status(cycle, lines)

    assert complete is True
    assert state == {"applicable": True, "closed": True, "source_dns": ["DN-ALLOWED"]}
    assert any("DN-ALLOWED" in params for _query, params in queries)
    assert "DN-RESTRICTED" not in str(queries)


def test_warehouse_status_query_is_limited_to_open_cycles_in_the_callers_scope():
    workbench = _workbench()
    rows = [
        Row(name="INC-1", erp_project="INC-PROJ", project="Incident", terminal=0,
            site_key="ZBH874"),
        Row(name="CAP-1", erp_project="CAP-PROJ", project="Capex", terminal=0,
            site_key="CAP001"),
        Row(name="INC-CLOSED", erp_project="INC-PROJ", project="Incident", terminal=1,
            site_key="ZBH875"),
    ]
    projects = {
        "INC-PROJ": {"custom_family": "Incident"},
        "CAP-PROJ": {"custom_family": "Capex"},
    }

    scoped = workbench._warehouse_cycles_in_scope(
        rows, projects, [{"scope": "Incident", "role": "pm"}], can_see_all=False)
    all_project = workbench._warehouse_cycles_in_scope(rows, projects, [], can_see_all=True)

    assert [row.name for row in scoped] == ["INC-1"]
    assert [row.name for row in all_project] == ["INC-1", "CAP-1"]


def test_one_visit_moves_cycle_to_handover_with_tags_still_pending():
    workbench = _workbench()
    row = _cycle(ho_at=None, stage="2 - Plan", tcn_at="2026-10-01", mir_at="2026-10-02",
                 first_visit_at="2026-10-03", sessions_auto_closed=1)
    cycle = workbench._cycle_view(row, {"custom_family": "Incident"}, "2026-10-19")
    assert cycle["stage"] == "3 - Handover"
    assert {w["key"] for w in cycle["work"]} == {"tags", "handover_documents"}
    assert all(w["stage"] == "3 - Handover" for w in cycle["work"])


def test_partial_legacy_plan_does_not_need_mapping_before_it_can_show_missing_work():
    workbench = _workbench()
    cycle = workbench._cycle_view(_cycle(ho_at=None, mir_at="2026-10-02"), {"custom_family": "Incident"}, "2026-10-19")
    assert cycle["stage"] == "2 - Plan"
    assert {w["key"] for w in cycle["work"]} == {"tcn", "visit"}


def test_saved_pm_invoicing_decision_does_not_reopen_old_preparation_tasks():
    workbench = _workbench()
    cycle = workbench._cycle_view(_cycle(stage="4 - Invoicing", ho_at=None, mir_at="2026-10-02"),
                                 {"custom_family": "Incident"}, "2026-10-19")
    assert cycle["stage"] == "4 - Invoicing"
    assert [(w["key"], w["stage"]) for w in cycle["work"]] == [("asbuilt", "4 - Invoicing")]


def test_bulk_closure_skips_a_cycle_visited_recently_unless_included():
    workbench = _workbench()
    fake = workbench.frappe
    cycles = {
        "RECENT": Row(name="RECENT", terminal=0, last_visit_at="2026-11-11 19:30:47", site_id="S1", site_key="S1",
                      project="5g", po="", wo=""),
        "IDLE": Row(name="IDLE", terminal=0, last_visit_at="2026-09-01 10:00:00", site_id="S2", site_key="S2",
                    project="5g", po="", wo=""),
    }
    saved, events = [], []
    for row in cycles.values():
        row["save"] = lambda row=row: saved.append(row["name"])
    fake.session = SimpleNamespace(user="pm@example.com")
    fake.throw = lambda message, *args: (_ for _ in ()).throw(RuntimeError(message))
    fake.PermissionError = PermissionError
    fake.has_permission = lambda *args, **kwargs: True
    fake.db = SimpleNamespace(exists=lambda doctype, name: name in cycles)
    fake.get_doc = lambda arg, name=None: cycles[name] if isinstance(arg, str) else SimpleNamespace(
        insert=lambda: events.append(arg))
    fake.utils = SimpleNamespace(now=lambda: "2026-11-15 12:00:00", nowdate=lambda: "2026-11-15",
                                 add_days=lambda day, n: "2026-11-01")
    workbench._can_close_cycles = lambda user, memberships=None: True
    result = workbench.close_cycles(["RECENT", "IDLE"], "tidy", outcome="Completed")
    assert result["closed"] == ["IDLE"] and result["skipped_recent_visit"] == ["RECENT"]
    assert result["already_closed"] == 0 and saved == ["IDLE"]
    result = workbench.close_cycles(["RECENT"], "tidy", include_recent=1, outcome="Cancelled")
    assert result["closed"] == ["RECENT"] and result["skipped_recent_visit"] == []

    assert events[0]["sig_close_outcome"] == "Completed"
    assert events[1]["sig_close_outcome"] == "Cancelled"
    assert events[1]["sig_close_reason"] == "tidy"
    assert cycles["RECENT"].sig_lifecycle == "Closed"


def test_park_and_reopen_use_existing_write_scope_and_keep_an_audit():
    workbench = _workbench()
    fake = workbench.frappe
    comments = []

    class Cycle(Row):
        def set(self, key, value):
            self[key] = value

        def save(self):
            pass

        def add_comment(self, kind, message):
            comments.append((kind, message))

    cycle = Cycle(name="OPEN", terminal=0)
    terminal = Cycle(name="CLOSED", terminal=1, sig_lifecycle="Parked")
    cycles = {"OPEN": cycle, "CLOSED": terminal, "DENIED": Cycle(name="DENIED", terminal=0)}
    fake.session = SimpleNamespace(user="pm@example.com")
    fake.throw = lambda message, exc=ValueError: (_ for _ in ()).throw(exc(message))
    fake.PermissionError = PermissionError
    fake.has_permission = lambda doctype, kind, name: name != "DENIED"
    fake.db = SimpleNamespace(exists=lambda doctype, name: name in cycles)
    fake.get_doc = lambda doctype, name: cycles[name]
    fake.utils = SimpleNamespace(now=lambda: "2026-11-16 12:00:00", get_datetime=datetime.fromisoformat)
    workbench._can_close_cycles = lambda user: True

    with pytest.raises(PermissionError):
        workbench.park_cycles(["OPEN", "DENIED"], "waiting")
    assert "sig_lifecycle" not in cycle
    assert comments == []

    assert workbench.park_cycles(["OPEN", "OPEN"], "<vendor>")["parked"] == ["OPEN"]
    assert cycle["sig_lifecycle"] == "Parked"
    assert comments[-1] == ("Info", "Parked Closed: &lt;vendor&gt;")
    with pytest.raises(ValueError):
        workbench.park_cycles(["OPEN"], "different reason")
    assert cycle["sig_park_reason"] == "<vendor>"

    assert workbench.reopen_parked_cycle("OPEN")["result"] == "reopened"
    assert cycle["sig_lifecycle"] == "Open"
    assert comments[-1][0] == "Info" and "Reopened" in comments[-1][1]
    with pytest.raises(ValueError):
        workbench.reopen_parked_cycle("CLOSED")
