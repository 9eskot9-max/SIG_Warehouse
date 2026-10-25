import sys
import unittest
from datetime import date
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from sig_warehouse.sig_warehouse import continuity as ct
from sig_warehouse.sig_warehouse import field_planner as fp

WEEK = date(2026, 10, 25)
P = dict(fp.DEFAULTS)
RIYADH, NEAR, JEDDAH, DAMMAM = (24.70, 46.70), (24.80, 46.75), (21.50, 39.20), (26.40, 50.10)


def trip(site, coords, win=None, value=1000.0, work_sites=1, must=False):
    lo, hi = win if win else (None, None)
    stops = [{"site": site, "cycle": site + "|NA", "tier": "T1", "reason": "x", "project": "P", "window": "",
              "win_start": lo, "win_end": hi, "value": value, "must": must, "has_mir": True, "order": i + 1,
              "leg_km": 0, "kind": "Proposed"} for i in range(work_sites)]
    return {"id": "C-" + site, "kind": "Proposed", "anchor": lo, "diameter_km": 0, "hours": 2, "team_days": 1,
            "best_tier": "T1", "stops": stops, "loaded": True, "status": ""}


class WalkTests(unittest.TestCase):
    def model(self, site, coords, work_h, win=None):
        t = ct._trip_model(trip(site, coords, work_sites=1), 0, coords, WEEK, 5, P)
        t["work"] = work_h
        if win:
            t["win"] = win
        return t

    def test_work_past_eleven_hours_continues_next_morning(self):
        coords = {"R1": RIYADH}
        res = ct._walk([self.model("R1", coords, 13)], 5, P)
        self.assertEqual([(0, 1)], res[3])

    def test_team_waits_for_a_window_that_opens_later(self):
        coords = {"R1": RIYADH}
        res = ct._walk([self.model("R1", coords, 2, win=(2, 3))], 5, P)
        self.assertEqual(2, res[3][0][0])

    def test_a_trip_must_start_inside_its_window_but_may_run_past_it(self):
        coords = {"R1": RIYADH, "J1": JEDDAH}
        # a long job may run past its window if it starts inside it
        self.assertIsNotNone(ct._walk([self.model("R1", coords, 30, win=(0, 0))], 5, P))
        # arriving after the window closed (a long drive from Riyadh to Jeddah) is infeasible
        first = self.model("R1", coords, 2)
        late = self.model("J1", coords, 2, win=(0, 0))
        self.assertIsNone(ct._walk([first, late], 5, P))

    def test_travel_between_trips_is_counted_and_matches_distance(self):
        coords = {"R1": RIYADH, "J1": JEDDAH}
        res = ct._walk([self.model("R1", coords, 2), self.model("J1", coords, 2)], 5, P)
        expect = fp.haversine_km(RIYADH, JEDDAH) * P["circuity"]
        self.assertAlmostEqual(expect, res[2], places=3)
        self.assertGreater(res[0], 0)


class ScheduleTests(unittest.TestCase):
    def test_windowed_trips_are_placed_inside_their_window(self):
        coords = {"R1": RIYADH, "R2": NEAR, "J1": JEDDAH}
        plan = {"clusters": [trip("R1", coords, (date(2026, 10, 26), date(2026, 10, 27))),
                             trip("J1", coords, (date(2026, 10, 28), date(2026, 10, 29)))],
                "later": [], "unplaced": [], "summary": {}, "params": P}
        res = ct.schedule_continuity(plan, coords, WEEK, {"teams": 1})
        by = {c["stops"][0]["site"]: c for c in res["clusters"] if c["status"] == "Scheduled"}
        self.assertEqual(date(2026, 10, 26), by["R1"]["days"][0] if by["R1"]["days"][0] <= date(2026, 10, 27) else None)
        self.assertGreaterEqual(by["J1"]["days"][0], date(2026, 10, 28))
        self.assertEqual(2, res["summary"]["windows_met"])

    def test_an_unreachable_window_lapses_with_the_reason(self):
        coords = {"R1": RIYADH, "R2": NEAR, "R3": RIYADH}
        windows = (date(2026, 10, 25), date(2026, 10, 25))
        plan = {"clusters": [trip("R1", coords, windows, work_sites=4), trip("R2", coords, windows, work_sites=4),
                             trip("R3", coords, windows, work_sites=4)],
                "later": [], "unplaced": [], "summary": {}, "params": P}
        res = ct.schedule_continuity(plan, coords, WEEK, {"teams": 1})
        lapsed = [c for c in res["clusters"] if c["status"] == "Lapsed"]
        self.assertTrue(lapsed)
        self.assertIn("TCN window", lapsed[0]["lapse_reason"])

    def test_same_input_gives_the_same_plan(self):
        coords = {"R1": RIYADH, "R2": NEAR, "J1": JEDDAH, "D1": DAMMAM}
        plan = {"clusters": [trip(s, coords, value=v) for s, v in (("R1", 500), ("R2", 900), ("J1", 300), ("D1", 800))],
                "later": [], "unplaced": [], "summary": {}, "params": P}
        a = ct.schedule_continuity(plan, coords, WEEK, {"teams": 2})
        b = ct.schedule_continuity(plan, coords, WEEK, {"teams": 2})
        self.assertEqual([(c["id"], c["status"], c.get("team")) for c in a["clusters"]],
                         [(c["id"], c["status"], c.get("team")) for c in b["clusters"]])


if __name__ == "__main__":
    unittest.main()
