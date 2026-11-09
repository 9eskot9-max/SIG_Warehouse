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
        recognition_json = '{}'
        account_scope_hash = ''
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


def test_repeat_ingest_adds_account_fingerprint_without_changing_source(api, monkeypatch):
    owner = types.ModuleType('sig_warehouse.sig_operations.app_connections')
    owner.TODOIST_OWNER = 'finance@example.com'
    monkeypatch.setitem(sys.modules, owner.__name__, owner)
    source = {'event_date':'2026-11-09', 'direction':'CREDIT'}
    name = hashlib.sha256(b'SNB-row').hexdigest()
    class Doc:
        source_key = 'SNB-row'
        source_json = api._json(source)
        recognition_json = '{}'
        erp_hint_json = '{}'
        account_scope_hash = ''
        flags = types.SimpleNamespace()
        def check_permission(self, permission): pass
        def save(self): self.saved = True
    doc=Doc()
    api.frappe.db = types.SimpleNamespace(exists=lambda *args: True, sql=lambda *args: None)
    api.frappe.get_doc = lambda *args: doc
    scope=hashlib.sha256(b'00000000000001').hexdigest()
    result=api.ingest([{'id':'SNB-row','source':source,'account_scope_hash':scope}])
    assert result == [{'id':'SNB-row','status':'ACCOUNT_SCOPE_UPDATED','name':name}]
    assert doc.account_scope_hash == scope
    assert doc.source_json == api._json(source)
    assert doc.saved


def test_readback_requires_unique_visible_marker_matching_bank_and_amount(api):
    scope=next(iter(api.SNB_BANK_GL_BY_SCOPE))
    bank_number=api.SNB_BANK_GL_BY_SCOPE[scope]
    source={'bank':'SNB','statement_key':'statement-1','direction':'DEBIT','signed_amount':-100,'currency':'SAR','reference':'ref-1'}
    class Doc:
        def __init__(self, doctype, name, **values):
            self.doctype=doctype; self.name=name; self.__dict__.update(values)
        def get(self, key): return getattr(self,key,None)
        def check_permission(self, permission): pass
    movement=Doc(api.DOCTYPE,'movement-1',source_json=api._json(source),erp_hint_json=api._json({'linked_doc':'PAY-1'}),
        account_scope_hash=scope,direction='DEBIT',amount=-100,currency='SAR')
    payment=Doc('Payment Entry','PAY-1',payment_type='Pay',paid_from='BANK-GL',paid_amount=100,
        paid_from_account_currency='SAR',reference_no='ref-1',company='SIG',docstatus=1)
    account=Doc('Account','BANK-GL',account_number=bank_number,company='SIG')
    lookup={(api.DOCTYPE,'movement-1'):movement,('Payment Entry','PAY-1'):payment,('Account','BANK-GL'):account}
    api.frappe.get_doc=lambda doctype,name:lookup[(doctype,name)]
    api.frappe.db=types.SimpleNamespace(count=lambda doctype,filters: 1 if doctype=='Payment Entry' else 0)
    api.frappe.get_list=lambda doctype,**kwargs: [Row(name='PAY-1')] if doctype=='Payment Entry' else []
    result=api.readback_movements(['movement-1'])[0]
    assert result['status']=='POSTED' and result['documents'][0]['name']=='PAY-1'
    payment.paid_amount=101
    assert api.readback_movements(['movement-1'])[0]['status']=='UNKNOWN'
    payment.paid_amount=100; payment.docstatus=2
    assert api.readback_movements(['movement-1'])[0]['status']=='CANCELLED'
    payment.docstatus=1
    second=Doc('Payment Entry','PAY-2',payment_type='Pay',paid_from='BANK-GL',paid_amount=100,
        paid_from_account_currency='SAR',reference_no='ref-1',company='SIG',docstatus=0)
    lookup[('Payment Entry','PAY-2')]=second
    api.frappe.db.count=lambda doctype,filters: 2 if doctype=='Payment Entry' else 0
    api.frappe.get_list=lambda doctype,**kwargs: [Row(name='PAY-1'),Row(name='PAY-2')] if doctype=='Payment Entry' else []
    mixed=api.readback_movements(['movement-1'])[0]
    assert mixed['status']=='AMBIGUOUS' and {doc['status'] for doc in mixed['documents']}=={'POSTED','DRAFT'}
    api.frappe.db.count=lambda doctype,filters: 1 if doctype=='Payment Entry' else 0
    api.frappe.get_list=lambda *args,**kwargs: []
    assert api.readback_movements(['movement-1'])[0]['status']=='UNAVAILABLE'


def test_journal_bank_line_must_match_direction_currency_and_gl(api):
    class Doc(dict):
        __getattr__ = dict.__getitem__
        def check_permission(self, permission): pass
    bank=Doc(account_number='13121',company='SIG')
    api.frappe.get_doc=lambda doctype,name: bank
    movement=Doc(amount=-1.15,currency='SAR',direction='DEBIT')
    source={'direction':'DEBIT','currency':'SAR'}
    journal=Doc(doctype='Journal Entry',company='SIG',accounts=[Doc(account='BANK',account_currency='SAR',
        credit_in_account_currency=1.15,debit_in_account_currency=0)])
    assert api._document_matches_movement(journal,movement,source,'13121')
    assert not api._document_matches_movement(journal,movement,source,'13123')
    assert not api._document_matches_movement(journal,movement,{**source,'direction':'CREDIT'},'13121')
