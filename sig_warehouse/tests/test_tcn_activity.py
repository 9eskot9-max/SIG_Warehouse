import importlib.util
import os
from datetime import date, datetime

_here = os.path.dirname(__file__)


def _load(name, *path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_here, "..", *path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ta = _load("tcn_activity", "sig_warehouse", "tcn_activity.py")


def t(code, start, end=None):
    return {"activity": code, "start": datetime.fromisoformat(start), "end": datetime.fromisoformat(end) if end else None}


def test_category_mirrors_rv80_purpose_reason():
    assert ta.category("pat") == "PAT"
    assert ta.category("Survey") == "SURVEY"
    assert ta.category("LiveLoadDC") == "INSTALL"
    assert ta.category("DMHVAC") == "DISMANTLE"
    assert ta.category("SU") is None


def test_visit_inside_window_takes_tcn_type():
    assert ta.match([t("PAT", "2026-11-03 00:00", "2026-11-05 23:00")], date(2026, 11, 5)) == ("PAT", "PAT", "")


def test_one_day_slack_and_outside():
    tcns = [t("PAT", "2026-11-03 00:00")]
    assert ta.match(tcns, date(2026, 11, 2))[0] == "PAT"
    assert ta.match(tcns, date(2026, 11, 4))[0] == "PAT"
    assert ta.match(tcns, date(2026, 11, 5)) == (None, "", "")


def test_nearest_tcn_wins():
    tcns = [t("DC", "2026-11-01 00:00"), t("PAT", "2026-11-10 00:00")]
    assert ta.match(tcns, date(2026, 11, 10))[0] == "PAT"


def test_same_category_codes_join_scope():
    tcns = [t("HVAC", "2026-11-03 00:00"), t("DC", "2026-11-03 00:00")]
    assert ta.match(tcns, date(2026, 11, 3)) == ("INSTALL", "DC+HVAC", "")


def test_conflicting_types_are_left_for_review():
    tcns = [t("PAT", "2026-11-03 00:00"), t("DC", "2026-11-03 00:00")]
    assert ta.match(tcns, date(2026, 11, 3)) == (None, "DC+PAT", "TCN_ACTIVITY_AMBIGUOUS:DC+PAT")


def test_unknown_code_is_flagged_not_guessed():
    assert ta.match([t("SU", "2026-11-03 00:00")], date(2026, 11, 3)) == (None, "SU", "TCN_ACTIVITY_UNMAPPED:SU")


def test_patch_rewrite_is_idempotent_and_adds_option():
    import sys
    import types
    sys.modules.setdefault("frappe", types.ModuleType("frappe"))
    patch = _load("tcn_patch", "sig_warehouse", "patches", "v1_0", "tcn_visit_type_20261125.py")
    src = "x = 1\n" + patch.ANCHOR + "\n"
    once = patch.rewrite(src)
    assert patch.MARKER in once and patch.rewrite(once) == once
    assert patch.add_option("\nINSTALL\nUNSPECIFIED", "PAT") == "\nINSTALL\nUNSPECIFIED\nPAT"
    assert patch.add_option("\nPAT", "PAT") == "\nPAT"


def test_resolve_accepts_tcn_created_long_before_planned_window(monkeypatch):
    import sys
    import types
    from types import SimpleNamespace
    def get_all(doctype, filters, fields, limit_page_length):
        assert "occurred_at" not in filters
        return [SimpleNamespace(planned_activity="PAT", occurred_at="2026-01-01 00:00:00",
                                tcn_window_start="2026-11-01", tcn_window_end="2026-11-02")]
    monkeypatch.setitem(sys.modules, "frappe", types.SimpleNamespace(get_all=get_all))
    assert ta.resolve("SITE1", "2026-11-01 10:00:00") == ("PAT", "PAT", "")


def test_migration_checks_script_and_metadata_before_writing(monkeypatch):
    import sys
    from types import SimpleNamespace

    import pytest

    writes = []
    script = "missing anchor"
    fieldtype = "Data"

    def get_value(doctype, *args, **kwargs):
        if doctype == "Server Script":
            return script
        if doctype == "DocField":
            return SimpleNamespace(name="activity", fieldtype=fieldtype, options="INSTALL")
        return None

    def throw(message):
        raise ValueError(message)

    fake = SimpleNamespace(
        db=SimpleNamespace(exists=lambda *args: True, get_value=get_value,
                           set_value=lambda *args, **kwargs: writes.append(args)),
        get_doc=lambda doc: SimpleNamespace(insert=lambda **kwargs: writes.append(doc)),
        clear_cache=lambda **kwargs: None,
        throw=throw,
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    patch = _load("tcn_patch_preflight", "sig_warehouse", "patches", "v1_0", "tcn_visit_type_20261125.py")

    with pytest.raises(ValueError, match="anchor"):
        patch.execute()
    assert writes == []

    script = patch.ANCHOR
    with pytest.raises(ValueError, match="Select"):
        patch.execute()
    assert writes == []

    fieldtype = "Select"
    patch.execute()
    assert writes[0]["fieldname"] == "planned_activity"
    assert writes[1] == ("DocField", "activity", "options", "INSTALL\nPAT")
    assert patch.MARKER in writes[2][3]
