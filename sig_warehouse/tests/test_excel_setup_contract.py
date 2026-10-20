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
        "projects": [{"id": "p", "project": "ERP-P", "po": "001", "enabled": True}],
        "builder_profiles": [{"id": "profile", "alias": "Capex", "enabled": True}],
        "builder_contacts": [{"id": "contact", "profile": "profile", "tawal_contact": "contact-1", "enabled": True}],
        "project_builder_links": [{"id": "link", "project": "ERP-P", "profile": "profile", "stream": "", "enabled": True}],
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
    value["projects"].append({"id": "p2", "project": "ERP-P2", "po": "", "enabled": True})
    value["project_builder_links"].append({"id": "link2", "project": "ERP-P2", "profile": "profile", "enabled": True})
    result = contract.validate(value)
    assert len(result["builder_profiles"]) == 1
    assert [(r["project"], r["profile"]) for r in result["project_builder_links"]] == [("ERP-P", "profile"), ("ERP-P2", "profile")]
    assert result["projects"][1]["po"] == ""


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
    package = {"schema_version":2, "batch_id":"test", "datasets":{"builder_defaults":[{"id":"b", "kind":"csv_remarks", "key":"K", "value":"V"}]}}
    first, counts = contract.merge_import(original, package)
    second, _ = contract.merge_import(first, package)
    assert first == second
    assert len(first["projects"]) == 1
    assert counts["added"] == 1
    assert original["builder_defaults"] == []


def test_merge_rejects_duplicate_ids_inside_batch():
    row = {"id":"b", "kind":"csv_remarks", "key":"K", "value":"V"}
    with pytest.raises(ValueError, match="duplicate ID inside"):
        contract.merge_import(contract.validate(data()), {"schema_version":2,"batch_id":"b","datasets":{"builder_defaults":[row,row]}})


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
        module.get_setup_bundle("RV80", 2)
    stub.session.user = "employee"
    stub.roles = {"Employee"}
    with pytest.raises(PermissionError):
        module.get_setup_bundle("RV80", 2)


def test_projected_payload_checksum_and_revision_unchanged(api):
    module, _ = api
    response = module.get_setup_bundle("SIGPC", 2)
    expected = base64.b64encode(hashlib.sha256(response["payload_json"].encode()).digest()).decode()
    assert response["payload_sha256_b64"] == expected
    assert json.loads(response["payload_json"]) == response["datasets"]
    assert response["complete"] is True
    unchanged = module.get_setup_bundle("SIGPC", 2, last_revision=3)
    assert unchanged["unchanged"] and unchanged["datasets"] == {}
    with pytest.raises(ValueError, match="Unsupported"):
        module.get_setup_bundle("SIGPC", 1)


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


def test_builder_contacts_resolve_existing_directory_without_inventing_project_assignment(api):
    module, stub = api
    row = contract.validate(data())["builder_contacts"][0]
    row.update(contact_email="c@example.test", contact_name="Old display")
    contact = SimpleNamespace(name="contact-1", full_name="Canonical name", mobile="00123", email="c@example.test")
    stub.get_all = lambda *args, **kwargs: [contact]
    stub.db = SimpleNamespace(exists=lambda dt, value: dt == "DocType" and value == "SIG TAWAL Contact")
    module._resolve_contact(row)
    assert row["tawal_contact"] == "contact-1"
    assert row["contact_name"] == "Canonical name"
    assert row["contact_phone"] == "00123"
    assert "project" not in row


def test_ambiguous_directory_match_never_creates_a_parallel_contact(api):
    module, stub = api
    row = contract.validate(data())["builder_contacts"][0]
    row.update(contact_email="c@example.test")
    stub.db = SimpleNamespace(exists=lambda *args: True)
    stub.get_all = lambda *args, **kwargs: [SimpleNamespace(name="one"), SimpleNamespace(name="two")]
    with pytest.raises(ValueError, match="one exact contact"):
        module._resolve_contact(row)


def test_profiles_can_precede_any_project_or_po():
    value = data()
    value["projects"] = []
    value["project_builder_links"] = []
    result = contract.validate(value)
    assert result["builder_profiles"][0]["alias"] == "Capex"
    assert contract.bundle_complete(result, "RV80")


@pytest.mark.parametrize("mutate", [
    lambda d: d["project_builder_links"][0].update(profile="missing"),
    lambda d: d["project_builder_links"][0].update(project="missing"),
    lambda d: d["builder_profiles"][0].update(enabled=False),
    lambda d: d["builder_contacts"][0].update(profile="missing"),
])
def test_dangling_assignments_or_contacts_cannot_publish(mutate):
    value = data()
    mutate(value)
    with pytest.raises(ValueError, match="enabled"):
        contract.validate(value)


def test_profile_alias_is_unique_but_can_be_assigned_repeatedly():
    value = data()
    value["builder_profiles"].append(dict(value["builder_profiles"][0], id="other", alias="CAPEX"))
    with pytest.raises(ValueError, match="duplicate scoped"):
        contract.validate(value)


def legacy_data():
    value = {k: v for k, v in data().items() if k not in ("builder_profiles", "builder_contacts", "project_builder_links")}
    value["projects"] = [
        {"id": "rv80-project-8", "project": "WO-0041", "po": "1000170", "alias": "capex7", "family": "", "template": "wrong", "internal_pm": "unverified", "enabled": True},
        {"id": "rv80-project-7", "project": "WO-0040", "po": "1000157", "alias": "incident", "family": "5G", "enabled": True},
    ]
    return value


def test_legacy_migration_never_carries_forward_false_row_joins():
    legacy = legacy_data()
    original = copy.deepcopy(legacy)
    upgraded = contract.upgrade_legacy(legacy)
    assert legacy == original
    assert upgraded["builder_profiles"] == upgraded["builder_contacts"] == upgraded["project_builder_links"] == []
    assert {(r["project"], r["po"]) for r in upgraded["projects"]} == {("WO-0041", "1000170"), ("WO-0040", "1000157")}
    assert not any("alias" in r or "internal_pm" in r for r in upgraded["projects"])
    assert upgraded["tag_definitions"] == contract.validate(data())["tag_definitions"]
    assert contract.upgrade_legacy(upgraded) == upgraded
    assert not contract.bundle_complete(upgraded, "RV80")


def test_legacy_seed_and_historical_bundle_cannot_reintroduce_row_joins(api, monkeypatch):
    module, stub = api
    with pytest.raises(ValueError, match="schema_version 2"):
        contract.merge_import(contract.validate(data()), {"schema_version": 1, "datasets": legacy_data(), "batch_id": "old"})
    monkeypatch.setattr(module, "_state", lambda lock=False: (SimpleNamespace(revision=3), legacy_data()))
    with pytest.raises(ValueError, match="Legacy Project/Builder"):
        module.get_setup_bundle("RV80", 2)


def test_empty_or_disabled_profiles_never_clear_existing_rv80(api, monkeypatch):
    module, stub = api
    value = contract.upgrade_legacy(legacy_data())
    monkeypatch.setattr(module, "_state", lambda lock=False: (SimpleNamespace(revision=4, published_at="today"), value))
    assert module.get_setup_bundle("RV80", 2)["complete"] is False
    assert module.get_setup_bundle("SIGPC", 2)["complete"] is True


def test_native_stream_must_belong_to_explicit_project(api):
    module, stub = api
    stub.db = SimpleNamespace(exists=lambda *args: True, get_value=lambda *args: "OTHER")
    with pytest.raises(ValueError, match="stream belonging"):
        module._linked_masters({"projects": [], "project_builder_links": [{"enabled": True, "project": "P", "profile": "builder", "stream": "S"}], "material_upl_links": []})


def test_split_migration_patch_is_repeatable(monkeypatch, api):
    module, stub = api
    from importlib.util import spec_from_file_location, module_from_spec
    state = {"data": legacy_data(), "revision": 3}
    writes = []
    def publish(value, revision):
        assert revision == state["revision"]
        state.update(data=value, revision=revision+1)
        writes.append(value)
    monkeypatch.setattr(module, "_state", lambda lock=False: (SimpleNamespace(revision=state["revision"]), state["data"]))
    monkeypatch.setattr(module, "_publish", publish)
    monkeypatch.setitem(sys.modules, "sig_warehouse.sig_operations.excel_setup", module)
    stub.db = SimpleNamespace(exists=lambda *args: True)
    spec = spec_from_file_location("split_patch", ROOT / "sig_warehouse/patches/v1_0/split_excel_setup_structure.py")
    patch = module_from_spec(spec)
    spec.loader.exec_module(patch)
    patch.execute()
    patch.execute()
    assert len(writes) == 1 and state["revision"] == 4


def test_pending_legacy_contacts_are_retained_but_block_rv80_import(api):
    module, stub = api
    row = contract.validate(data())["builder_contacts"][0]
    row.update(tawal_contact="", contact_name="Legacy contact", origin="RV80 Builder")
    stub.db = SimpleNamespace(exists=lambda *args: True)
    stub.get_all = lambda *args, **kwargs: []
    module._resolve_contact(row)
    assert row["contact_name"] == "Legacy contact" and not row["tawal_contact"]
    value = contract.validate(data())
    value["builder_contacts"] = [row]
    assert not contract.bundle_complete(value, "RV80")
    row["origin"] = "ERP directory"
    with pytest.raises(ValueError, match="one exact contact"):
        module._resolve_contact(row)


def test_seed_ignores_po_validation_order_and_keeps_profiles_before_po():
    spec = importlib.util.spec_from_file_location("builder_seed_test", ROOT / "sig_operations/excel_setup_seed.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    rows = [{"R": "capex7", "S": "Contact", "T": "00123", "U": "c@example.test", "Y": "PM", "AC": "1000170", "AB": "5G"},
            {"R": "mobily", "S": "Other", "AC": "1000238"}]
    first = seed.builder_seed(rows, "seed")
    rows[0]["AC"], rows[1]["AC"] = rows[1]["AC"], rows[0]["AC"]
    rows[0]["AB"] = "Incident"
    assert seed.builder_seed(rows, "seed") == first
    assert set(first["datasets"]) == {"builder_profiles", "builder_contacts"}
    assert {r["alias"] for r in first["datasets"]["builder_profiles"]} == {"capex7", "mobily"}
    result = contract.validate(first["datasets"])
    assert result["projects"] == result["project_builder_links"] == []
    assert first["datasets"]["builder_contacts"][0]["contact_phone"] in ("00123", "")


def test_conflicting_profile_source_rows_require_review():
    spec = importlib.util.spec_from_file_location("builder_seed_conflict", ROOT / "sig_operations/excel_setup_seed.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    with pytest.raises(ValueError, match="Conflicting template"):
        seed.builder_seed([{"R": "5g", "V": "one"}, {"R": "5g", "V": "two"}], "seed")
