"""Stock Entry builders must post consumption to the materials expense account (decision 2026-10-04).

Source-level checks (no Frappe import) so they run anywhere and fail loudly if someone drops the line
or points a builder back at the stock-adjustment account 5129."""
import ast
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1] / "sig_warehouse"


def _src(name):
    return (BASE / name).read_text(encoding="utf-8")


def _assignments_of_materials_account(src):
    """Count places that set expense_account to MATERIALS_EXPENSE_ACCOUNT, as a dict entry or item["expense_account"] = ..."""
    hits = 0
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "expense_account"
                        and isinstance(value, ast.Name) and value.id == "MATERIALS_EXPENSE_ACCOUNT"):
                    hits += 1
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "expense_account"
                        and isinstance(node.value, ast.Name) and node.value.id == "MATERIALS_EXPENSE_ACCOUNT"):
                    hits += 1
    return hits


def test_constant_is_the_materials_account():
    tree = ast.parse(_src("ledger_accounts.py"))
    values = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)}
    assert values["MATERIALS_EXPENSE_ACCOUNT"] == "5121 - مواد - SIG"


def test_workbench_dispatch_issue_sets_materials_account():
    assert _assignments_of_materials_account(_src("dispatch_operation.py")) == 1


def test_return_receipt_sets_materials_account():
    assert _assignments_of_materials_account(_src("disposition.py")) == 1


def test_custody_issue_sets_materials_account():
    assert _assignments_of_materials_account(_src("custody.py")) == 1


def test_no_builder_hardcodes_the_stock_adjustment_account():
    for name in ("dispatch_operation.py", "disposition.py", "custody.py"):
        assert "5129" not in _src(name), name
