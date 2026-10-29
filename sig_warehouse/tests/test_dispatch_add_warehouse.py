import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).parents[1] / 'sig_warehouse' / 'dispatch_operation.py'


def load_endpoint(fake, authorize):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'sig_add_mr_line')
    fn.decorator_list = []
    scope = {'frappe': fake, '_authorize': authorize, 'WH_MAP': {'Ry': 'selected'},
             'rollup': SimpleNamespace(recompute_mr_dispatch_state=lambda mr: {})}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['sig_add_mr_line']


def fake_frappe(header):
    inserted = []
    class Row:
        name = 'new-line'
        def __init__(self, values): self.values = values
        def insert(self, **kwargs): inserted.append(self.values)
    mr = SimpleNamespace(docstatus=1, material_request_type='Material Issue', set_warehouse=header,
                         get=lambda name: None)
    item = SimpleNamespace(stock_uom='Nos', uoms=[])
    def get_doc(doctype, name=None):
        if isinstance(doctype, dict): return Row(doctype)
        return mr if doctype == 'Material Request' else item
    db = SimpleNamespace(exists=lambda *args: True, sql=lambda *args: [(0,)], commit=lambda: None)
    return SimpleNamespace(get_doc=get_doc, db=db, utils=SimpleNamespace(nowdate=lambda: '2026-10-29'),
                           clear_document_cache=lambda *args: None), inserted


def test_selected_warehouse_is_authorized_and_written_when_header_empty():
    fake, inserted = fake_frappe(None)
    authorized = []
    endpoint = load_endpoint(fake, lambda mr, wh: authorized.append(wh))
    assert endpoint('MR-26-1190', 'E-DC-CAB-10', 35, from_wh='Ry')['result'] == 'created'
    assert authorized == ['selected']
    assert inserted[0]['warehouse'] == 'selected'


def test_legacy_caller_uses_header_and_missing_warehouse_fails():
    fake, inserted = fake_frappe('header')
    endpoint = load_endpoint(fake, lambda mr, wh: None)
    assert endpoint('MR', 'item', 1)['result'] == 'created'
    assert inserted[0]['warehouse'] == 'header'
    fake, inserted = fake_frappe(None)
    assert load_endpoint(fake, lambda mr, wh: None)('MR', 'item', 1)['reason'] == 'MR has no warehouse set'
    assert not inserted


def test_denied_warehouse_does_not_insert():
    fake, inserted = fake_frappe(None)
    def deny(mr, wh): raise PermissionError(wh)
    with pytest.raises(PermissionError, match='selected'):
        load_endpoint(fake, deny)('MR', 'item', 1, from_wh='selected')
    assert not inserted
