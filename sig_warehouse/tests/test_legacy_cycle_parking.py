import json
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from sig_warehouse.sig_warehouse.legacy_cycle_parking import parked_values, validate


def sample():
    manifest = [{
        "name": "SITE|PO|20260101", "modified": "2026-10-01 10:00:00.000000",
        "site_key": "SITE", "po": "PO", "wo": "WO", "closure_event": "EV1",
        "sig_lifecycle": None, "sig_parked_at": None,
    }]
    cycles = [{
        "name": "SITE|PO|20260101", "modified": "2026-10-01 10:00:00.000000",
        "terminal": 1, "site_key": "SITE", "po": "PO", "wo": "WO",
        "sig_lifecycle": None, "sig_parked_at": None, "sig_parked_by": None,
        "sig_park_reason": None,
    }]
    events = [{"name": "EV1", "event_code": "SITE_CLOSED", "cycle": "SITE|PO|20260101"}]
    return manifest, cycles, events


def test_reviewed_live_manifest_has_exact_scope_and_event_fields():
    path = Path(__file__).parents[1] / "sig_warehouse" / "patches" / "v1_0" / "park_legacy_site_cycles_20261116.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) == 136
    assert len({row["name"] for row in rows}) == 136
    assert len({row["closure_event"] for row in rows}) == 136
    assert all({"modified", "site_key", "po", "wo", "sig_lifecycle", "sig_parked_at"} <= row.keys() for row in rows)


def test_preflight_accepts_exact_unchanged_cycle_and_closure_event():
    assert validate(*sample(), expected_count=1) == []


def test_preflight_rejects_changed_row_missing_event_and_successor_scope():
    manifest, cycles, events = sample()
    cycles[0]["modified"] = "changed"
    cycles.append({"name": "SUCCESSOR", "terminal": 0, "site_key": "SITE", "po": "PO", "sig_lifecycle": "Open"})
    errors = validate(manifest, cycles, [], expected_count=1)
    codes = {error["code"] for error in errors}
    assert {"CYCLE_CHANGED", "CLOSURE_EVENT_MISSING_OR_MISLINKED", "OPEN_SCOPE_CONFLICT"} <= codes


def test_preflight_rejects_partial_or_duplicate_manifest():
    manifest, cycles, events = sample()
    errors = validate(manifest * 2, cycles, events, expected_count=1)
    assert {error["code"] for error in errors} >= {"UNEXPECTED_MANIFEST_COUNT", "MISSING_OR_DUPLICATE_MANIFEST_NAME"}


def test_parked_values_are_compact_and_require_actor():
    values = parked_values(actor="Administrator", parked_at="2026-11-16 12:00:00")
    assert values["terminal"] == 0
    assert values["sig_lifecycle"] == "Parked"
    assert values["sig_park_reason"] == "Legacy in-progress work; original closure retained in history."
    with pytest.raises(ValueError):
        parked_values(actor="", parked_at="2026-11-16 12:00:00")


def test_patch_updates_only_reviewed_rows_and_preserves_closure_history():
    path = Path(__file__).parents[1] / "sig_warehouse" / "patches" / "v1_0" / "park_legacy_site_cycles_20261116.py"
    manifest_path = path.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cycles = [{
        **{key: row.get(key) for key in ("name", "modified", "site_key", "po", "wo", "sig_lifecycle", "sig_parked_at")},
        "terminal": 1, "sig_parked_by": None, "sig_park_reason": None, "closed_on": "2026-10-01",
    } for row in manifest]
    cycles.append({
        "name": "UNRELATED|PO|1", "modified": "2026-10-01", "terminal": 0,
        "site_key": "UNRELATED", "po": "PO", "wo": "", "sig_lifecycle": "Open",
        "sig_parked_at": None, "sig_parked_by": None, "sig_park_reason": None,
    })
    events = [{"name": row["closure_event"], "event_code": "SITE_CLOSED", "cycle": row["name"]} for row in manifest]
    writes = []

    class DB:
        def exists(self, doctype, name):
            return name == "Administrator"

        def set_value(self, doctype, name, values, update_modified=True):
            row = next(item for item in cycles if item["name"] == name)
            row.update(values)
            writes.append(name)

    fake = types.SimpleNamespace(
        db=DB(), session=types.SimpleNamespace(user="Administrator"),
        utils=types.SimpleNamespace(now_datetime=lambda: "2026-11-16 12:00:00"),
        get_all=lambda doctype, **kwargs: cycles if doctype == "SIG Site Cycle" else events,
        throw=lambda message: (_ for _ in ()).throw(RuntimeError(message)),
    )
    with patch.dict(sys.modules, {"frappe": fake}):
        spec = importlib.util.spec_from_file_location("park_legacy_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.execute()
    assert len(writes) == 136 and len(set(writes)) == 136
    assert all(row["sig_lifecycle"] == "Parked" and row["terminal"] == 0 for row in cycles[:136])
    assert all(row["closed_on"] == "2026-10-01" for row in cycles[:136])
    assert cycles[-1]["sig_lifecycle"] == "Open" and cycles[-1]["terminal"] == 0
