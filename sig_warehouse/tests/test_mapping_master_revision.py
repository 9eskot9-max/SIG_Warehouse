import importlib
import sys
import types


def _module(monkeypatch):
    calls = {"exists": set(), "inserted": []}
    fake = types.ModuleType("frappe")
    fake.session = types.SimpleNamespace(user="operator@example.com")
    fake.form_dict = {}
    fake.PermissionError = type("PermissionError", (Exception,), {})
    fake.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
    fake.get_roles = lambda user: ["Operations User"]
    fake.db = types.SimpleNamespace(exists=lambda doctype, name: name in calls["exists"])
    fake.utils = types.SimpleNamespace(now=lambda: "2026-10-21 12:00:00")

    def get_doc(doc):
        return types.SimpleNamespace(insert=lambda ignore_permissions=False: calls["inserted"].append(doc.copy()))

    fake.get_doc = get_doc
    fake.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, "frappe", fake)
    sys.modules.pop("sig_warehouse.sig_warehouse.mapping_master", None)
    module = importlib.import_module("sig_warehouse.sig_warehouse.mapping_master")
    return module, calls, fake


def test_mapping_revision_receipt_is_idempotent_and_metadata_only(monkeypatch):
    module, calls, fake = _module(monkeypatch)
    fake.form_dict.update({
        "master_key": "mapping.xlsx|mapping master", "fingerprint": "a1b2c3d4",
        "source_workbook": "mapping.xlsx", "source_sheet": "Mapping Master",
        "row_count": "40", "site_count": "12",
    })
    first = module.record_revision()
    assert first["result"] == "created"
    assert calls["inserted"][0]["doctype"] == "SIG Mapping Master Revision"
    assert "mapping_rows" not in calls["inserted"][0]
    calls["exists"].add(first["name"])
    second = module.record_revision()
    assert second == {"result": "duplicate", "name": first["name"]}
    assert len(calls["inserted"]) == 1


def test_mapping_revision_rejects_unknown_role(monkeypatch):
    module, calls, fake = _module(monkeypatch)
    fake.get_roles = lambda user: ["Stock User"]
    try:
        module.record_revision()
    except fake.PermissionError:
        pass
    else:
        raise AssertionError("unauthorized role should be denied")
    assert calls["inserted"] == []
