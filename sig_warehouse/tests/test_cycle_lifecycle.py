import unittest
from datetime import datetime

from sig_warehouse.sig_warehouse.cycle_lifecycle import effective_lifecycle, parking_transition


class ParkedLifecycleTests(unittest.TestCase):
    def test_legacy_rows_resolve_without_a_data_migration(self):
        self.assertEqual("Closed", effective_lifecycle(None, 1))
        self.assertEqual("Open", effective_lifecycle(None, 0))
        self.assertEqual("Closed", effective_lifecycle("Parked", 1))

    def test_parking_preserves_closed_history_and_rejects_closed_or_missing_reason(self):
        cycle = {"terminal": 0, "closed_on": "2026-01-01"}
        result = parking_transition(cycle, actor="user", parked_at=datetime(2026, 11, 16), reason=" waiting ")
        self.assertEqual("waiting", result["sig_park_reason"])
        self.assertNotIn("closed_on", result)
        self.assertEqual("2026-01-01", cycle["closed_on"])
        with self.assertRaises(ValueError):
            parking_transition({"terminal": 1}, actor="user", parked_at=datetime(2026, 11, 16), reason="waiting")
        with self.assertRaises(ValueError):
            parking_transition(cycle, actor="user", parked_at=datetime(2026, 11, 16), reason=" ")
