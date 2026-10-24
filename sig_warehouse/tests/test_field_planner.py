import sys
import unittest
from datetime import date
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from sig_warehouse.sig_warehouse import field_planner as fp

TODAY = date(2026, 10, 25)          # Sunday
WEEK = date(2026, 10, 25)
PARAMS = dict(fp.DEFAULTS)

# Riyadh area, Jeddah area, Dammam area (straight-line degrees only; distances are computed)
RIYADH = (24.70, 46.70)
NEAR_RIYADH = (24.80, 46.75)
JEDDAH = (21.50, 39.20)
DAMMAM = (26.40, 50.10)


def event(cycle, recorded, occurred=None):
    return {"cycle": cycle, "event_code": "TCN_GENERATED", "recorded_at": recorded + " 10:00:00",
            "occurred_at": (occurred or recorded) + " 10:00:00"}


def cycle(**kw):
    row = {"name": "C", "stage": "2 - Plan", "terminal": 0, "tcn_at": "2026-10-20 10:00:00",
           "mir_at": "2026-10-21 10:00:00", "first_visit_at": None, "impl_visits": 0, "tags_at": None,
           "planned_start": None, "last_event_at": "2026-10-21 10:00:00"}
    row.update(kw)
    return row


class TcnWindowTests(unittest.TestCase):
    def test_consecutive_exports_form_one_window_anchored_on_the_middle_day(self):
        windows = fp.tcn_windows([event("C", "2026-10-20"), event("C", "2026-10-21"), event("C", "2026-10-22")])
        self.assertEqual(date(2026, 10, 21), windows["C"]["anchor"])
        self.assertEqual((date(2026, 10, 20), date(2026, 10, 22)), (windows["C"]["start"], windows["C"]["end"]))
        self.assertEqual(3, windows["C"]["exports"])

    def test_two_day_window_anchors_on_the_first_day(self):
        windows = fp.tcn_windows([event("C", "2026-10-20"), event("C", "2026-10-21")])
        self.assertEqual(date(2026, 10, 20), windows["C"]["anchor"])

    def test_a_later_separate_export_starts_a_new_window_and_the_latest_is_used(self):
        windows = fp.tcn_windows([event("C", "2026-10-01"), event("C", "2026-10-02"), event("C", "2026-10-10")])
        self.assertEqual(date(2026, 10, 10), windows["C"]["anchor"])
        self.assertEqual(2, windows["C"]["windows"])

    def test_planned_start_is_used_when_it_is_after_the_export_time(self):
        windows = fp.tcn_windows([event("C", "2026-10-22", occurred="2026-10-26")])
        self.assertEqual(date(2026, 10, 26), windows["C"]["anchor"])


class ClassifyTests(unittest.TestCase):
    def window(self, start, end):
        return {"start": date.fromisoformat(start), "end": date.fromisoformat(end), "anchor": date.fromisoformat(start)}

    def test_open_window_is_committed(self):
        tier, _ = fp.classify(cycle(), self.window("2026-10-26", "2026-10-28"), [], TODAY, PARAMS)
        self.assertEqual("T0", tier)

    def test_window_passed_without_visit_is_overdue(self):
        tier, _ = fp.classify(cycle(), self.window("2026-10-10", "2026-10-12"), [], TODAY, PARAMS)
        self.assertEqual("T1", tier)

    def test_visit_inside_tolerance_clears_the_window(self):
        tier, reason = fp.classify(cycle(first_visit_at="2026-10-11 09:00:00", impl_visits=1),
                                   self.window("2026-10-10", "2026-10-12"), [date(2026, 10, 11)], TODAY, PARAMS)
        self.assertEqual("T2", tier)          # visited, MIR+TCN present, Tags missing
        self.assertIn("Tags", reason)

    def test_old_overdue_with_no_recent_evidence_is_parked_not_overdue(self):
        old = cycle(last_event_at="2026-07-01 10:00:00")
        tier, reason = fp.classify(old, self.window("2026-07-01", "2026-07-03"), [], TODAY, PARAMS)
        self.assertIsNone(tier)
        self.assertIn("Parked", reason)

    def test_mir_without_tcn_or_visit_is_ready_to_batch(self):
        tier, _ = fp.classify(cycle(tcn_at=None), None, [], TODAY, PARAMS)
        self.assertEqual("T3", tier)

    def test_tcn_without_mir_is_filler(self):
        tier, _ = fp.classify(cycle(mir_at=None), None, [], TODAY, PARAMS)
        self.assertEqual("T4", tier)

    def test_handover_without_tags_needs_field_work_and_with_tags_does_not(self):
        self.assertEqual("T2", fp.classify(cycle(stage="3 - Handover"), None, [], TODAY, PARAMS)[0])
        self.assertIsNone(fp.classify(cycle(stage="3 - Handover", tags_at="2026-10-22 10:00:00"), None, [], TODAY, PARAMS)[0])

    def test_office_stages_and_pm_marks_are_excluded(self):
        self.assertIsNone(fp.classify(cycle(stage="4 - Invoicing"), None, [], TODAY, PARAMS)[0])
        self.assertIsNone(fp.classify(cycle(stage="1 - Initial"), None, [], TODAY, PARAMS)[0])
        self.assertEqual("Held by PM", fp.classify(cycle(), None, [], TODAY, PARAMS, mark="Hold")[1])
        self.assertEqual("Marked visited by PM", fp.classify(cycle(), None, [], TODAY, PARAMS, mark="Visited")[1])


def item(site, tier, anchor=None, age="2026-10-01"):
    return {"site": site, "cycle": site + "|NA", "tier": tier, "anchor": anchor, "age": age,
            "reason": "x", "project": "P", "window": ""}


class PlanWeekTests(unittest.TestCase):
    def setUp(self):
        self.coords = {"R1": RIYADH, "R2": NEAR_RIYADH, "R3": (24.75, 46.60), "J1": JEDDAH, "D1": DAMMAM,
                       "R4": (24.65, 46.80)}

    def plan(self, items, **overrides):
        return fp.plan_week(items, self.coords, WEEK, overrides)

    def test_committed_sites_form_a_trip_and_nearby_ready_sites_fill_it(self):
        items = [item("R1", "T0", date(2026, 10, 26)), item("R2", "T3"), item("J1", "T3")]
        result = self.plan(items)
        committed = [c for c in result["clusters"] if c["kind"] == "Committed"]
        self.assertEqual(1, len(committed))
        self.assertEqual({"R1", "R2"}, {s["site"] for s in committed[0]["stops"]})
        self.assertEqual("Fill", next(s for s in committed[0]["stops"] if s["site"] == "R2")["kind"])

    def test_fill_does_not_cross_the_diameter_cap(self):
        result = self.plan([item("R1", "T0", date(2026, 10, 26)), item("J1", "T1")], diameter_km=150)
        self.assertEqual(["R1"], [s["site"] for c in result["clusters"] if c["kind"] == "Committed" for s in c["stops"]])

    def test_distant_must_do_site_becomes_a_lone_trip_but_a_filler_is_deferred(self):
        result = self.plan([item("J1", "T1"), item("D1", "T4")])
        kinds = {c["stops"][0]["site"]: c["kind"] for c in result["clusters"]}
        self.assertEqual("Lone trip", kinds["J1"])
        self.assertEqual("Deferred", kinds["D1"])

    def test_sites_without_coordinates_are_listed_not_dropped(self):
        result = self.plan([item("NOPE", "T1"), item("R1", "T1")])
        self.assertEqual(["NOPE"], [i["site"] for i in result["unplaced"]])
        self.assertEqual(1, result["summary"]["no_coordinates"])

    def test_capacity_loads_committed_first_then_higher_tiers_and_pushes_the_rest_to_backlog(self):
        items = [item("R1", "T0", date(2026, 10, 26)), item("J1", "T1"), item("D1", "T3")]
        result = self.plan(items, teams=1, work_days=3)       # capacity 2.55 team-days
        loaded = {c["stops"][0]["site"]: c["loaded"] for c in result["clusters"]}
        self.assertTrue(loaded["R1"])
        self.assertTrue(loaded["J1"])
        self.assertFalse(loaded["D1"])
        self.assertEqual(1, result["summary"]["backlog_trips"])

    def test_committed_trips_are_always_loaded_even_over_capacity(self):
        items = [item("R1", "T0", date(2026, 10, 26)), item("J1", "T0", date(2026, 10, 26)), item("D1", "T0", date(2026, 10, 26))]
        result = self.plan(items, teams=1, work_days=1)
        self.assertTrue(all(c["loaded"] for c in result["clusters"]))
        self.assertTrue(result["summary"]["over_capacity"])

    def test_committed_outside_the_week_is_reported_but_not_loaded(self):
        result = self.plan([item("R1", "T0", date(2026, 11, 3))])
        self.assertEqual(1, len(result["later"]))
        self.assertEqual([], result["clusters"])

    def test_workload_uses_scope_hours_and_travel_and_days_round_up(self):
        result = self.plan([item("R1", "T1"), item("R2", "T1"), item("R3", "T1"), item("R4", "T1")], scope_hours=2)
        trip = result["clusters"][0]
        self.assertEqual(4, len(trip["stops"]))
        self.assertGreaterEqual(trip["hours"], 8)
        self.assertEqual(1 if trip["hours"] <= 11 else 2, trip["team_days"])
        long_scope = self.plan([item("R1", "T1"), item("R2", "T1"), item("R3", "T1"), item("R4", "T1")], scope_hours=4)
        self.assertEqual(2, long_scope["clusters"][0]["team_days"])

    def test_same_input_gives_the_same_plan(self):
        items = [item("R1", "T1"), item("R2", "T3"), item("J1", "T2"), item("D1", "T4"), item("R3", "T1")]
        first = self.plan(items)
        second = self.plan(list(reversed(items)))
        self.assertEqual([[s["site"] for s in c["stops"]] for c in first["clusters"]],
                         [[s["site"] for s in c["stops"]] for c in second["clusters"]])

    def test_week_start_moves_to_next_sunday_from_friday(self):
        self.assertEqual(date(2026, 10, 25), fp.week_start_for(date(2026, 10, 23)))   # Friday
        self.assertEqual(date(2026, 10, 25), fp.week_start_for(date(2026, 10, 25)))   # Sunday
        self.assertEqual(date(2026, 10, 25), fp.week_start_for(date(2026, 10, 28)))   # Wednesday


if __name__ == "__main__":
    unittest.main()
