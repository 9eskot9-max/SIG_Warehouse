"""Batch creation behavior without a running Frappe site."""
import ast
import json
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
        self.rows = [SimpleNamespace(name="row1", idx=1, description="Cable 4 mm", item_name="Cable 4 mm", uom="Meter", item_code=None, item_family_key="E-CAB", proposed_item_code="E-CAB-4MM"),
                     SimpleNamespace(name="row2", idx=2, description="Cable 6 mm", item_name="Cable 6 mm", uom="Meter", item_code=None, item_family_key="E-CAB", proposed_item_code="E-CAB-6MM")]
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
        frappe = SimpleNamespace(get_doc=get_doc, get_single=lambda name: object(), db=SimpleNamespace(exists=exists), throw=throw)
        env = {"frappe": frappe, "_": lambda value: value, "_require_doc_permission": lambda *args: None,
               "_item_family_registry": lambda settings: [{"key": "E-CAB"}],
               "_proposal_basis": lambda description, uom: description + ':' + uom,
               "_family_for_code": lambda code, keys: next((key for key in sorted(keys, key=len, reverse=True)
                   if code.startswith(key + "-") or code.startswith("A-" + key + "-")), "")}
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

    def test_wrong_family_code_aborts_before_any_creation(self):
        self.rows[1].proposed_item_code = "SIG-CABLE-RANDOM"
        with self.assertRaises(ValueError): self.create("WINT-1")
        self.assertEqual(self.created, [])

    def test_duplicate_proposed_codes_abort_before_any_creation(self):
        self.rows[1].proposed_item_code = self.rows[0].proposed_item_code
        with self.assertRaises(ValueError): self.create("WINT-1")
        self.assertEqual(self.created, [])

    def test_changed_description_invalidates_proposal(self):
        self.rows[0].proposal_basis = 'previous description:Meter'
        with self.assertRaises(ValueError): self.create('WINT-1')
        self.assertEqual(self.created, [])


class FamilyTests(unittest.TestCase):
    def setUp(self):
        def throw(message, *args):
            raise ValueError(message)
        env = {"frappe": SimpleNamespace(throw=throw), "_": lambda value: value, "re": re,
               "Path": Path, "json": json, "__file__": str(source)}
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ("_item_family_registry", "_valid_family_code", "_family_for_code", "_item_search_tokens")]
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source), "exec"), env)
        self.registry = env["_item_family_registry"]
        self.valid = env["_valid_family_code"]
        self.family_for_code = env["_family_for_code"]
        self.tokens = env["_item_search_tokens"]

    def test_registry_allows_subfamilies_but_rejects_conflicting_keys(self):
        settings = SimpleNamespace(item_family_registry="Electrical|Power|Battery|BAT|E-BAT|Lithium\nElectrical|Power|Battery|BAT|E-BAT|Lead")
        self.assertEqual(len(self.registry(settings)), 2)
        settings.item_family_registry += "\nElectrical|Other|Cable|CAB|E-BAT|"
        with self.assertRaises(ValueError): self.registry(settings)

    def test_code_must_use_family_and_can_include_asset_prefix(self):
        self.assertTrue(self.valid("E-BAT-NR-200", "E-BAT"))
        self.assertTrue(self.valid("A-E-BAT-NR-200", "E-BAT"))
        self.assertFalse(self.valid("SIG-BATTERY-1234", "E-BAT"))
        self.assertFalse(self.valid("E-BAT--200", "E-BAT"))

    def test_family_is_inferred_from_entered_code(self):
        self.assertEqual(self.family_for_code("A-E-BAT-NR-200", {"E-BAT", "E-B"}), "E-BAT")
        self.assertEqual(self.family_for_code("E-BAT-NR-200", {"E-BAT"}), "E-BAT")
        self.assertEqual(self.family_for_code("OTHER-BAT-200", {"E-BAT"}), "")

    def test_bundled_registry_includes_documented_corrected_families(self):
        rows = self.registry(SimpleNamespace(item_family_registry=""))
        keys = {row["key"] for row in rows}
        self.assertTrue({"C-FND", "E-TPE", "E-TIE", "E-PRINT"}.issubset(keys))
        self.assertGreater(len(keys), 40)

    def test_candidate_search_uses_distinguishing_words(self):
        self.assertEqual(self.tokens('Cable for DC Panel 35mm'), {'cable', 'panel', '35mm'})


class SimilarItemsTests(unittest.TestCase):
    def test_finds_legacy_code_by_name_and_skips_linked_rows(self):
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('_item_search_tokens', 'similar_items_for_rows')]
        for node in functions:
            node.decorator_list = []
        item = SimpleNamespace(name='E-DC-CAB-35', item_name='DC Cable 35mm', stock_uom='Meter')
        intake = SimpleNamespace(lines=[SimpleNamespace(name='row1', description='DC cable 35mm', item_code=None),
                                        SimpleNamespace(name='row2', description='DC cable 35mm', item_code='EXISTING')])
        env = {'re': re, 'frappe': SimpleNamespace(get_list=lambda *args, **kwargs: [item]),
               '_intake_for_write': lambda name: intake, '_require_doc_permission': lambda *args: None}
        exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])), str(source), 'exec'), env)
        result = env['similar_items_for_rows']('WINT-1')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['items'][0]['name'], 'E-DC-CAB-35')


if __name__ == "__main__":
    unittest.main()
