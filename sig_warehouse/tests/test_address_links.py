import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    frappe = types.ModuleType("frappe")
    frappe.flags = types.SimpleNamespace()
    frappe.local = types.SimpleNamespace(request=object())
    frappe._ = lambda s: s

    def throw(message, title=None):
        raise RuntimeError(message)

    frappe.throw = throw
    sys.modules["frappe"] = frappe
    spec = importlib.util.spec_from_file_location("address_links", ROOT / "sig_warehouse" / "address_links.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, frappe


class Doc:
    def __init__(self, links, new=True):
        self.links, self._new, self.values = links, new, {}
        self.meta = types.SimpleNamespace(has_field=lambda f: True)

    def get(self, key):
        return self.links if key == "links" else self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def is_new(self):
        return self._new


def link(doctype, name):
    return types.SimpleNamespace(link_doctype=doctype, link_name=name)


def test_new_address_without_party_is_refused_from_the_desk():
    module, _ = _load()
    try:
        module.validate_address(Doc([]))
    except RuntimeError:
        return
    raise AssertionError("expected the address to be refused")


def test_linked_address_passes_and_gets_summary():
    module, _ = _load()
    doc = Doc([link("Customer", "ACME")])
    module.validate_address(doc)
    assert doc.values["custom_linked_party"] == "Customer: ACME"


def test_system_contexts_and_existing_addresses_are_not_blocked():
    module, frappe = _load()
    module.validate_address(Doc([], new=False))
    frappe.flags.in_import = True
    module.validate_address(Doc([]))
    frappe.flags.in_import = False
    frappe.local.request = None
    module.validate_address(Doc([]))
