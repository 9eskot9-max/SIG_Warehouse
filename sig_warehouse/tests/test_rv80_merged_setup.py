import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


def functions():
    path = Path(__file__).resolve().parents[1] / "sig_operations" / "excel_setup_v3.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("_v3_datasets", "_validated_v3")]
    ns = {"_configured_project_rows": lambda d: d["projects"], "_active_contacts": lambda: [{"id": "c"}],
          "validate": lambda d: d, "frappe": SimpleNamespace(throw=lambda message: (_ for _ in ()).throw(ValueError(message)))}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns


def test_merged_rv80_retains_link_datasets_and_hash_changes():
    api = functions()
    source = {"projects": [{"id": "p", "default_contact": ""}], "tag_definitions": [{"item": "Battery Rack"}],
              "tag_upl_links": [{"tag_item": "Battery Rack", "cuc": "DC-039-2034"}],
              "material_upl_links": [{"item_code": "WH1", "cuc": "DC-039-2034"}], "builder_defaults": []}
    filtered = api["_validated_v3"](source, "RV80")
    result = api["_v3_datasets"](filtered, "RV80")
    assert result["tag_upl_links"] == source["tag_upl_links"]
    assert result["material_upl_links"] == source["material_upl_links"]
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    changed = copy.deepcopy(source)
    changed["tag_upl_links"][0]["cuc"] = "DC-039-2035"
    assert digest(result) != digest(api["_v3_datasets"](api["_validated_v3"](changed, "RV80"), "RV80"))


def test_family_default_and_explicit_exception_ignore_legacy_project_contact():
    path = Path(__file__).resolve().parents[1] / "sig_operations" / "excel_setup_v3.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_configured_project_rows"]
    class Project(dict):
        __getattr__ = dict.get
    project = Project(name="WO-2026-0050", project_name="10001045", custom_default_tawal_contact="MUHANNED", custom_excel_csv_alias="", custom_agreement_no="10001045")
    rule = [None]
    ns = {"_meta_project_fields": lambda: SimpleNamespace(has_field=lambda field: False),
          "frappe": SimpleNamespace(db=SimpleNamespace(get_value=lambda *a, **k: project), throw=lambda m: (_ for _ in ()).throw(ValueError(m))),
          "resolve_project_family": lambda p: {"family": "Colocation", "label": "5G / Colocation", "conflict": False, "values": []},
          "_assignment_default_state": lambda *a: {"default_contact": "MUHANNED", "project_default": "MUHANNED", "assignment_default": "MUHANNED", "needs_reconciliation": False},
          "_family_default": lambda *a: {"tawal_contact": "OMAR", "effective_from": "2026-01-01"},
          "_project_contact_rule": lambda *a: rule[0]}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    data = {"projects": [{"id": "p", "project": "WO-2026-0050", "enabled": True}]}
    row = ns["_configured_project_rows"](data)[0]
    assert (row["default_contact"], row["contact_source"]) == ("OMAR", "family default")
    rule[0] = {"mode": "exception", "tawal_contact": "MUHANNED", "effective_from": "2026-01-01"}
    row = ns["_configured_project_rows"](data)[0]
    assert (row["default_contact"], row["contact_source"]) == ("MUHANNED", "PO exception")
    rule[0] = {"mode": "cleared", "effective_from": "2026-01-01"}
    assert ns["_configured_project_rows"](data)[0]["default_contact"] == ""
