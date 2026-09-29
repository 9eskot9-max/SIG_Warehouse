"""Pure-logic tests for disposition.stamp_return_links (no Frappe needed): run with
    python -m unittest sig_warehouse.tests.test_return_links
from the SIG_Warehouse repo root. `frappe` is stubbed with an in-memory store."""
import sys
import types
import unittest


class FakeDb:
    def __init__(self):
        self.se = {}
        self.sed = {}
        self.writes = []

    def get_value(self, doctype, name, fields, as_dict=False):
        row = self.se[name] if doctype == "Stock Entry" else self.sed[name]
        if isinstance(fields, str):
            return row.get(fields)
        row = dict(row, name=name)
        return types.SimpleNamespace(**{f: row.get(f) for f in fields})

    def set_value(self, doctype, name, values, update_modified=True):
        assert update_modified is False
        (self.se if doctype == "Stock Entry" else self.sed)[name].update(values)
        self.writes.append((doctype, name, dict(values)))


DB = FakeDb()


def _get_all(doctype, filters=None, fields=None):
    assert doctype == "Stock Entry Detail"
    if "parent" in filters:
        rows = [dict(r, name=n) for n, r in DB.sed.items() if r.get("parent") == filters["parent"]]
    else:
        wanted = filters["name"][1]
        rows = [dict(DB.sed[n], name=n) for n in wanted if n in DB.sed]
    return [types.SimpleNamespace(**{f: r.get(f) for f in fields}) for r in rows]


def _stub():
    frappe = types.ModuleType("frappe")
    frappe.whitelist = lambda *a, **k: (lambda f: f)
    frappe.db = DB
    frappe.get_all = _get_all
    frappe.clear_document_cache = lambda *a, **k: None
    sys.modules["frappe"] = frappe


_stub()
from sig_warehouse.sig_warehouse import disposition as d  # noqa: E402


def _reset():
    DB.writes.clear()
    DB.se.clear()
    DB.sed.clear()
    DB.se["SRC"] = {"custom_site": "ZBR085"}
    DB.sed["S1"] = {"parent": "SRC", "material_request": "MR-1", "custom_site": "ZBR085"}
    DB.sed["S2"] = {"parent": "SRC", "material_request": "MR-1", "custom_site": None}
    DB.se["RET"] = {"docstatus": 1, "is_return": 1, "custom_return_against_se": "SRC", "custom_site": None}
    DB.sed["R1"] = {"parent": "RET", "material_request": None, "custom_site": None, "custom_original_se_detail": "S1"}
    DB.sed["R2"] = {"parent": "RET", "material_request": None, "custom_site": None, "custom_original_se_detail": "S2"}


class StampReturnLinks(unittest.TestCase):
    def setUp(self):
        _reset()

    def test_dry_run_reports_without_writing(self):
        changes = d.stamp_return_links("RET", apply=False)
        self.assertEqual(len(changes), 3)  # header site + two rows
        self.assertEqual(DB.writes, [])

    def test_apply_fills_mr_and_site_but_never_the_item_link(self):
        d.stamp_return_links("RET")
        self.assertEqual(DB.se["RET"]["custom_site"], "ZBR085")
        for row in ("R1", "R2"):
            self.assertEqual(DB.sed[row]["material_request"], "MR-1")
            self.assertEqual(DB.sed[row]["custom_site"], "ZBR085")  # R2 falls back to the source header site
            self.assertNotIn("material_request_item", DB.sed[row])

    def test_never_overwrites_and_is_idempotent(self):
        DB.sed["R1"]["material_request"] = "MR-OTHER"
        DB.sed["R1"]["custom_site"] = "KEEP"
        d.stamp_return_links("RET")
        self.assertEqual(DB.sed["R1"]["material_request"], "MR-OTHER")
        self.assertEqual(DB.sed["R1"]["custom_site"], "KEEP")
        DB.writes.clear()
        self.assertEqual(d.stamp_return_links("RET"), [])
        self.assertEqual(DB.writes, [])

    def test_ignores_entries_that_are_not_submitted_declared_returns(self):
        for patch in ({"docstatus": 0}, {"is_return": 0}, {"custom_return_against_se": None}):
            _reset()
            DB.se["RET"].update(patch)
            self.assertEqual(d.stamp_return_links("RET"), [])
            self.assertEqual(DB.writes, [])


if __name__ == "__main__":
    unittest.main()
