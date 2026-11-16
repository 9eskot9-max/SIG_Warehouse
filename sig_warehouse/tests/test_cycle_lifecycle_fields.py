import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class LifecycleFieldsTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.fake = types.ModuleType("frappe")
        self.fake.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
        self.fake.clear_cache = lambda **kwargs: None
        self.fake.db = types.SimpleNamespace(
            get_value=lambda dt, filters, field: (filters["dt"], filters["fieldname"]) if (filters["dt"], filters["fieldname"]) in self.rows else None,
            exists=lambda dt, filters: (filters["dt"], filters["fieldname"]) in self.rows)
        def get_doc(arg, name=None):
            if isinstance(arg, dict):
                return types.SimpleNamespace(insert=lambda **kw: self.rows.__setitem__((arg["dt"], arg["fieldname"]), arg))
            return types.SimpleNamespace(get=lambda key: self.rows[name].get(key))
        self.fake.get_doc = get_doc
        self.modules = patch.dict(sys.modules, {"frappe": self.fake})
        self.modules.start()
        path = Path(__file__).resolve().parents[1] / "sig_warehouse/patches/v1_0/add_cycle_lifecycle_fields.py"
        spec = importlib.util.spec_from_file_location("lifecycle_fields_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.modules.stop()

    def test_repeat_does_not_duplicate_fields(self):
        self.module.execute()
        self.module.execute()
        self.assertEqual(7, len(self.rows))

    def test_conflict_stops_before_any_insert(self):
        self.rows["SIG Site Cycle", "sig_parked_at"] = {"fieldtype": "Data"}
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.module.execute()
        self.assertEqual([("SIG Site Cycle", "sig_parked_at")], list(self.rows))


if __name__ == "__main__":
    unittest.main()
