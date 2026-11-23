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


def test_project_id_remains_required_when_po_is_pending():
    value = data()
    value["projects"][0]["po"] = ""
    value["projects"][0]["project"] = ""
    with pytest.raises(ValueError, match="project is required"):
        contract.validate(value)


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d.update(UserPasswords=[]), "Unknown"),
    (lambda d: d.update(builder_profiles=[]), "Unknown"),
    (lambda d: d["projects"][0].update(family="Capex"), "unknown fields"),
    (lambda d: d["projects"][0].update(api_secret="bad"), "unknown fields"),
    (lambda d: d["tag_upl_links"][0].update(tag_item="Unknown"), "definition missing"),
    (lambda d: d["material_upl_links"][0].update(target_uom="String"), "cannot convert"),
    (lambda d: d["material_upl_links"][0].update(quantity_basis=""), "reviewed quantity"),
    (lambda d: d["material_upl_links"][0].update(treatment="Guess"), "treatment"),
    (lambda d: d["tag_definitions"][0].update(priority="first"), "priority"),
    (lambda d: d["projects"][0].update(enabled="yes"), "boolean"),
    (lambda d: d["projects"].append(copy.deepcopy(d["projects"][0])), "duplicate ID"),
    (lambda d: d["builder_defaults"].append({"id": "b", "kind": "routing", "key": "k", "value": "v"}), "Adapter v1"),
    (lambda d: d["builder_defaults"].append({"id": "b", "kind": "csv_remarks", "key": "k", "value": "v", "po": "1"}), "PO-scoped"),
])
def test_invalid_configuration_blocks_publication(mutate, expected):
    value = data()
    mutate(value)
    with pytest.raises(ValueError, match=expected):
        contract.validate(value)


def test_duplicate_logical_links_with_different_ids_are_rejected():
    value = data()
    value["tag_upl_links"].append(dict(value["tag_upl_links"][0], id="different"))
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
    for fn, args in [(module.get_page_state, ()), (module.save_and_publish, ({}, 3)), (module.preview_import, ({}, 3)), (module.apply_import, ({}, 3)), (module.get_history, ())]:
        with pytest.raises(PermissionError):
            fn(*args)


def test_the_v2_workbook_bundle_no_longer_exists(api):
    module, _ = api
    assert not hasattr(module, "get_setup_bundle")


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


def ops(**kw):
    row = {"id": "o1", "family": "Capex", "project": "", "employee": "E1", "role": "pm", "effective_from": "2026-11-05", "enabled": True}
    row.update(kw)
    return {"ops_team_members": [row]}


def test_operations_row_needs_a_role_and_a_family_except_warehouse():
    assert contract.validate(ops())["ops_team_members"][0]["weekly_pm"] is False
    with pytest.raises(ValueError, match="role is required"):
        contract.validate(ops(role=""))
    with pytest.raises(ValueError, match="pm, coordinator or warehouse"):
        contract.validate(ops(role="member"))
    with pytest.raises(ValueError, match="supported family"):
        contract.validate(ops(family=""))
    assert contract.validate(ops(role="warehouse", family=""))["ops_team_members"][0]["family"] == ""
    with pytest.raises(ValueError, match="no family"):
        contract.validate(ops(role="warehouse", family="Capex"))


def test_only_a_pm_can_receive_the_weekly_check_and_colocation_is_normalised():
    assert contract.validate(ops(weekly_pm=True, family="Colocation"))["ops_team_members"][0]["family"] == "5G / Colocation"
    with pytest.raises(ValueError, match="Only a PM"):
        contract.validate(ops(role="coordinator", weekly_pm=True))


def test_crew_flags_default_and_overlapping_leaders_are_rejected():
    crew = {"id": "c", "team_name": "Crew", "family": "Capex", "archetype": "Project"}
    assert contract.validate({"operational_teams": [crew]})["operational_teams"][0]["no_visit_message"] is True

    def lead(i, e, a, b):
        return {"id": i, "team": "c", "employee": e, "role": "leader", "effective_from": a, "effective_to": b, "enabled": True}
    with pytest.raises(ValueError, match="Overlapping Crew leader"):
        contract.validate({"operational_teams": [crew], "team_memberships": [lead("a", "E1", "2026-01-01", ""), lead("b", "E2", "2026-06-01", "")]})
    with pytest.raises(ValueError, match="leader or member"):
        contract.validate({"operational_teams": [crew], "team_memberships": [dict(lead("a", "E1", "2026-01-01", ""), role="pm")]})


def test_setup_warnings_name_what_would_be_silently_skipped():
    datasets = contract.validate({
        "family_tawal_defaults": [{"id": "f", "family": "Capex", "tawal_contact": "C", "effective_from": "2026-01-01"}],
        "operational_teams": [{"id": "c", "team_name": "Crew A", "family": "Capex", "archetype": "Project"}],
        **ops()})
    notes = contract.setup_warnings(datasets, "2026-11-24")
    assert any("Incident" in n and "TAWAL" in n for n in notes)
    assert any("Capex has no active Operations coordinator" in n for n in notes)
    assert any("Crew A" in n and "exactly one active leader" in n for n in notes)
    assert not any("Capex" in n and "TAWAL" in n for n in notes)


def test_removed_lists_and_v2_bundle_are_gone():
    for name in ("builder_profiles", "builder_contacts", "project_builder_links", "teams", "team_projects",
                 "project_responsibilities", "project_tawal_rules"):
        assert name not in contract.FIELDS
    assert not hasattr(contract, "project_bundle") and not hasattr(contract, "upgrade_legacy")


def load_migration():
    spec = importlib.util.spec_from_file_location("ops_setup_migration_test", ROOT / "sig_operations/ops_setup_migration.py")
    module = importlib.util.module_from_spec(spec)
    key = "sig_warehouse.sig_operations.excel_setup_contract"
    previous = sys.modules.get(key)
    sys.modules[key] = contract
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules[key]
        else:
            sys.modules[key] = previous
    return module


def test_migration_gives_roles_adds_warehouse_and_keeps_crew_history():
    mig = load_migration()
    stored = {
        "builder_profiles": [{"id": "x"}], "teams": [{"leader": "L1", "team": "Crew One", "enabled": True}],
        "projects": [{"id": "p", "project": "P", "po": "1", "family": "Capex", "enabled": True}],
        "operational_teams": [{"id": "c1", "team_name": "Crew One", "family": "Capex", "archetype": "Project", "enabled": True}],
        "team_memberships": [{"id": "m", "team": "c1", "employee": "L1", "role": "leader", "effective_from": "2026-11-05", "enabled": True}],
        "ops_team_members": [
            {"id": "a", "family": "Capex", "project": "", "employee": "E1", "effective_from": "2026-11-05", "enabled": True},
            {"id": "b", "family": "Capex", "project": "", "employee": "E2", "effective_from": "2026-11-05", "enabled": True}]}
    names = {"E1": "Mohammed Sohail Mohammed Ilyas", "E2": "Ghlzar Ahmad Fazal Malik"}
    out = mig.migrate(stored, names, ["W1"], "2026-11-24")
    assert "builder_profiles" not in out and "family" not in out["projects"][0]
    assert {r["employee"]: r["role"] for r in out["ops_team_members"]} == {"E1": "pm", "E2": "coordinator", "W1": "warehouse"}
    assert out["team_memberships"][0]["effective_from"] == mig.OPEN_START
    assert contract.validate(out)
    assert mig.migrate(out, names, ["W1"], "2026-11-24") == out   # repeatable
    stored["ops_team_members"][0]["employee"] = "E9"
    with pytest.raises(ValueError, match="not in the previous roster"):
        mig.migrate(stored, names, [], "2026-11-24")


def test_history_names_who_published_and_which_lists_changed(api):
    module, stub = api
    stub.roles = {"SIG Excel Setup Editor"}
    old = json.dumps({"ops_team_members": [], "family_tawal_defaults": [{"id": "a"}]})
    new = json.dumps({"ops_team_members": [{"id": "o"}], "family_tawal_defaults": [{"id": "a"}]})
    stub.get_all = lambda *a, **k: [{"revision": 2, "published_by": "pm@x", "configuration_json": new},
                                    {"revision": 1, "published_by": "owner@x", "configuration_json": old}]
    first, second = module.get_history()
    assert (first["published_by"], first["changed"]) == ("pm@x", ["ops_team_members (1)"])
    assert second["changed"] == [] and "configuration_json" not in first
