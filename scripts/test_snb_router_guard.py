"""Focused controller checks runnable without a local Frappe bench."""
import importlib.util
import pathlib
import sys
import types
import unittest

root = pathlib.Path(__file__).resolve().parents[1]
frappe = types.ModuleType("frappe")
frappe.PermissionError = type("FrappePermissionError", (Exception,), {})
def throw(message, exc=ValueError):
    raise exc(message)
frappe.throw = throw
model = types.ModuleType("frappe.model")
document = types.ModuleType("frappe.model.document")
class Document:
    def get(self, key): return getattr(self, key, None)
document.Document = Document
sys.modules.update({"frappe": frappe, "frappe.model": model, "frappe.model.document": document})
spec = importlib.util.spec_from_file_location("snb_review_controller", root / "sig_warehouse/sig_accounting/doctype/snb_movement_review/snb_movement_review.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)

class ControllerGuardTest(unittest.TestCase):
    def make_doc(self, authorized, changed):
        doc = controller.SNBMovementReview()
        doc.flags = types.SimpleNamespace(snb_router_write=authorized)
        doc.is_new = lambda: False
        before = types.SimpleNamespace(get=lambda field: "original" if field == "source_json" else None)
        doc.get_doc_before_save = lambda: before
        doc.source_json = "changed" if changed else "original"
        return doc

    def test_direct_form_or_rest_write_is_denied(self):
        with self.assertRaises(frappe.PermissionError):
            self.make_doc(False, False).validate()

    def test_authorized_review_cannot_rewrite_bank_evidence(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.make_doc(True, True).validate()

    def test_authorized_review_can_keep_original_evidence(self):
        self.make_doc(True, False).validate()

if __name__ == "__main__": unittest.main()
