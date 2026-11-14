import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("nv", Path(__file__).resolve().parents[1] / "sig_operations" / "no_visit_logic.py")
nv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nv)


def emp(name, status="Active", phone="966500000000"):
    return {"name": name, "employee_name": name.title(), "cell_number": phone, "status": status}


def decide(**kw):
    base = dict(employees=[emp("a"), emp("b"), emp("c")], roster={"a", "b", "c"}, active_today=set(),
                on_leave_or_holiday=set(), exclude=set(), already_sent=set())
    base.update(kw)
    rows, truncated = nv.decide(**base)
    return {r["employee"]: r for r in rows}, truncated


def test_everyone_without_activity_is_sent():
    rows, _ = decide()
    assert {k for k, r in rows.items() if r["decision"] == "send"} == {"a", "b", "c"}


def test_people_with_a_visit_or_report_today_are_skipped():
    rows, _ = decide(active_today={"a"})
    assert rows["a"]["decision"] == "skip" and rows["b"]["decision"] == "send"


def test_leave_holiday_exclusion_inactive_and_missing_phone_are_skipped():
    rows, _ = decide(employees=[emp("a"), emp("b"), emp("c"), emp("d", status="Left"), emp("e", phone=None)],
                     roster={"a", "b", "c", "d", "e"}, on_leave_or_holiday={"a"}, exclude={"b"})
    assert [rows[k]["reason"] for k in "abcde"] == [
        "leave or holiday", "excluded", "no visit recorded today", "not active", "no phone number"]


def test_only_planner_roster_is_considered():
    rows, _ = decide(roster={"a"})
    assert set(rows) == {"a"}


def test_one_message_per_person_per_day():
    rows, _ = decide(already_sent={"a", "b"})
    assert rows["a"]["reason"] == "already messaged today" and rows["c"]["decision"] == "send"


def test_per_run_cap():
    people = [emp(f"e{i:02d}") for i in range(5)]
    out, truncated = nv.decide(people, {p["name"] for p in people}, set(), set(), set(), set(), max_recipients=3)
    assert truncated and [r["decision"] for r in out].count("send") == 3


def test_message_is_bilingual_and_test_prefix_names_the_person():
    text = nv.compose_message("03-11-2026")
    assert "03-11-2026" in text and "SIG" in text and "لم يتم تسجيل" in text
    assert nv.compose_message("03-11-2026", test_for="Ali").startswith("[TEST - would go to Ali]")


def test_parse_ids_accepts_commas_spaces_and_lines():
    assert nv.parse_ids("HR-EMP-00001, HR-EMP-00002\nHR-EMP-00003") == {"HR-EMP-00001", "HR-EMP-00002", "HR-EMP-00003"}


def test_roster_uses_enabled_crews_and_dated_unique_leaders():
    setup = {"operational_teams": [{"id": "a", "enabled": 1}, {"id": "b", "enabled": 1}, {"id": "c", "enabled": 0}],
             "team_memberships": [
                 {"team": "a", "employee": "current", "role": "leader", "enabled": 1, "effective_from": "2026-11-05"},
                 {"team": "a", "employee": "old", "role": "leader", "enabled": 1, "effective_from": "2026-01-01", "effective_to": "2026-11-04"},
                 {"team": "a", "employee": "member", "role": "member", "enabled": 1, "effective_from": "2026-01-01"},
                 {"team": "b", "employee": "one", "role": "leader", "enabled": 1, "effective_from": "2026-01-01"},
                 {"team": "b", "employee": "two", "role": "leader", "enabled": 1, "effective_from": "2026-01-01"},
                 {"team": "c", "employee": "disabled", "role": "leader", "enabled": 1, "effective_from": "2026-01-01"}]}
    assert nv.planner_leaders(setup, "2026-11-11") == {"current"}
    assert nv.planner_leaders(setup, "2026-11-03") == {"old"}
