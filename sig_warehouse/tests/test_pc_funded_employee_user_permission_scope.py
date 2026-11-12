"""Tests for the narrow Journal Entry Employee-link permission exception."""

import importlib.util
from pathlib import Path
import sys
import types

import pytest


class Field(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value

    def save(self, ignore_permissions=False):
        self["saved_ignore_permissions"] = ignore_permissions


@pytest.fixture
def patch_module(monkeypatch):
    field = Field(fieldtype="Link", options="Employee", ignore_user_permissions=0)
    events = {"cleared": []}
    fake = types.ModuleType("frappe")
    fake.PermissionError = RuntimeError
    fake.db = types.SimpleNamespace(exists=lambda doctype, name: True)
    fake.get_doc = lambda doctype, name: field
    fake.clear_cache = lambda **kwargs: events["cleared"].append(kwargs)
    fake.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
    monkeypatch.setitem(sys.modules, "frappe", fake)
    path = Path(__file__).parents[1] / "sig_warehouse/patches/v1_0/fix_pc_funded_employee_user_permission_scope.py"
    spec = importlib.util.spec_from_file_location("pc_funded_employee_permission_patch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, field, events


def test_patch_marks_only_the_funded_employee_link_to_ignore_user_permissions(patch_module):
    module, field, events = patch_module
    module.execute()
    assert field.ignore_user_permissions == 1
    assert field.saved_ignore_permissions is True
    assert events["cleared"] == [{"doctype": "Journal Entry"}]


def test_patch_is_idempotent_when_target_setting_is_already_present(patch_module):
    module, field, events = patch_module
    field.ignore_user_permissions = 1
    module.execute()
    assert "saved_ignore_permissions" not in field
    assert not events["cleared"]


@pytest.mark.parametrize("fieldtype,options", [("Data", ""), ("Link", "Customer")])
def test_patch_fails_closed_if_field_contract_changed(patch_module, fieldtype, options):
    module, field, events = patch_module
    field.fieldtype = fieldtype
    field.options = options
    with pytest.raises(RuntimeError, match="field contract changed"):
        module.execute()
    assert field.ignore_user_permissions == 0
    assert not events["cleared"]
