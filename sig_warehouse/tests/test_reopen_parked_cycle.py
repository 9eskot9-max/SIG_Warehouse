import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta
from textwrap import dedent
from pathlib import Path
from unittest.mock import patch


class ReopenWriterTests(unittest.TestCase):
    def setUp(self):
        self.modules = patch.dict(sys.modules, {"frappe": types.ModuleType("frappe")})
        self.modules.start()
        path = Path(__file__).resolve().parents[1] / "sig_warehouse/patches/v1_0/reopen_parked_cycle.py"
        spec = importlib.util.spec_from_file_location("reopen_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.modules.stop()

    def test_duplicate_check_precedes_insert_and_commit(self):
        source = "    dup_cycle = True\n    if True:\n        if True:\n            if True:\n                cycdoc.set('sessions_auto_closed', (cycdoc.get('sessions_auto_closed') or 0) + 1)\n    cycdoc.save(ignore_permissions=True)\n    ev.insert(ignore_permissions=True)\n    frappe.db.commit()\n"
        result = self.module.rewrite(source)
        self.assertEqual(result, self.module.rewrite(result))
        self.assertLess(result.index("dup_cycle"), result.index("SIG_PARKED_REOPEN_V1"))
        self.assertLess(result.index("SIG_PARKED_REOPEN_V1"), result.index("frappe.db.commit()"))
        compile("def test():\n" + result, "writer", "exec")

    def test_writer_transition_and_audit(self):
        at = datetime(2026, 11, 16, 12)
        for code, days, terminal, expected in (
            ("TCN_GENERATED", 0, 0, "Open"),
            ("FIELD_VISIT_COMPLETED", 0, 0, "Open"),
            ("MIR_CONFIRMED", 30, 0, "Parked"),
            ("MIR_CONFIRMED", 31, 0, "Open"),
            ("SITE_CLOSED", 31, 1, "Closed"),
        ):
            with self.subTest(code=code, days=days, terminal=terminal):
                values = {"sig_lifecycle": "Parked", "sig_parked_at": at, "terminal": terminal}
                comments = []
                writer = types.SimpleNamespace(
                    utils=types.SimpleNamespace(
                        get_datetime=lambda value: value,
                        now=lambda: at + timedelta(days=days),
                        add_to_date=lambda value, days, as_datetime: value + timedelta(days=days),
                    ),
                    get_doc=lambda doc: types.SimpleNamespace(insert=lambda **kw: comments.append(doc)),
                )
                scope = {"frappe": writer, "cycdoc": types.SimpleNamespace(get=values.get, set=values.__setitem__),
                         "event_code": code, "cyc": "C-1"}
                exec(dedent(self.module.BLOCK + self.module.AUDIT_BLOCK), scope)
                self.assertEqual(expected, values["sig_lifecycle"])
                self.assertEqual(int(expected == "Open"), len(comments))

    def test_missing_or_duplicate_anchor_is_rejected(self):
        for source in ("unknown", "    ev.insert(ignore_permissions=True)\n" * 2):
            with self.assertRaises(ValueError):
                self.module.rewrite(source)


if __name__ == "__main__":
    unittest.main()
