import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from sig_warehouse.sig_warehouse.cycle_kpi import replay_cycles, summarize


class CycleKpiReplayTests(unittest.TestCase):
    def event(self, name, code, at, artifact_ref="", source_sub="field_feed", event_id=None):
        return {"name": name, "event_id": event_id or name, "cycle": "C-1", "event_code": code,
                "occurred_at": at, "recorded_at": at, "artifact_ref": artifact_ref, "source_sub": source_sub}

    def setUp(self):
        self.cycle = {"name": "C-1", "site_key": "ZJD134", "terminal": 1}

    def test_replays_real_stage_exits_and_qualifying_closure_once(self):
        events = [
            self.event("e1", "MAPPING_GENERATED", "2026-10-12 08:00:00"),
            self.event("e2", "PIMP_GENERATED", "2026-10-13 08:00:00"),
            self.event("e3", "TCN_GENERATED", "2026-10-14 08:00:00"),
            self.event("e4", "MIR_CONFIRMED", "2026-10-15 08:00:00"),
            self.event("e5", "FIELD_VISIT_COMPLETED", "2026-10-16 08:00:00"),
            self.event("e6", "TAGS_COLLECTED", "2026-10-17 08:00:00"),
            self.event("e7", "ASBUILT_BOQ_GENERATED", "2026-10-18 08:00:00"),
            self.event("e8", "GCL_GENERATED", "2026-10-19 08:00:00"),
            self.event("e9", "SITE_CLOSED", "2026-10-20 08:00:00", "close|PM confirms invoice submitted", "operations_workbench"),
            self.event("e9-retry", "SITE_CLOSED", "2026-10-20 08:00:00", "close|PM confirms invoice submitted", "operations_workbench", "e9"),
        ]
        result = replay_cycles([self.cycle], events, "2026-10-21 12:00:00")
        metric = result["cycles"]["C-1"]
        self.assertTrue(metric["completion_in_period"])
        self.assertEqual(["1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing"],
                         [row["stage"] for row in metric["stage_exits_in_period"]])
        self.assertEqual(8, metric["elapsed_days"])
        summary = summarize(result["cycles"])
        self.assertEqual(1, summary["completed_cycles"])
        self.assertEqual([1, 1, 1, 1], [summary["stages"][stage]["completed"] for stage in (
            "1 - Initial", "2 - Plan", "3 - Handover", "4 - Invoicing")])

    def test_does_not_invent_initial_entry_or_count_admin_close_as_completion(self):
        events = [
            self.event("e1", "TCN_GENERATED", "2026-10-12 08:00:00"),
            self.event("e2", "PHOTOS_FINALIZED", "2026-10-13 08:00:00"),
            self.event("e3", "SITE_CLOSED", "2026-10-20 08:00:00", "close|PM note: cancelled", "operations_workbench"),
        ]
        result = replay_cycles([self.cycle], events, "2026-10-21 12:00:00")
        metric = result["cycles"]["C-1"]
        self.assertFalse(metric["completion_in_period"])
        self.assertIsNone(metric["stage_timings"][0]["days"])
        self.assertFalse(any(item["stage"] == "4 - Invoicing" for item in metric["stage_exits_in_period"]))
        self.assertEqual(0, summarize(result["cycles"])["completed_cycles"])

    def test_business_closure_completes_only_the_stage_the_cycle_actually_left(self):
        events = [
            self.event("e1", "MAPPING_GENERATED", "2026-10-12 08:00:00"),
            self.event("e2", "PIMP_GENERATED", "2026-10-13 08:00:00"),
            self.event("e3", "SITE_CLOSED", "2026-10-20 08:00:00", "MANUAL_CLOSE|u|t|PM confirms invoice submitted", "operations_workbench"),
        ]
        metric = replay_cycles([self.cycle], events, "2026-10-21 12:00:00")["cycles"]["C-1"]
        self.assertEqual(["1 - Initial", "2 - Plan"], [x["stage"] for x in metric["stage_exits_in_period"]])
        self.assertTrue(metric["completion_in_period"])


if __name__ == "__main__":
    unittest.main()
