import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

APP = Path(__file__).resolve().parents[1]


def load(existing):
    log = {"inserted": [], "set": [], "cleared": []}
    frappe = ModuleType("frappe")

    def throw(message):
        raise RuntimeError(message)

    class Doc:
        def __init__(self, data):
            self.data = data

        def insert(self, ignore_permissions=False):
            log["inserted"].append(self.data)

    frappe.throw = throw
    frappe.get_all = lambda doctype, **kw: list(existing)
    frappe.get_doc = lambda data: Doc(data)
    frappe.clear_cache = lambda doctype=None: log["cleared"].append(doctype)
    frappe.db = ModuleType("db")
    frappe.db.set_value = lambda *a, **kw: log["set"].append(a)
    sys.modules["frappe"] = frappe
    spec = importlib.util.spec_from_file_location("grant_under_test",
                                                  APP / "sig_warehouse" / "patches" / "v1_0" / "grant_projects_user_site_read.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, log


BASELINE = [{"name": "a", "role": "System Manager", "permlevel": 0}, {"name": "b", "role": "SIG Field Ops", "permlevel": 0}]


class GrantProjectsUserSiteReadTests(unittest.TestCase):
    def test_adds_one_read_only_row_and_nothing_else(self):
        module, log = load(BASELINE)
        module.execute()
        self.assertEqual(1, len(log["inserted"]))
        row = log["inserted"][0]
        self.assertEqual(("SIG Site", "Projects User"), (row["parent"], row["role"]))
        granted = [p for p in module.PTYPES if row[p]]
        self.assertEqual(["read"], granted)
        self.assertEqual([], log["set"])

    def test_rerun_updates_the_existing_row_instead_of_duplicating(self):
        module, log = load(BASELINE + [{"name": "c", "role": "Projects User", "permlevel": 0}])
        module.execute()
        self.assertEqual([], log["inserted"])
        self.assertEqual([("Custom DocPerm", "c", "read", 1)], [a for a in log["set"]])

    def test_refuses_when_there_are_no_custom_rows_to_avoid_shadowing_standard_permissions(self):
        module, log = load([])
        with self.assertRaises(RuntimeError):
            module.execute()
        self.assertEqual([], log["inserted"])


if __name__ == "__main__":
    unittest.main()
