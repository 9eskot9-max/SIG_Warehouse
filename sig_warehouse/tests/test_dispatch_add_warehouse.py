import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).parents[1] / 'sig_warehouse' / 'dispatch_operation.py'


def load_endpoint(fake, authorize):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_mr_source_context')
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'sig_add_mr_line')
    fn.decorator_list = []
    scope = {'frappe': fake, '_authorize': authorize, 'WH_MAP': {'Ry': 'selected'},
             'rollup': SimpleNamespace(recompute_mr_dispatch_state=lambda mr: {})}
    exec(compile(ast.Module(body=[helper, fn], type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['sig_add_mr_line']


def fake_frappe(header, items=None):
    inserted = []
    class Row:
        name = 'new-line'
        def __init__(self, values): self.values = values
        def insert(self, **kwargs): inserted.append(self.values)
    mr = SimpleNamespace(docstatus=1, material_request_type='Material Issue', set_warehouse=header, items=items or [],
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


def test_added_line_inherits_unambiguous_project_and_alias():
    fake, inserted = fake_frappe(None, [
        {'project': 'WO-2026-0037', 'custom_source_project_name': 'Capex9'},
        {'project': 'WO-2026-0037', 'custom_source_project_name': 'capex9'},
    ])
    result = load_endpoint(fake, lambda mr, wh: None)('MR', 'item', 35, from_wh='selected')
    assert result['result'] == 'created'
    assert inserted[0]['project'] == 'WO-2026-0037'
    assert inserted[0]['custom_source_project_name'] == 'Capex9'


@pytest.mark.parametrize('items,reason', [
    ([{'project': 'A'}, {'project': 'B'}], 'AMBIGUOUS_MR_PROJECT'),
    ([{'project': 'A', 'custom_source_project_name': 'Capex9'},
      {'project': 'A', 'custom_source_project_name': 'Other'}], 'AMBIGUOUS_MR_ALIAS'),
])
def test_ambiguous_context_is_not_guessed(items, reason):
    fake, inserted = fake_frappe(None, items)
    result = load_endpoint(fake, lambda mr, wh: None)('MR', 'item', 1, from_wh='selected')
    assert result['reason'] == reason
    assert not inserted


def test_notification_recovers_unambiguous_alias_for_existing_blank_line(monkeypatch):
    import sys
    import types
    fake, _ = fake_frappe(None)
    fake.db.exists = lambda *args: args[0] == 'DocType' and args[1] == 'Maytapi Settings'
    fake.db.get_value = lambda dt, name, field, **kw: (
        {'parent': 'MR-26-1190', 'custom_source_project_name': None}
        if dt == 'Material Request Item' else '10001274')
    fake.get_single = lambda name: SimpleNamespace(enabled=1, dispatch_notify_enabled=1,
        dispatch_recipients=[SimpleNamespace(project_prefix='capex', recipient='group')])
    fake.get_all = lambda dt, **kwargs: [
        {'project': 'WO-2026-0037', 'custom_source_project_name': 'Capex9'},
        {'project': None, 'custom_source_project_name': None},
    ]
    sent = []
    module = types.ModuleType('sig_whatsapp.maytapi')
    module._audit = lambda *args, **kwargs: None
    module.send_document = lambda dt, name, to: sent.append((dt, name, to)) or {'status': 'QUEUED'}
    package = types.ModuleType('sig_whatsapp')
    package.maytapi = module
    monkeypatch.setitem(sys.modules, 'sig_whatsapp', package)
    monkeypatch.setitem(sys.modules, 'sig_whatsapp.maytapi', module)
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('_mr_source_context', '_notify_dispatch_whatsapp')]
    scope = {'frappe': fake}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), 'exec'), scope)
    result = scope['_notify_dispatch_whatsapp']([{'mri': 'new'}], 'STE')
    assert result['sent'] and result['alias'] == 'Capex9' and result['route'] == 'legacy_prefix'
    assert sent == [('Stock Entry', 'STE', 'group')]
    fake.get_all = lambda dt, **kwargs: [
        {'project': 'A', 'custom_source_project_name': 'Capex9'},
        {'project': 'B', 'custom_source_project_name': 'Other'},
    ]
    result = scope['_notify_dispatch_whatsapp']([{'mri': 'new'}], 'STE2')
    assert not result['sent'] and 'AMBIGUOUS' in result['reason']
    assert len(sent) == 1
