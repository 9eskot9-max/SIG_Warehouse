from pathlib import Path
from unittest.mock import Mock

import pytest

PATCH_PATH = (
    Path(__file__).resolve().parents[1]
    / "sig_warehouse"
    / "patches"
    / "v1_0"
    / "fix_sig_material_issue_print_items.py"
)


def load_patch(monkeypatch):
    import importlib.util
    import sys
    import types

    fake_frappe = types.ModuleType("frappe")
    fake_frappe.db = Mock()
    fake_frappe.throw = Mock(side_effect=RuntimeError)
    fake_frappe.get_doc = Mock()
    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    spec = importlib.util.spec_from_file_location("print_items_patch_test", PATCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fake_frappe


def test_repair_html_replaces_all_three_dictionary_method_references(monkeypatch):
    module, _ = load_patch(monkeypatch)
    source = "_d.items[0] | _d.items | for item in _d.items"

    result = module.repair_html(source)

    assert result == '_d.get("items")[0] | _d.get("items") | for item in _d.get("items")'


def test_repair_html_is_idempotent(monkeypatch):
    module, _ = load_patch(monkeypatch)
    source = '_d.get("items")[0] | for item in _d.get("items")'

    assert module.repair_html(source) == source


def test_repair_html_rejects_unexpected_template_shape(monkeypatch):
    module, _ = load_patch(monkeypatch)

    with pytest.raises(ValueError, match="Expected 3"):
        module.repair_html("_d.items[0]")


def test_execute_saves_only_the_expected_stock_entry_format(monkeypatch):
    module, frappe = load_patch(monkeypatch)
    doc = Mock(doc_type="Stock Entry", html="_d.items[0] | _d.items | _d.items")
    frappe.db.exists.return_value = True
    frappe.get_doc.return_value = doc

    module.execute()

    assert doc.html.count('_d.get("items")') == 3
    doc.save.assert_called_once_with(ignore_permissions=True)


def test_execute_stops_if_format_doctype_is_unexpected(monkeypatch):
    module, frappe = load_patch(monkeypatch)
    doc = Mock(doc_type="Purchase Receipt", html="_d.items[0] | _d.items | _d.items")
    frappe.db.exists.return_value = True
    frappe.get_doc.return_value = doc

    with pytest.raises(RuntimeError):
        module.execute()

    doc.save.assert_not_called()
