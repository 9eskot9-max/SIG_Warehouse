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
    source = {"projects": [{"id": "p"}], "tag_definitions": [{"item": "Battery Rack"}],
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
