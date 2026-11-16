"""Router decisions must be accepted by the persisted DocType metadata."""
import ast
import json
from pathlib import Path


def test_engine_literal_decisions_are_valid_select_options():
    root = Path(__file__).parents[1] / "sig_accounting"
    metadata = json.loads((root / "doctype/snb_movement_review/snb_movement_review.json").read_text(encoding="utf-8"))
    options = set(next(field for field in metadata["fields"] if field["fieldname"] == "decision_type")["options"].splitlines())
    tree = ast.parse((root / "bank_router/engine.py").read_text(encoding="utf-8"))
    decisions = {kw.value.value for node in ast.walk(tree) if isinstance(node, ast.Call)
                 for kw in node.keywords if kw.arg == "decision_type" and isinstance(kw.value, ast.Constant)
                 and isinstance(kw.value.value, str)}
    assert "CHOOSE_PURPOSE" in decisions
    assert decisions <= options
