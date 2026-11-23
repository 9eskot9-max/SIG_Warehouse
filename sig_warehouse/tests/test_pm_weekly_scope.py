import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def pms(setup, families, today="2026-11-24"):
    """Run pm_weekly._pms against a setup and a Project -> family table."""
    tree = ast.parse((ROOT / "sig_operations/pm_weekly.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_pms")
    spec = importlib.util.spec_from_file_location("contract_for_pms", ROOT / "sig_operations/excel_setup_contract.py")
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    frappe = SimpleNamespace(
        db=SimpleNamespace(get_single_value=lambda *a: json.dumps(setup), get_value=lambda dt, name, fields, as_dict=False: {"family": families[name]}),
        utils=SimpleNamespace(nowdate=lambda: today),
        get_meta=lambda dt: SimpleNamespace(has_field=lambda f: f == "custom_project_family"))
    family_module = ModuleType("sig_warehouse.sig_warehouse.project_family")
    family_module.resolve_project_family = lambda row: {"family": row["family"]}
    modules = {"sig_warehouse.sig_operations.excel_setup_contract": contract,
               "sig_warehouse.sig_warehouse.project_family": family_module}
    saved = {k: sys.modules.get(k) for k in modules}
    sys.modules.update(modules)
    try:
        ns = {"frappe": frappe}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "pm_weekly", "exec"), ns)
        return ns["_pms"]()
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def row(employee, role="pm", family="Capex", project="", weekly=True, **extra):
    return {"employee": employee, "role": role, "family": family, "project": project, "weekly_pm": weekly,
            "effective_from": "2026-11-05", "effective_to": "", "enabled": True, **extra}


def test_ticked_pms_cover_their_family_projects_or_their_one_project():
    setup = {"projects": [{"project": "P1", "enabled": True}, {"project": "P2", "enabled": True}, {"project": "P3", "enabled": True}],
             "ops_team_members": [row("A"), row("B", project="P2"), row("C", weekly=False), row("D", role="coordinator", weekly=False),
                                  row("E", effective_to="2026-11-10"), row("F", family="5G / Colocation")]}
    result = pms(setup, {"P1": "Capex", "P2": "Capex", "P3": "Colocation"})
    assert result == {"A": {"P1", "P2"}, "B": {"P2"}, "F": {"P3"}}
