import sys
import unittest
from datetime import date, datetime
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

    def test_every_separate_tcn_date_is_retained(self):
        windows = fp.tcn_windows([event("C", "2026-10-26", occurred="2026-10-27"),
                                  event("C", "2026-10-26", occurred="2026-10-29")])
        self.assertEqual([date(2026, 10, 27), date(2026, 10, 29)], windows["C"]["dates"])
        self.assertTrue(fp.window_covers(windows["C"], date(2026, 10, 27)))
        self.assertTrue(fp.window_covers(windows["C"], date(2026, 10, 29)))
        self.assertFalse(fp.window_covers(windows["C"], date(2026, 10, 28)))


class ErpCandidateTests(unittest.TestCase):
    def test_stage_two_and_tags_outstanding_stage_three_stay_in_pool_after_a_visit(self):
        now = datetime(2026, 10, 26, 13, 59)
        days = [date(2026, 10, 27), date(2026, 10, 28)]
        stage_two = cycle(name="C2", stage="2 - Plan", tcn_at=None, mir_at=None, impl_visits=1)
        stage_three = cycle(name="C3", stage="3 - Handover", tcn_at=None, mir_at=None, impl_visits=1)
        self.assertEqual("T5", fp.erp_candidate(stage_two, None, schedule_dates=days, now=now)[0])
        self.assertEqual("T2", fp.erp_candidate(stage_three, None, schedule_dates=days, now=now)[0])
        tags_done = dict(stage_three, tags_at="2026-10-25 08:00:00")
        self.assertIsNone(fp.erp_candidate(tags_done, None, schedule_dates=days, now=now)[0])

    def test_exact_two_pm_cutoff_removes_tomorrow_but_keeps_later_workday(self):
        dates = [date(2026, 10, 27), date(2026, 10, 28)]
        c = cycle(name="C", tcn_at=None, mir_at=None)
        before = fp.erp_candidate(c, None, schedule_dates=dates, now=datetime(2026, 10, 26, 13, 59))
        after = fp.erp_candidate(c, None, schedule_dates=dates, now=datetime(2026, 10, 26, 14, 0))
        self.assertEqual(dates, before[2])
        self.assertEqual([date(2026, 10, 28)], after[2])
        self.assertEqual([date(2026, 10, 28)], after[3])

    def test_a_dated_tcn_fixes_eligibility_to_its_evidenced_dates(self):
        dates = [date(2026, 10, 27), date(2026, 10, 28)]
        window = {"start": dates[0], "end": dates[0], "runs": [{"start": dates[0], "end": dates[0]}]}
        result = fp.erp_candidate(cycle(tcn_at="2026-10-26"), window, schedule_dates=dates,
                                  now=datetime(2026, 10, 26, 13, 59))
        self.assertEqual([dates[0]], result[2])
        self.assertEqual([], result[3])


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
        # a visit without HO documents is held for 30 days, so an old visit is what sends the cycle back to T2
        tier, reason = fp.classify(cycle(first_visit_at="2026-09-01 09:00:00", impl_visits=1),
                                   self.window("2026-09-01", "2026-09-03"), [date(2026, 9, 1)], TODAY, PARAMS)
        self.assertEqual("T2", tier)          # visited 24 days ago, MIR+TCN present, Tags missing
        self.assertIn("Tags", reason)

    def test_a_recent_visit_without_ho_docs_is_held_for_thirty_days(self):
        tier, reason = fp.classify(cycle(first_visit_at="2026-10-11 09:00:00", impl_visits=1, tcn_at="2026-10-01 10:00:00"),
                                   None, [date(2026, 10, 11)], TODAY, PARAMS)
        self.assertIsNone(tier)
        self.assertIn("Held", reason)

    def test_a_new_tcn_after_the_visit_overrides_the_hold(self):
        tier, _ = fp.classify(cycle(first_visit_at="2026-10-11 09:00:00", impl_visits=1, tcn_at="2026-10-20 10:00:00"),
                              self.window("2026-10-26", "2026-10-27"), [date(2026, 10, 11)], TODAY, PARAMS)
        self.assertEqual("T0", tier)

    def test_handover_documents_end_the_hold_at_once(self):
        tier, reason = fp.classify(cycle(first_visit_at="2026-10-11 09:00:00", impl_visits=1, ho_at="2026-10-20 10:00:00",
                                         stage="4 - Invoicing"), None, [date(2026, 10, 11)], TODAY, PARAMS)
        self.assertIsNone(tier)
        self.assertNotIn("Held", reason)

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


class IncidentAndScheduleTests(unittest.TestCase):
    def test_incident_cycles_are_found_through_the_erp_project_not_a_hardcoded_po(self):
        projects = [{"name": "WO-2026-0036", "project_name": "10001134 Incident & Crisis Management - ES 2026",
                     "custom_project_family": "Incident", "custom_family": "Incident", "custom_agreement_no": "10001134"},
                    {"name": "WO-2026-0037", "project_name": "10001274 Capex Replacement Project 2026",
                     "custom_project_family": "Capex", "custom_family": "Capex", "custom_agreement_no": "10001274"},
                    {"name": "WO-2026-0009", "project_name": "1000268 B2S- (Quality & Crises)-SIG",
                     "custom_project_family": "Incident", "custom_family": "Incident", "custom_agreement_no": "1000268"}]
        index = fp.index_projects(projects)
        for row in (dict(project="10001134", po=""), dict(project="Capex9", po="10001134"), dict(project="x", po="1000268"),
                    dict(project="incident", po=""), dict(project="y", po="", erp_project="WO-2026-0036")):
            row["project_text"] = fp.project_text(row, index)
            tier, reason = fp.classify(cycle(**row), None, [], TODAY, PARAMS)
            self.assertIsNone(tier, row)
            self.assertIn("Incident", reason)
        capex = dict(project="Capex9", po="10001274")
        capex["project_text"] = fp.project_text(capex, index)
        self.assertEqual("T3", fp.classify(cycle(tcn_at=None, **capex), None, [], TODAY, PARAMS)[0])

    def test_schedule_pins_committed_trips_to_their_day_and_fills_free_team_days(self):
        coords = {"R1": RIYADH, "R2": NEAR_RIYADH, "J1": JEDDAH, "D1": DAMMAM}
        items = [item("R1", "T0", date(2026, 10, 27)), item("J1", "T1"), item("D1", "T1")]
        plan = fp.plan_week(items, coords, WEEK, {"teams": 2})
        placed = {p["trip"]: p for p in fp.schedule_week(plan, WEEK, teams=2)}
        committed = next(c["id"] for c in plan["clusters"] if c["kind"] == "Committed")
        self.assertEqual(date(2026, 10, 27), placed[committed]["start"])
        self.assertTrue(all(p["status"] == "Scheduled" and p["team"] in (1, 2) for p in placed.values()))
        slots = [(p["team"], d) for p in placed.values() for d in p["days"]]
        self.assertEqual(len(slots), len(set(slots)), "no team is double booked")

    def test_schedule_marks_trips_that_do_not_fit_the_week(self):
        coords = {"R1": RIYADH, "J1": JEDDAH, "D1": DAMMAM}
        items = [item("R1", "T1"), item("J1", "T1"), item("D1", "T1")]
        plan = fp.plan_week(items, coords, WEEK, {"teams": 1, "work_days": 5, "load_target": 5})
        placed = fp.schedule_week(plan, WEEK, teams=1, work_days=2)
        self.assertEqual(2, sum(1 for p in placed if p["status"] == "Scheduled"))
        self.assertEqual(1, sum(1 for p in placed if p["status"] == "No free slot"))


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

    def test_a_window_that_just_ended_is_due_on_the_first_day_of_the_week(self):
        result = self.plan([item("R1", "T0", date(2026, 10, 24))])
        trip = result["clusters"][0]
        self.assertEqual(("Committed", date(2026, 10, 25)), (trip["kind"], trip["anchor"]))
        self.assertEqual(0, len(result["later"]))

    def test_two_cycles_at_one_site_remain_separate_work_items(self):
        a, b = item("R1", "T1"), item("R1", "T1")
        a["cycle"], b["cycle"] = "R1|WO-1", "R1|WO-2"
        result = self.plan([a, b, item("R2", "T1")])
        stops = [s for c in result["clusters"] for s in c["stops"]]
        self.assertEqual(3, len(stops))
        r1 = [s for s in stops if s["site"] == "R1"]
        self.assertEqual({"R1|WO-1", "R1|WO-2"}, {s["cycle"] for s in r1})

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


class ChooseWeekTests(unittest.TestCase):
    def cand(self, site, tier, start=None, end=None, value=1000.0, must=False, has_mir=True):
        return {"site": site, "cycle": site + "|NA", "tier": tier, "anchor": start, "age": "2026-10-01", "reason": "x",
                "project": "P", "window": "", "win_start": start, "win_end": end, "value": value, "must": must,
                "has_mir": has_mir}

    def statuses(self, result):
        return {c["stops"][0]["site"]: c["status"] for c in result["clusters"]}

    def test_a_must_site_beats_a_richer_normal_site_when_there_is_one_team_day(self):
        items = [self.cand("R1", "T1", value=9000, has_mir=False), self.cand("J1", "T1", value=10, must=True)]
        result = fp.choose_week(items, {"R1": RIYADH, "J1": JEDDAH}, WEEK, {"teams": 1, "work_days": 1})
        self.assertEqual({"J1": "Scheduled", "R1": "Lapsed"}, self.statuses(result))

    def test_value_per_team_day_orders_equal_priority_sites(self):
        items = [self.cand("R1", "T1", value=500), self.cand("J1", "T1", value=5000)]
        result = fp.choose_week(items, {"R1": RIYADH, "J1": JEDDAH}, WEEK, {"teams": 1, "work_days": 1})
        self.assertEqual({"J1": "Scheduled", "R1": "Lapsed"}, self.statuses(result))

    def test_no_extra_teams_are_invented_and_the_rest_lapse(self):
        items = [self.cand(s, "T0", date(2026, 10, 25), date(2026, 10, 25)) for s in ("R1", "J1", "D1")]
        result = fp.choose_week(items, {"R1": RIYADH, "J1": JEDDAH, "D1": DAMMAM}, WEEK, {"teams": 2, "work_days": 1})
        self.assertEqual(["Lapsed", "Scheduled", "Scheduled"], sorted(c["status"] for c in result["clusters"]))
        self.assertTrue(all(c["team"] in (1, 2) for c in result["clusters"] if c["status"] == "Scheduled"))
        self.assertEqual(1, result["summary"]["trips_lapsed"])

    def test_a_windowed_trip_takes_any_free_day_inside_its_window(self):
        items = [self.cand("R1", "T0", date(2026, 10, 26), date(2026, 10, 27)),
                 self.cand("J1", "T0", date(2026, 10, 26), date(2026, 10, 27))]
        result = fp.choose_week(items, {"R1": RIYADH, "J1": JEDDAH}, WEEK, {"teams": 1, "work_days": 3})
        days = sorted(c["days"][0] for c in result["clusters"] if c["status"] == "Scheduled")
        self.assertEqual([date(2026, 10, 26), date(2026, 10, 27)], days)

    def test_cycles_from_the_database_carry_datetimes_not_strings(self):
        from datetime import datetime as dtm
        cycle_row = {"name": "C-9", "site_id": "R1", "stage": "2 - Plan", "terminal": 0, "tcn_at": None,
                     "mir_at": dtm(2026, 10, 20, 9, 0), "first_visit_at": None, "impl_visits": 0, "tags_at": None,
                     "planned_start": None, "last_event_at": dtm(2026, 10, 21, 9, 30), "gross_value": 1000.0}
        rows, _ = fp.build_candidates([cycle_row], {}, {}, TODAY, PARAMS)
        self.assertEqual("2026-10-21", rows[0]["age"])

    def test_a_site_with_no_window_is_not_forced_onto_a_day(self):
        items = [self.cand("R1", "T1", value=100)]
        result = fp.choose_week(items, {"R1": RIYADH}, WEEK, {"teams": 1, "work_days": 3})
        self.assertEqual("Scheduled", result["clusters"][0]["status"])
        self.assertEqual(date(2026, 10, 25), result["clusters"][0]["days"][0])


class PMDecisionTests(unittest.TestCase):
    def entry(self, action, created="2026-10-20 09:00:00", until=None, reason=""):
        return {"action": action, "created": created, "until": until, "reason": reason}

    def test_hold_keeps_the_site_out_for_thirty_days_then_returns(self):
        dec = fp.active_decision([self.entry("Hold")], cycle(), None, TODAY, PARAMS)
        self.assertEqual("Hold", dec["action"])
        self.assertIsNone(fp.active_decision([self.entry("Hold", created="2026-09-01 09:00:00")], cycle(), None, TODAY, PARAMS))

    def test_a_tcn_after_a_hold_or_remove_cancels_it(self):
        c = cycle(tcn_at="2026-10-22 10:00:00")
        self.assertIsNone(fp.active_decision([self.entry("Hold")], c, None, TODAY, PARAMS))
        self.assertIsNone(fp.active_decision([self.entry("Remove")], c, None, TODAY, PARAMS))

    def test_remove_stays_until_a_blank_line_clears_it(self):
        self.assertEqual("Remove", fp.active_decision([self.entry("Remove")], cycle(), None, TODAY, PARAMS)["action"])
        self.assertIsNone(fp.active_decision([self.entry(""), self.entry("Remove")], cycle(), None, TODAY, PARAMS))

    def test_must_ends_after_fourteen_days_or_on_a_visit(self):
        self.assertEqual("Must", fp.active_decision([self.entry("Must")], cycle(), None, TODAY, PARAMS)["action"])
        self.assertIsNone(fp.active_decision([self.entry("Must", created="2026-10-01 09:00:00")], cycle(), None, TODAY, PARAMS))
        self.assertIsNone(fp.active_decision([self.entry("Must")], cycle(), date(2026, 10, 22), TODAY, PARAMS))

    def test_build_candidates_excludes_held_sites_and_marks_must(self):
        decisions = {"R1|NA": [self.entry("Hold", reason="no access")], "J1|NA": [self.entry("Must")]}
        cycles = [dict(cycle(), name="R1|NA", site_id="R1"), dict(cycle(), name="J1|NA", site_id="J1")]
        rows, excluded = fp.build_candidates(cycles, {}, {}, TODAY, PARAMS, None, "plan_hold", decisions)
        self.assertEqual(["J1"], [r["site"] for r in rows])
        self.assertTrue(rows[0]["must"])
        self.assertIn("PM Hold", excluded[0]["reason"])


if __name__ == "__main__":
    unittest.main()


class TeamPositionTests(unittest.TestCase):
    leaders = [{"leader": "E1", "team": "Waqas", "phone": "1"}, {"leader": "E2", "team": "Old", "phone": "2"},
               {"leader": "E3", "team": "New", "phone": "3"}]
    coords = {"AAA1": (24.7, 46.7), "BBB2": (21.5, 39.2)}

    def test_latest_check_in_or_out_sets_the_position(self):
        today = date(2026, 10, 26)
        visits = [{"employee": "E1", "site": "AAA1", "start_at": "2026-10-20 08:00:00", "end_at": "2026-10-20 10:00:00"},
                  {"employee": "E1", "site": "BBB2", "start_at": "2026-10-25 08:00:00", "end_at": None},
                  {"employee": "E2", "site": "AAA1", "start_at": "2026-09-01 08:00:00", "end_at": "2026-09-01 09:00:00"}]
        rows = {r["leader"]: r for r in fp.team_positions(self.leaders, visits, self.coords, today)}
        self.assertEqual(("BBB2", "Current", True, 1), (rows["E1"]["site"], rows["E1"]["state"], rows["E1"]["on_site"], rows["E1"]["age_days"]))
        self.assertEqual("Stale", rows["E2"]["state"])
        self.assertEqual("Unknown", rows["E3"]["state"])
        self.assertEqual(self.coords["BBB2"], (rows["E1"]["lat"], rows["E1"]["lon"]))
