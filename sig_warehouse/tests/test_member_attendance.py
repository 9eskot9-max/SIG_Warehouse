import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "member_attendance", os.path.join(os.path.dirname(__file__), "..", "sig_warehouse", "member_attendance.py"))
ma = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ma)

SETUP = {"team_memberships": [
    {"team": "T1", "employee": "L1", "role": "leader", "effective_from": "2000-01-01", "enabled": 1},
    {"team": "T1", "employee": "M1", "role": "member", "effective_from": "2026-11-01", "effective_to": "2026-11-30", "enabled": 1},
    {"team": "T1", "employee": "M2", "role": "member", "effective_from": "2026-11-20", "enabled": 1},
    {"team": "T1", "employee": "M3", "role": "member", "effective_from": "2026-11-01", "enabled": 0},
    {"team": "T2", "employee": "M4", "role": "member", "effective_from": "2026-11-01", "enabled": 1},
]}


def test_gate_is_off_by_default():
    assert ma.MEMBER_CREDIT_ENABLED is False
    assert ma.credited_members(SETUP, "T1", "2026-11-25") == []


def test_members_are_only_the_active_members_of_that_crew_on_that_day():
    assert ma.members_on(SETUP, "T1", "2026-11-25") == ["M1", "M2"]
    assert "L1" not in ma.members_on(SETUP, "T1", "2026-11-25")          # leaders are not members
    assert ma.members_on(SETUP, "T1", "2026-11-21") == ["M1", "M2"]    # M2 starts 20 Nov
    assert ma.members_on(SETUP, "T1", "2026-12-01") == ["M2"]          # M1 ended 30 Nov
    assert ma.members_on(SETUP, "T1", "2026-10-31") == []              # before anyone started


def test_disabled_row_is_ignored():
    assert "M3" not in ma.members_on(SETUP, "T1", "2026-11-25")


def test_enabled_gate_credits_members_minus_absent():
    absent = lambda employee, day: employee == "M1" and day == "2026-11-25"
    assert ma.credited_members(SETUP, "T1", "2026-11-25", enabled=True, absent=absent) == ["M2"]
    assert ma.credited_members(SETUP, "T1", "2026-11-21", enabled=True, absent=absent) == ["M1", "M2"]


def test_placeholder_absence_marks_nobody_absent_once_enabled():
    assert ma.credited_members(SETUP, "T1", "2026-11-25", enabled=True) == ["M1", "M2"]
