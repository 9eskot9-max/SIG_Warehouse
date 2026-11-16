import copy
import unittest

from sig_warehouse.sig_warehouse.cycle_shadow import compare_cycles


class CycleShadowTests(unittest.TestCase):
    def test_out_of_order_event_is_reported_without_mutation(self):
        cycles = [{"name": "C1", "last_event_at": "2026-11-01 10:00:00"}]
        events = [{"cycle": "C1", "occurred_at": "2026-11-03 10:00:00"},
                  {"cycle": "C1", "occurred_at": "2026-11-02 10:00:00"}]
        before = copy.deepcopy((cycles, events))
        result = compare_cycles(cycles, events, [], events_complete=True)
        self.assertEqual("2026-11-03 10:00:00", result[0]["observed"])
        self.assertEqual(before, (cycles, events))

    def test_incomplete_or_invalid_history_never_claims_a_mismatch(self):
        cycles = [{"name": "C1", "last_event_at": "2026-11-01 10:00:00"}]
        events = [{"cycle": "C1", "occurred_at": "2026-11-03 10:00:00"},
                  {"cycle": "C1", "occurred_at": "invalid"}]
        self.assertEqual([], compare_cycles(cycles, events[:1], []))
        self.assertEqual([], compare_cycles(cycles, events, [], events_complete=True))

    def test_visit_counts_include_estimates_separately_and_ignore_other_cycles(self):
        cycles = [{"name": "C1", "sessions_completed": 0, "sessions_auto_closed": 1}]
        visits = [{"cycle": "C1", "status": "COMPLETED"},
                  {"cycle": "C1", "status": "AUTO_CLOSED"},
                  {"cycle": "C2", "status": "COMPLETED"},
                  {"cycle": None, "status": "COMPLETED"}]
        self.assertEqual([], compare_cycles(cycles, [], visits))
        result = compare_cycles(cycles, [], visits, visits_complete=True)
        self.assertEqual([("sessions_completed", 0, 1)],
                         [(x["check"], x["stored"], x["observed"]) for x in result])

    def test_mixed_timezone_awareness_is_not_compared(self):
        cycles = [{"name": "C1", "last_event_at": "2026-11-01 10:00:00"}]
        events = [{"cycle": "C1", "occurred_at": "2026-11-03T10:00:00Z"}]
        self.assertEqual([], compare_cycles(cycles, events, [], events_complete=True))

    def test_missing_or_unknown_visit_status_suppresses_count_comparison(self):
        cycles = [{"name": "C1", "sessions_completed": 1}]
        self.assertEqual([], compare_cycles(cycles, [], [{"cycle": "C1"}], visits_complete=True))

    def test_missing_cycle_name_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_cycles([{}], [], [])


if __name__ == "__main__":
    unittest.main()
