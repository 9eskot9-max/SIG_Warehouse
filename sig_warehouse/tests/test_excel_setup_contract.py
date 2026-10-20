"""Offline contract/security tests; these do not substitute for Frappe/Excel UAT."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_contract_test", ROOT / "sig_operations/excel_setup_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def data():
    return {
        "projects": [{"id": "p", "project": "ERP-P", "po": "001", "alias": "Capex", "enabled": True}],
        "tag_definitions": [{"id": "t", "item": "Module", "rule": "Module", "priority": "1"}],
        "tag_upl_links": [{"id": "l", "tag_item": "Module", "cuc": "CUC"}],
        "material_upl_links": [{"id": "m", "item_code": "ITEM", "cuc": "CUC", "treatment": "Direct 1:1", "source_uom": "Nos", "target_uom": "Nos", "quantity_basis": "One module = one contract unit"}],
        "builder_defaults": [],
    }


def test_normalization_preserves_ids_po_zeroes_and_disabled_rows():
    value = data()
    value["tag_definitions"][0]["enabled"] = False
    value["tag_upl_links"][0]["enabled"] = False
    result = contract.validate(value)
    assert result["projects"][0]["po"] == "001"
    assert result["tag_definitions"][0]["enabled"] is False
    assert result["projects"][0]["upl_revision"] == ""


def test_builder_alias_may_link_multiple_projects_and_po_may_be_pending():
    value = data()
    value["projects"].append({
        "id": "p2", "project": "ERP-P2", "po": "", "alias": "Capex", "enabled": True
    })
    result = contract.validate(value)
    assert [(row["project"], row["alias"], row["po"]) for row in result["projects"]] == [
        ("ERP-P", "Capex", "001"), ("ERP-P2", "Capex", "")
    ]


def test_project_id_remains_required_when_po_is_pending():
    value = data()
    value["projects"][0]["po"] = ""
    value["projects"][0]["project"] = ""
    with pytest.raises(ValueError, match="project is required"):
        contract.validate(value)


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d.update(UserPasswords=[]), "Unknown"),
    (lambda d: d["projects"][0].update(api_secret="bad"), "unknown fields"),
    (lambda d: d["tag_upl_links"][0].update(tag_item="Unknown"), "definition missing"),
    (lambda d: d["material_upl_links"][0].update(target_uom="String"), "cannot convert"),
    (lambda d: d["material_upl_links"][0].update(quantity_basis=""), "reviewed quantity"),
    (lambda d: d["material_upl_links"][0].update(treatment="Guess"), "treatment"),
    (lambda d: d["tag_definitions"][0].update(priority="first"), "priority"),
    (lambda d: d["projects"][0].update(enabled="yes"), "boolean"),
    (lambda d: d["projects"].append(copy.deepcopy(d["projects"][0])), "duplicate ID"),
    (lambda d: d["builder_defaults"].append({"id":"b", "kind":"routing", "key":"k", "value":"v"}), "Adapter v1"),
    (lambda d: d["builder_defaults"].append({"id":"b", "kind":"csv_remarks", "key":"k", "value":"v", "po":"1"}), "PO-scoped"),
])
def test_invalid_configuration_blocks_publication(mutate, expected):
    value = data()
    mutate(value)
    with pytest.raises(ValueError, match=expected):
        contract.validate(value)


def test_duplicate_logical_links_with_different_ids_are_rejected():
    value = data()
    other = dict(value["tag_upl_links"][0], id="different")
    value["tag_upl_links"].append(other)
    with pytest.raises(ValueError, match="duplicate scoped"):
        contract.validate(value)


def test_global_tag_link_cannot_rely_on_foreign_po_definition():
    value = data()
    value["tag_definitions"][0]["po"] = "OTHER"
    with pytest.raises(ValueError, match="PO scope"):
        contract.validate(value)


def test_separate_po_rules_remain_distinct_and_priority_is_explicit():
    value = data()
    value["tag_upl_links"].append(dict(value["tag_upl_links"][0], id="other", po="002"))
    value["tag_definitions"].append({"id":"z", "item":"Battery", "rule":"Battery", "priority":"0"})
    result = contract.validate(value)
    assert len(result["tag_upl_links"]) == 2
    assert result["tag_definitions"][0]["id"] == "z"


def test_merge_is_additive_no_implicit_retirements_and_repeatable():
    original = contract.validate(data())
    package = {"schema_version":1, "batch_id":"test", "datasets":{"builder_defaults":[{"id":"b", "kind":"csv_remarks", "key":"K", "value":"V"}]}}
    first, counts = contract.merge_import(original, package)
    second, _ = contract.merge_import(first, package)
    assert first == second
    assert len(first["projects"]) == 1
    assert counts["added"] == 1
    assert original["builder_defaults"] == []


def test_merge_rejects_duplicate_ids_inside_batch():
    row = {"id":"b", "kind":"csv_remarks", "key":"K", "value":"V"}
    with pytest.raises(ValueError, match="duplicate ID inside"):
        contract.merge_import(contract.validate(data()), {"schema_version":1,"batch_id":"b","datasets":{"builder_defaults":[row,row]}})


def test_workbook_projections_do_not_include_other_workbook_datasets():
    value = contract.validate(data())
    rv = contract.project_bundle(value, "RV80")
    pc = contract.project_bundle(value, "SIGPC")
    assert "material_upl_links" not in rv and "builder_defaults" not in pc
    assert set(pc["projects"][0]) == {"id", "project", "po", "upl_revision", "enabled"}
    rv["projects"][0]["po"] = "changed"
    assert value["projects"][0]["po"] == "001"
    with pytest.raises(ValueError):
        contract.project_bundle(value, "OTHER")


@pytest.fixture
def api(monkeypatch):
    stub = ModuleType("frappe")
    stub.whitelist = lambda *args, **kw: (lambda f: f)
    stub.session = SimpleNamespace(user="reader@example.test")
    stub.roles = {"SIG Stock Viewer"}
    stub.get_roles = lambda: stub.roles
    stub.PermissionError = PermissionError
    def throw(message, error=ValueError):
        raise error(message)
    stub.throw = throw
    utils = ModuleType("frappe.utils")
    utils.now_datetime = lambda: "2026-10-20 00:00:00"
    monkeypatch.setitem(sys.modules, "frappe", stub)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    monkeypatch.setitem(sys.modules, "sig_warehouse.sig_operations.excel_setup_contract", contract)
    spec = importlib.util.spec_from_file_location("excel_setup_api_test", ROOT / "sig_operations/excel_setup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    doc = SimpleNamespace(revision=3, published_at="2026-10-20", published_hash="hash")
    monkeypatch.setattr(module, "_state", lambda lock=False: (doc, contract.validate(data())))
    return module, stub


def test_reader_cannot_use_any_editor_endpoint(api):
    module, _ = api
    for fn, args in [(module.get_page_state,()),(module.save_and_publish,({},3)),(module.preview_import,({},3)),(module.apply_import,({},3)),(module.get_history,())]:
        with pytest.raises(PermissionError):
            fn(*args)


def test_guest_and_unrelated_role_cannot_fetch(api):
    module, stub = api
    stub.session.user = "Guest"
    with pytest.raises(PermissionError):
        module.get_setup_bundle("RV80", 1)
    stub.session.user = "employee"
    stub.roles = {"Employee"}
    with pytest.raises(PermissionError):
        module.get_setup_bundle("RV80", 1)


def test_projected_payload_checksum_and_revision_unchanged(api):
    module, _ = api
    response = module.get_setup_bundle("SIGPC", 1)
    expected = base64.b64encode(hashlib.sha256(response["payload_json"].encode()).digest()).decode()
    assert response["payload_sha256_b64"] == expected
    assert json.loads(response["payload_json"]) == response["datasets"]
    assert response["complete"] is True
    unchanged = module.get_setup_bundle("SIGPC", 1, last_revision=3)
    assert unchanged["unchanged"] and unchanged["datasets"] == {}
    with pytest.raises(ValueError, match="Unsupported"):
        module.get_setup_bundle("SIGPC", 2)


def test_stale_editor_write_rejected_before_any_mutation(api, monkeypatch):
    module, stub = api
    stub.roles = {"SIG Excel Setup Editor"}
    with pytest.raises(ValueError, match="another session"):
        module.save_and_publish(data(), 2)


def test_enabled_material_link_rejects_mapping_unit_not_in_erp(api):
    module, stub = api
    class DB:
        @staticmethod
        def exists(doctype, name):
            return (doctype, name) in {("Item", "E-Lit-MT-150"), ("UOM", "Nos")}
        @staticmethod
        def get_value(doctype, name, field):
            assert (doctype, name, field) == ("Item", "E-Lit-MT-150", "stock_uom")
            return "Nos"
    stub.db = DB()
    row = {"enabled": True, "item_code": "E-Lit-MT-150", "source_uom": "Nos", "target_uom": "Bogus UOM"}
    with pytest.raises(ValueError, match="does not exist in ERP"):
        module._linked_masters({"projects": [], "material_upl_links": [row]})
    row["target_uom"] = "Nos"
    module._linked_masters({"projects": [], "material_upl_links": [row]})


def test_operations_roles_and_new_matrices_are_narrow():
    for slug in ("sig_excel_setup", "sig_excel_setup_revision"):
        value = json.loads((ROOT / f"sig_operations/doctype/{slug}/{slug}.json").read_text())
        assert "SIG Excel Setup Editor" in {p["role"] for p in value["permissions"]}
        assert all(not p.get("write") and not p.get("create") and not p.get("delete") for p in value["permissions"])
    page = json.loads((ROOT / "sig_operations/page/excel_setup/excel_setup.json").read_text())
    assert page["module"] == "SIG Operations"
    assert "Employee" not in {p["role"] for p in page["roles"]}


def test_standard_doctype_controller_names_match_frappe_loader():
    import ast
    for name in ("SIG Excel Setup", "SIG Excel Setup Revision"):
        slug = name.lower().replace(" ", "_")
        tree = ast.parse((ROOT / f"sig_operations/doctype/{slug}/{slug}.py").read_text())
        assert name.replace(" ", "") in {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def test_permission_migration_is_append_only_and_repeatable(monkeypatch):
    stub = ModuleType("frappe")
    editor = "SIG Excel Setup Editor"
    roles, user_roles = set(), {"ops": {"Projects User", "SIG Finance Viewer"}, "inactive": {"Projects User"}, "hr": {"HR User"}}
    class Profile:
        def __init__(self): self.roles = [SimpleNamespace(role="Projects User")]
        def append(self, field, row):
            child = SimpleNamespace(**row, db_insert=lambda: None)
            self.roles.append(child)
            return child
        def save(self, **kw): raise AssertionError("RoleProfile.save would queue a destructive role fanout")
    profiles = {"SIG PM": Profile()}
    class DB:
        def exists(self, dt, key):
            if dt == "Role": return key in roles
            if dt == "Role Profile": return key in profiles
            if dt == "Custom DocPerm": return False
            if dt == "Has Role": return key["role"] in user_roles[key["parent"]]
            raise AssertionError(dt)
        def get_single_value(self, *args): return 0
        def set_single_value(self, *args): pass
    stub.db = DB()
    def get_doc(dt, name=None):
        if dt == "Role Profile": return profiles[name]
        def insert(**kw):
            if dt["doctype"] == "Role": roles.add(dt["role_name"])
            elif dt["doctype"] == "Has Role": user_roles[dt["parent"]].add(dt["role"])
            else: raise AssertionError(dt)
        return SimpleNamespace(insert=insert)
    stub.get_doc = get_doc
    stub.get_all = lambda dt, filters, pluck: ["ops"] if filters["role_profile_name"] == "SIG PM" else []
    stub.clear_cache = lambda **kwargs: None
    stub.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
    monkeypatch.setitem(sys.modules, "frappe", stub)
    spec = importlib.util.spec_from_file_location("setup_permission_patch_test", ROOT / "sig_warehouse/patches/v1_0/add_excel_setup.py")
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    patch.execute()
    patch.execute()
    assert user_roles["ops"] == {"Projects User", "SIG Finance Viewer", editor}
    assert user_roles["inactive"] == {"Projects User"}
    assert user_roles["hr"] == {"HR User"}
    assert [row.role for row in profiles["SIG PM"].roles].count(editor) == 1


def test_builder_contacts_resolve_existing_directory_and_project_eligibility(api):
    module, stub = api
    row = contract.validate(data())["projects"][0]
    row.update(contact_email="c@example.test", contact_name="Old display")
    contact = SimpleNamespace(name="contact-1", full_name="Canonical name", mobile="00123", email="c@example.test")
    stub.get_all = lambda *args, **kwargs: [contact]
    stub.get_meta = lambda dt: SimpleNamespace(has_field=lambda field: False)
    stub.db = SimpleNamespace(exists=lambda dt, value: dt == "DocType" and value in ("SIG TAWAL Contact", "SIG Project PM Assignment") or dt == "SIG Project PM Assignment" and value["project"] == "ERP-P")
    module._resolve_contact(row)
    assert row["tawal_contact"] == "contact-1"
    assert row["contact_name"] == "Canonical name"
    assert row["contact_phone"] == "00123"
    row["project"] = "OTHER"
    with pytest.raises(ValueError, match="not assigned"):
        module._resolve_contact(row)


def test_ambiguous_directory_match_never_creates_a_parallel_contact(api):
    module, stub = api
    row = contract.validate(data())["projects"][0]
    row.update(contact_email="c@example.test")
    stub.db = SimpleNamespace(exists=lambda *args: True)
    stub.get_all = lambda *args, **kwargs: [SimpleNamespace(name="one"), SimpleNamespace(name="two")]
    with pytest.raises(ValueError, match="one exact contact"):
        module._resolve_contact(row)
