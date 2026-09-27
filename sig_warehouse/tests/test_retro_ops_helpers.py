"""Pure-logic tests for retro_ops (no Frappe needed): run with
    python -m unittest sig_warehouse.tests.test_retro_ops_helpers
from the SIG_Warehouse repo root. `frappe` and `rollup` are stubbed."""
import sys
import types
import unittest


def _stub():
    """Only `frappe` is stubbed; the real rollup module imports cleanly against it (it only uses frappe inside functions)."""
    frappe = types.ModuleType("frappe")
    frappe.whitelist = lambda *a, **k: (lambda f: f)
    frappe.PermissionError = PermissionError
    frappe.session = types.SimpleNamespace(user="test@example.com")
    frappe.db = types.SimpleNamespace()
    sys.modules["frappe"] = frappe


_stub()
from sig_warehouse.sig_warehouse import retro_ops as r  # noqa: E402


class TestVoucherRules(unittest.TestCase):
    def test_parse_old_voucher(self):
        self.assertEqual(r.parse_old_voucher("DN26-1043"), 1043)
        for bad in ("DN26-1043X", "DN26-1043-1", "SIG-DN-DN26-1043", "DN26-43", "", None, "DN27-1043"):
            self.assertIsNone(r.parse_old_voucher(bad), bad)

    def test_rename_allowed(self):
        for n in (1035, 1043, 1048, 9901):
            ok, why = r.valid_rename("DN26-%04d" % n, "DN26-%04dX" % n)
            self.assertTrue(ok, (n, why))
        self.assertTrue(r.valid_rename("DN26-1035", "DN26-1035X2")[0])     # the shared test-era voucher

    def test_rename_refused(self):
        cases = [
            ("DN26-0519", "DN26-0519X", "OLD_VOUCHER_NOT_ELIGIBLE"),       # WH-era, must never be renamed
            ("DN26-1049", "DN26-1049X", "OLD_VOUCHER_NOT_ELIGIBLE"),       # beyond the ERP-era range
            ("DN26-1043X", "DN26-1043XX", "OLD_VOUCHER_NOT_ELIGIBLE"),     # already renamed
            ("DN26-1043", "DN26-1044X", "NEW_VOUCHER_FORMAT"),             # different number
            ("DN26-1043", "DN26-1043", "NEW_VOUCHER_FORMAT"),              # no X
            ("DN26-1043", "DN26-1043-1", "NEW_VOUCHER_FORMAT"),            # suffix is not X
            ("DN26-1043", "DN26-X1043", "NEW_VOUCHER_FORMAT"),             # X-namespace form is not a rename target
        ]
        for old, new, why in cases:
            ok, got = r.valid_rename(old, new)
            self.assertFalse(ok, (old, new))
            self.assertEqual(got, why, (old, new))


class TestGuards(unittest.TestCase):
    def test_retro_note(self):
        self.assertTrue(r.is_retro_note("Retrospective WH import"))
        self.assertTrue(r.is_retro_note("9A.13 G3 canary - throwaway"))
        self.assertFalse(r.is_retro_note("Tahir"))
        self.assertFalse(r.is_retro_note(""))
        self.assertFalse(r.is_retro_note(None))

    def test_dry_run_default(self):
        self.assertTrue(r._truthy_dry(1))
        self.assertTrue(r._truthy_dry("1"))
        self.assertTrue(r._truthy_dry(None))          # anything unclear stays a dry run
        self.assertFalse(r._truthy_dry(0))
        self.assertFalse(r._truthy_dry("0"))
        self.assertFalse(r._truthy_dry("false"))

    def test_reasons(self):
        self.assertEqual(set(r.REASONS), {"SMALL_VALUE_WAIVED", "DELTA_DISMISSED", "WH_CLOSED"})
        self.assertNotIn("OPERATOR_CANCEL", r.REASONS)   # a real cancel is never written by this module


class TestUomGroups(unittest.TestCase):
    def test_same_and_grouped_names_are_compatible(self):
        for a, b in (("Nos", "Pcs"), ("Pcs", "Nos"), ("Meter", "Mtr"), ("mtr", "METER"), ("Nos", "String"),
                     ("Unit", "Pcs"), ("Pcs", "Pcs"), ("Box", "Box")):
            self.assertTrue(r.uom_compatible(a, b), (a, b))

    def test_different_dimensions_are_not(self):
        for a, b in (("Box", "Pcs"), ("Set", "Nos"), ("Meter", "Pcs"), ("Roll", "Mtr"), ("Bucket", "Nos"),
                     ("", "Pcs"), (None, "Nos"), ("Ems(Pica)", "Nos")):
            self.assertFalse(r.uom_compatible(a, b), (a, b))


class TestApprovedClosureAllowList(unittest.TestCase):
    """2026-09-27: a second eligibility path for _load_mr - an explicit MIR allow-list, not a loosened
    marker check. Exercised at the pure-logic level with frappe.db.get_value stubbed."""
    def test_allow_list_loaded_and_nonempty(self):
        self.assertGreater(len(r.APPROVED_CLOSURE_MIRS), 0)
        self.assertIsInstance(next(iter(r.APPROVED_CLOSURE_MIRS)), int)

    def _mr_row(self, mir, confirmed_by):
        return {"name": "MR-TEST", "docstatus": 1, "material_request_type": "Material Issue",
                "custom_mir_number": str(mir), "custom_source_confirmed_by": confirmed_by}

    def test_native_mr_on_the_allow_list_is_accepted(self):
        mir = next(iter(r.APPROVED_CLOSURE_MIRS))
        r.frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: types.SimpleNamespace(**self._mr_row(mir, "A Real Person")))
        row, err = r._load_mr("MR-TEST", mir)
        self.assertIsNone(err, err)
        self.assertEqual(row.name, "MR-TEST")

    def test_native_mr_not_on_the_allow_list_is_still_refused(self):
        not_approved = max(r.APPROVED_CLOSURE_MIRS) + 1000
        r.frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: types.SimpleNamespace(**self._mr_row(not_approved, "A Real Person")))
        row, err = r._load_mr("MR-TEST", not_approved)
        self.assertIsNone(row)
        self.assertEqual(err["reason"], "MR_NOT_MARKED_RETROSPECTIVE_AND_NOT_APPROVED")

    def test_retro_marked_mr_still_accepted_regardless_of_list(self):
        not_approved = max(r.APPROVED_CLOSURE_MIRS) + 1000
        r.frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: types.SimpleNamespace(**self._mr_row(not_approved, "Retrospective WH import")))
        row, err = r._load_mr("MR-TEST", not_approved)
        self.assertIsNone(err, err)


class TestBackfillSiteGuard(unittest.TestCase):
    """2026-09-27: BACKFILL_SITE only fills a BLANK custom_site; never overwrites one already set."""
    def test_row_with_site_already_set_is_refused(self):
        r.frappe.db = types.SimpleNamespace(
            get_value=lambda dt, name, fields, as_dict=False: types.SimpleNamespace(
                name="ROW1", docstatus=1, purpose="Material Issue", custom_source_id="DN26-0374",
                custom_legacy_dn=None, parent="STE-1", item_code="X", custom_site="ALREADY-SET")
            if dt == "Stock Entry Detail" else
            types.SimpleNamespace(name="STE-1", docstatus=1, purpose="Material Issue", is_return=0,
                                   custom_source_id="DN26-0374", custom_legacy_dn=None))
        out = r._backfill_site({"stock_entry": "STE-1", "row": "ROW1", "site": "ZRH824"}, apply=False)
        self.assertEqual(out["reason"], "SITE_ALREADY_SET")

    def test_blank_row_dry_run_proposes_the_change(self):
        r.frappe.db = types.SimpleNamespace(
            get_value=lambda dt, name, fields, as_dict=False: types.SimpleNamespace(
                name="ROW1", docstatus=1, purpose="Material Issue", custom_source_id="DN26-0374",
                custom_legacy_dn=None, parent="STE-1", item_code="X", custom_site=None)
            if dt == "Stock Entry Detail" else
            types.SimpleNamespace(name="STE-1", docstatus=1, purpose="Material Issue", is_return=0,
                                   custom_source_id="DN26-0374", custom_legacy_dn=None))
        out = r._backfill_site({"stock_entry": "STE-1", "row": "ROW1", "site": "ZRH824"}, apply=False)
        self.assertEqual(out["result"], "dry_run")
        self.assertEqual(out["changes"][0]["site"], "ZRH824")


class TestRefusalShape(unittest.TestCase):
    def test_fail_accepts_a_reason_extra_without_crashing(self):
        # regression (2026-09-24): _fail(..., reason=...) raised "multiple values for argument 'reason'"
        out = r._fail("REASON_NOT_ALLOWED", given_reason="OPERATOR_CANCEL", allowed=["WH_CLOSED"])
        self.assertEqual(out["result"], "refused")
        self.assertEqual(out["reason"], "REASON_NOT_ALLOWED")
        self.assertEqual(out["given_reason"], "OPERATOR_CANCEL")
        r._fail("X", reason="would previously collide")     # must not raise either


if __name__ == "__main__":
    unittest.main()
