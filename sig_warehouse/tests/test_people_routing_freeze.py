import importlib
import sys
import types

import pytest


class Denied(Exception):
    pass


def test_publish_is_blocked_even_for_system_manager(monkeypatch):
    fake = types.ModuleType('frappe')
    fake.whitelist = lambda **kwargs: lambda fn: fn
    fake._ = lambda text: text
    fake.PermissionError = Denied
    fake.session = types.SimpleNamespace(user='admin@example.com')
    fake.get_roles = lambda: ['System Manager']
    fake.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or RuntimeError)(message))
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    routing = types.ModuleType('sig_warehouse.sig_warehouse.pc_review_routing')
    routing.load_matrix = lambda: (_ for _ in ()).throw(AssertionError('publish must not load or write the matrix'))
    monkeypatch.setitem(sys.modules, routing.__name__, routing)
    module = importlib.import_module('sig_warehouse.sig_operations.people_routing')
    sys.modules.pop('sig_warehouse.sig_operations.people_routing', None)
    monkeypatch.setattr(module, 'frappe', fake)
    with pytest.raises(Denied, match='temporarily read-only'):
        module.publish('[]', 1, '{}')
