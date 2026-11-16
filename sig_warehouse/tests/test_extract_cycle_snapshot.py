import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "scripts" / "extract_cycle_snapshot.py"
spec = importlib.util.spec_from_file_location("extract_cycle_snapshot", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DumpParserTests(unittest.TestCase):
    def test_handles_quoted_null_escapes_and_punctuation(self):
        self.assertEqual([["NULL", None, "a,b(c)", "one\ntwo", "O'Reilly"]],
            list(module.rows("('NULL',NULL,'a,b(c)','one\\ntwo','O\\'Reilly');")))

    def test_rejects_truncated_row(self):
        with self.assertRaises(ValueError):
            list(module.rows("('not closed"))


if __name__ == "__main__":
    unittest.main()
