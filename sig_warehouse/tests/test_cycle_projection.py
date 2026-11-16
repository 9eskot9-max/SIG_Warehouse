import unittest

from sig_warehouse.sig_warehouse.cycle_projection import project_evidence_stage


class EvidenceProjectionTests(unittest.TestCase):
    def test_normal_preparation_moves_to_handover_without_tags(self):
        result = project_evidence_stage(["TCN_GENERATED", "MIR_CONFIRMED", "FIELD_VISIT_COMPLETED"],
                                        history_complete=True)
        self.assertEqual("3 - Handover", result["stage"])
        self.assertEqual([], result["missing_preparation"])

    def test_downstream_evidence_survives_missing_mir_and_reports_gap(self):
        result = project_evidence_stage(["FIELD_VISIT_COMPLETED", "GCL_GENERATED"], history_complete=True)
        self.assertEqual("4 - Invoicing", result["stage"])
        self.assertEqual(["MIR_CONFIRMED", "TCN_GENERATED"], result["missing_preparation"])

    def test_partial_history_does_not_call_absence_a_fact(self):
        result = project_evidence_stage(["PHOTOS_FINALIZED"])
        self.assertEqual("3 - Handover", result["stage"])
        self.assertIsNone(result["missing_preparation"])

    def test_stage_is_order_and_duplicate_independent(self):
        codes = ["TCN_GENERATED", "MIR_CONFIRMED", "FIELD_VISIT_COMPLETED"]
        self.assertEqual(project_evidence_stage(codes), project_evidence_stage(codes[::-1] + codes))

    def test_a_single_visit_is_plan_not_an_invented_handover(self):
        self.assertEqual("2 - Plan", project_evidence_stage(["FIELD_VISIT_COMPLETED"])["stage"])


if __name__ == "__main__":
    unittest.main()
