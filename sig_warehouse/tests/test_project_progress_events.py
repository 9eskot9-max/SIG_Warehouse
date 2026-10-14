"""Evidence history exposes operational facts without generator metadata."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _project_progress(query_rows):
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda: lambda function: function
    queries = []
    frappe.db = SimpleNamespace(
        exists=lambda doctype, name: True,
        sql=lambda query, values, as_dict=False: (queries.append(query), query_rows)[1],
    )
    sys.modules["frappe"] = frappe
    source = Path(__file__).resolve().parents[1] / "sig_warehouse" / "project_progress.py"
    spec = importlib.util.spec_from_file_location("project_progress_events_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, queries


def test_event_history_keeps_code_and_date_but_drops_source_metadata():
    module, queries = _project_progress([SimpleNamespace(
        event_code="TCN_GENERATED",
        occurred_at="2026-10-08 09:00:00",
        recorded_at="2026-10-08 09:00:02",
        artifact_ref="",
        event_id="batch-000001",
        source_sub="Export_TCN_MDT_CSV_And_Word_Enhanced",
    )])

    event = module.events_for("ZBH874|WO-1|20260823")[0]

    assert event == {
        "code": "TCN_GENERATED",
        "occurred_at": "2026-10-08 09:00:00",
        "recorded_at": "2026-10-08 09:00:02",
        "artifact_ref": "",
        "event_id": "batch-000001",
    }
    assert "source_sub" not in queries[0].lower()
