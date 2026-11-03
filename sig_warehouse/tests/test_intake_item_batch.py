"""Batch creation behavior without a running Frappe site."""
import ast
import hashlib
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


source = Path(__file__).resolve().parents[1] / "sig_warehouse" / "warehouse_intake.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_items_from_rows")
function.decorator_list = []


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.rows = [SimpleNamespace(name="row1", idx=1, description="Cable 4 mm", uom="Meter", item_code=None),
                     SimpleNamespace(name="row2", idx=2, description="Cable 6 mm", uom="Meter", item_code=None)]
        self.intake = SimpleNamespace(name="WINT-1", docstatus=0, purchase_receipt=None,
            purchase_order_created=None, item_creation_group="Materials", lines=self.rows, save=lambda: None)
        def exists(doctype, query):
            if doctype == "Item Group": return True
            if doctype == "UOM": return query == "Meter"
            return False
        def get_doc(doctype, name=None, **kwargs):
            if isinstance(doctype, dict):
                item = SimpleNamespace(name=doctype["item_code"], item_name=doctype["item_name"])
                item.insert = lambda: self.created.append(item.name)
                return item
            return self.intake
        def throw(message, *args): raise ValueError(message)
        frappe = SimpleNamespace(get_doc=get_doc, db=SimpleNamespace(exists=exists), throw=throw)
        env = {"frappe": frappe, "_": lambda value: value, "_require_doc_permission": lambda *args: None,
               "re": re, "hashlib": hashlib}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(source), "exec"), env)
        self.create = env["create_items_from_rows"]

    def test_creates_and_links_each_row_once(self):
        self.assertEqual(self.create("WINT-1"), {"created": 2})
        self.assertEqual(len(set(self.created)), 2)
        self.assertEqual([row.item_code for row in self.rows], self.created)
        with self.assertRaises(ValueError): self.create("WINT-1")
        self.assertEqual(len(self.created), 2)

    def test_missing_unit_aborts_before_any_item_is_created(self):
        self.rows[1].uom = None
        with self.assertRaises(ValueError): self.create("WINT-1")
        self.assertEqual(self.created, [])


if __name__ == "__main__":
    unittest.main()
