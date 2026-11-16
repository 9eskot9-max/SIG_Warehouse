import unittest

from sig_warehouse.sig_warehouse.cycle_parking_manifest import validate_parking_manifest


class ParkingManifestTests(unittest.TestCase):
    def setUp(self):
        self.cycle = {"name": "C1", "terminal": 1, "modified": "2026-11-15 12:00:00",
                      "site_key": "SITE", "po": "PO"}
        self.item = {"name": "C1", "modified": self.cycle["modified"], "reviewed_open_cycles": []}

    def test_verified_single_record_is_eligible_for_review_not_a_write(self):
        self.assertEqual([], validate_parking_manifest([self.item], [self.cycle], expected_count=1))
        self.assertEqual(1, self.cycle["terminal"])

    def test_changed_missing_duplicate_and_wrong_count_are_rejected(self):
        result = validate_parking_manifest([self.item, self.item], [{**self.cycle, "modified": "later"}],
                                           expected_count=142)
        self.assertEqual({"UNEXPECTED_COUNT", "CYCLE_CHANGED_OR_VERSION_MISSING", "MISSING_OR_DUPLICATE_NAME"},
                         {issue["code"] for issue in result})
        self.assertEqual("CYCLE_MISSING", validate_parking_manifest([self.item], [], expected_count=1)[0]["code"])

    def test_new_successor_requires_explicit_review(self):
        successor = {"name": "C2", "terminal": 0, "site_key": "SITE", "po": "PO"}
        issues = validate_parking_manifest([self.item], [self.cycle, successor], expected_count=1)
        self.assertEqual("OPEN_SCOPE_REVIEW_NEEDED", issues[0]["code"])
        reviewed = {**self.item, "reviewed_open_cycles": ["C2"]}
        self.assertEqual([], validate_parking_manifest([reviewed], [self.cycle, successor], expected_count=1))

    def test_unknown_scope_is_not_treated_as_safe(self):
        issues = validate_parking_manifest([self.item], [{**self.cycle, "po": ""}], expected_count=1)
        self.assertEqual("SCOPE_INCOMPLETE", issues[0]["code"])


if __name__ == "__main__":
    unittest.main()
