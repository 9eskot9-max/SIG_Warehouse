"""Access and identity checks for the router's existing-document listing."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest


@pytest.fixture
def api(monkeypatch):
    fake = types.ModuleType('frappe')
    fake._ = lambda value: value
    fake.parse_json = json.loads
    fake.whitelist = lambda **kwargs: lambda fn: fn
    fake.session = types.SimpleNamespace(user='finance@example.com')
    fake.PermissionError = PermissionError
    fake.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
    fake.has_permission = lambda doctype, permission: True
    utils = types.ModuleType('frappe.utils')
    utils.flt = float
    utils.now_datetime = lambda: None
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    monkeypatch.setitem(sys.modules, 'frappe.utils', utils)
    path = Path(__file__).parents[1] / 'sig_accounting/snb_movement_router.py'
    spec = importlib.util.spec_from_file_location('router_marked_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Row(dict):
    __getattr__ = dict.__getitem__


def test_permission_filtered_listing_and_bank_identity(api):
    calls = []
    api.frappe.get_list = lambda doctype, **kw: calls.append((doctype, kw)) or [Row(
        name='JV-1', docstatus=0, posting_date='2026-11-09', custom_pc_statement_key='key')]
    result = api.list_marked_documents('Journal Entry', start=3, limit=500)
    assert result['rows'][0]['bank'] == 'UNCONFIRMED'
    assert result['rows'][0]['docstatus'] == 0
    assert calls[0][1]['filters'] == {'custom_pc_statement_key': ['is', 'set']}
    assert calls[0][1]['start'] == 3 and calls[0][1]['page_length'] == 200


def test_missing_document_permission_never_queries(api):
    api.frappe.has_permission = lambda doctype, permission: doctype != 'Payment Entry'
    api.frappe.get_list = lambda *args, **kwargs: pytest.fail('must not query')
    assert api.list_marked_documents('Payment Entry') == {'available': False, 'rows': []}


def test_router_denied_and_type_whitelist(api):
    api.frappe.has_permission = lambda doctype, permission: False
    with pytest.raises(PermissionError):
        api.list_marked_documents('Payment Entry')
    api.frappe.has_permission = lambda doctype, permission: True
    with pytest.raises(ValueError):
        api.list_marked_documents('Employee')


def test_repeat_ingest_preserves_review_and_updates_only_hint(api, monkeypatch):
    owner = types.ModuleType('sig_warehouse.sig_operations.app_connections')
    owner.TODOIST_OWNER = 'finance@example.com'
    monkeypatch.setitem(sys.modules, owner.__name__, owner)
    source = {'event_date':'2026-11-09', 'direction':'DEBIT'}
    name = hashlib.sha256(b'SNB-row').hexdigest()
    class Doc:
        source_key = 'SNB-row'
        source_json = api._json(source)
        erp_hint_json = '{}'
        flags = types.SimpleNamespace()
        review_status = 'REVIEWED'
        def check_permission(self, permission): pass
        def save(self): self.saved = True
    doc = Doc()
    api.frappe.db = types.SimpleNamespace(exists=lambda *args: True, sql=lambda *args: None)
    api.frappe.get_doc = lambda *args: doc
    item = {'id':'SNB-row','source':source,'erp':{'linked_doc':'ACC-JV-1'}}
    assert api.ingest([item]) == [{'id':'SNB-row','status':'HINT_UPDATED','name':name}]
    assert doc.review_status == 'REVIEWED'
    assert json.loads(doc.erp_hint_json)['readback_status'] == 'NEEDS_LIVE_READBACK'
    assert api.ingest([item])[0]['status'] == 'EXISTS'
    item['erp']['linked_doc'] = 'ACC-JV-2'
    assert api.ingest([item])[0]['status'] == 'HINT_CONFLICT'
    item['source'] = {**source, 'direction':'CREDIT'}
    assert api.ingest([item])[0]['status'] == 'SOURCE_CONFLICT'
