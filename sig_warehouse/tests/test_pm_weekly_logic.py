import importlib.util
from datetime import date
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "pmw", Path(__file__).resolve().parents[1] / "sig_operations" / "pm_weekly_logic.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

SUN = date(2026, 11, 8)  # a Sunday
PREV = date(2026, 11, 1)


def test_week_starts_on_sunday():
    assert L.sunday_on_or_before(date(2026, 11, 8)) == SUN
    assert L.sunday_on_or_before(date(2026, 11, 12)) == SUN  # Thursday
    assert L.sunday_on_or_before(date(2026, 11, 7)) == PREV  # Saturday belongs to the previous week
    assert L.previous_week(SUN) == PREV


def test_scope_only_active_rows_for_that_employee():
    rows = [{"employee": "E1", "project": "P1", "active": 1}, {"employee": "E1", "project": "P2", "active": 0},
            {"employee": "E2", "project": "P3", "active": 1}]
    assert L.scope_projects(rows, "E1") == {"P1"}


def test_last_week_marks_visits_within_that_week_only():
    plan = [{"site": "S1", "cycle": "C1", "project": "P1", "planned_day": "2026-11-02"},
            {"site": "S2", "cycle": "C2", "project": "P1", "planned_day": "2026-11-03"},
            {"site": "S3", "cycle": "C3", "project": "P9", "planned_day": "2026-11-03"}]
    visits = [{"site": "S1", "project": "P1", "day": date(2026, 11, 2)},
              {"site": "S2", "project": "P1", "day": date(2026, 11, 8)}]  # the next Sunday is not last week
    lines = L.last_week_lines(plan, {"P1"}, PREV, visits)
    assert [(l["site"], l["visited"]) for l in lines] == [("S1", 1), ("S2", 0)]


def test_additions_are_visits_outside_the_plan_in_the_pm_projects():
    visits = [{"site": "X1", "project": "P1", "day": date(2026, 11, 4)},
              {"site": "X1", "project": "P1", "day": date(2026, 11, 5)},
              {"site": "X2", "project": "P9", "day": date(2026, 11, 4)},
              {"site": "S1", "project": "P1", "day": date(2026, 11, 4)}]
    out = L.additions(visits, PREV, {"S1"}, {"P1"})
    assert out == [{"site": "X1", "project": "P1", "visit_count": 2, "note": ""}]


def test_this_week_lines_one_per_site_for_the_projects():
    snap = [{"site": "S1", "cycle": "C1", "project": "P1", "planned_day": "2026-11-09"},
            {"site": "S1", "cycle": "C1b", "project": "P1", "planned_day": "2026-11-10"},
            {"site": "S2", "cycle": "C2", "project": "P9", "planned_day": "2026-11-09"}]
    lines = L.this_week_lines(snap, {"P1"})
    assert len(lines) == 1 and lines[0]["site"] == "S1" and lines[0]["decision"] == ""


def test_system_comment_counts_visits_misses_and_extras():
    lines = [{"visited": 1, "reason": ""}, {"visited": 0, "reason": "access"}, {"visited": 0, "reason": ""}]
    comment = L.system_comment(lines, extra=[{"site": "X"}])
    assert comment["planned"] == 3 and comment["visited"] == 1 and comment["misses"] == 2 and comment["extra"] == 1
    assert "access: 1" in comment["en"] and "no reason yet: 1" in comment["en"]


def test_scores_are_1_to_5_or_blank():
    assert L.valid_score("3") and L.valid_score("") and L.valid_score(None)
    assert not L.valid_score("6") and not L.valid_score("0")


def test_three_messages_each_carry_the_link_and_the_right_counts():
    comment = {"en": "E", "ar": "A", "planned": 4, "visited": 3}
    msgs = L.build_messages("Ali", comment, this_week_count=5, link="https://x/y")
    assert len(msgs) == 3 and all(m.endswith("https://x/y") for m in msgs)
    assert "3 of 4" in msgs[0] and "5 sites" in msgs[1] and "1 إلى 5" in msgs[2]
