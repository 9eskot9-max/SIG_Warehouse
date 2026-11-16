import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class StageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe.throw = lambda text: (_ for _ in ()).throw(ValueError(text))
        self.frappe.db = types.SimpleNamespace(exists=lambda *args: True,
            get_value=lambda *args: "unexpected", set_value=lambda *args: self.fail("unexpected write"))
        self.patch = patch.dict(sys.modules, {"frappe": self.frappe})
        self.patch.start()
        path = Path(__file__).resolve().parents[1] / "sig_warehouse/patches/v1_0/update_cycle_stage_rule.py"
        spec = importlib.util.spec_from_file_location("stage_migration_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)


    def tearDown(self):
        self.patch.stop()

    def test_unknown_writer_fails_before_write(self):
        with self.assertRaisesRegex(ValueError, "not recognized"):
            self.module.execute()

    def test_repeat_does_not_write(self):
        source = "    if sig_tcn and sig_mir and sig_visits >= 1 and sig_visit:\n"
        self.frappe.db.get_value = lambda *args: source
        with patch.object(self.module, "rewrite", return_value=source), patch.object(self.module, "fill_estimated_visit_dates"):
            self.module.execute()


    def test_missing_estimated_checkpoints_use_only_linked_visit_dates(self):
        candidates = [types.SimpleNamespace(name="C-1", last_visit_at=None),
                      types.SimpleNamespace(name="C-2", last_visit_at=None)]
        writes = []

        def get_all(doctype, **kwargs):
            if doctype == "SIG Site Cycle":
                return candidates
            return ["2026-11-01 12:00:00"] if kwargs["filters"]["cycle"] == "C-1" else []

        self.frappe.get_all = get_all
        self.frappe.db.set_value = lambda *args, **kwargs: writes.append(args)
        self.module.fill_estimated_visit_dates()
        self.assertEqual([("SIG Site Cycle", "C-1", {"first_visit_at": "2026-11-01 12:00:00",
                                                     "last_visit_at": "2026-11-01 12:00:00"})], writes)


if __name__ == "__main__":
    unittest.main()
