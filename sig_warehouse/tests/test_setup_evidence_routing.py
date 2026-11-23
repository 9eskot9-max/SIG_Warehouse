"""Offline routing scenarios, including Frappe's dictionary-shaped safe metadata."""
import importlib.util
import ast
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def route(monkeypatch):
    fake = ModuleType('frappe')
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    path = Path(__file__).resolve().parents[1] / 'sig_warehouse/patches/v1_0/align_site_po_wo_evidence.py'
    spec = importlib.util.spec_from_file_location('routing_review', path)
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    source = '''def select_cycle(wo, po, event_code, project):
    sk = 'SITE'
    open_rows = frappe.get_all('SIG Site Cycle', filters={'site_key': sk, 'terminal': 0},
                               fields=['name', 'wo', 'po', 'resolution_state'], order_by='modified desc', limit_page_length=100)
    blank_open = [r for r in open_rows if not r.wo]
    real_open = [r for r in open_rows if r.wo]
    cyc = None
    resolution = ''
    closed_exact_scope = False
    if False:
        pass
    elif wo:
        pass
    created_cycle = 0
    return {'cycle': cyc, 'resolution': resolution}
'''
    namespace = {'frappe': fake}
    update_path = path.with_name('allow_visit_new_cycle.py')
    update_spec = importlib.util.spec_from_file_location('visit_cycle_patch', update_path)
    update = importlib.util.module_from_spec(update_spec)
    update_spec.loader.exec_module(update)
    revert_path = path.with_name('record_visit_without_cycle.py')
    revert_spec = importlib.util.spec_from_file_location('visit_unallocated_patch', revert_path)
    revert = importlib.util.module_from_spec(revert_spec)
    revert_spec.loader.exec_module(revert)
    # Migration order: align -> allow_visit_new_cycle -> record_visit_without_cycle.
    exec(compile(revert.rewrite(update.rewrite(patch.rewrite(source))), '<reviewed resolver>', 'exec'), namespace)

    def run(rows, event='TCN_GENERATED', po='PO1', wo='', project='Capex'):
        cycles = [SimpleNamespace(site_key='SITE', terminal=0, resolution_state='',
                                  project='Capex', erp_project='ERP-P', **r) for r in rows]
        def matching(filters):
            return [r for r in cycles if all(getattr(r, k) == v for k, v in filters.items())]
        fake.get_all = lambda dt, filters, **kwargs: matching(filters)
        fake.db = SimpleNamespace(exists=lambda dt, filters: bool(matching(filters)),
                                  get_value=lambda *args: 'Capex')
        # Server Scripts receive a dict, not a Meta object with has_field().
        fake.get_meta = lambda dt: {'fields': [{'fieldname': 'custom_family'}]}
        fake.response = {}
        result = namespace['select_cycle'](wo, po, event, project)
        return result, fake.response.get('message')
    return run


def test_first_boq_can_start_new_cycle(route):
    result, error = route([], event='BOQ_GENERATED')
    assert result['cycle'] is None and error is None


def test_boq_cannot_fall_back_to_another_po(route):
    result, error = route([dict(name='other', po='PO2', wo='WO-A')], event='BOQ_GENERATED')
    assert result['cycle'] is None and error is None


def test_visit_uses_safe_metadata_dictionary(route):
    result, error = route([dict(name='one', po='PO1', wo='WO-A')],
                          event='FIELD_VISIT_COMPLETED', po='')
    assert result['cycle'] == 'one' and error is None


def test_visit_with_multiple_pos_stays_for_review(route):
    result, error = route([dict(name='one', po='PO1', wo='WO-A'),
                           dict(name='two', po='PO2', wo='WO-B')],
                          event='FIELD_VISIT_COMPLETED', po='')
    assert result is None and error['result'] == 'exception'


def test_visit_without_open_cycle_does_not_create_a_cycle(route):
    # The feed records this visit without a cycle (field_feed._record_unallocated).
    result, error = route([], event='FIELD_VISIT_COMPLETED', po='', project='5g')
    assert result is None and 'no compatible' in error['reason']


def test_visit_does_not_create_when_an_incompatible_open_cycle_exists(route):
    result, error = route([dict(name='other', po='PO1', wo='WO-A')],
                          event='FIELD_VISIT_COMPLETED', po='', project='5g')
    assert result is None and 'no compatible' in error['reason']


def test_non_visit_without_open_cycle_remains_review(route):
    result, error = route([], event='TCN_GENERATED', po='', project='5g')
    assert result is None and 'no compatible' in error['reason']


def test_visit_cycle_patch_is_repeatable_and_rejects_unknown_source(monkeypatch):
    fake = ModuleType('frappe')
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    path = Path(__file__).resolve().parents[1] / 'sig_warehouse/patches/v1_0/allow_visit_new_cycle.py'
    spec = importlib.util.spec_from_file_location('cycle_patch_test', path)
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    changed = patch.rewrite('before\n' + patch.OLD + ' after')
    assert patch.rewrite(changed) == changed
    with pytest.raises(ValueError):
        patch.rewrite('unexpected writer')


def test_shared_preparation_accepts_one_same_po_target(route):
    result, error = route([dict(name='one', po='PO1', wo='WO-A'),
                           dict(name='two', po='PO1', wo='WO-B')])
    assert result['cycle'] == 'one' and error is None


def test_financial_event_does_not_choose_a_sibling_wo(route):
    result, error = route([dict(name='one', po='PO1', wo='WO-A')], event='GCL_GENERATED')
    assert result is None and error['result'] == 'exception'


def test_unknown_wo_without_po_does_not_create_scope(route):
    result, error = route([], po='', wo='WO-A')
    assert result is None and error['result'] == 'exception'


def test_exact_wo_honours_supplied_po(route):
    result, error = route([dict(name='wrong', po='PO2', wo='WO-A')], wo='WO-A')
    assert result['cycle'] is None and error is None


def test_duplicate_exact_cycles_need_explicit_selection(route):
    result, error = route([dict(name='one', po='PO1', wo='WO-A'),
                           dict(name='two', po='PO1', wo='WO-A')], wo='WO-A')
    assert result is None and error['result'] == 'exception'


def setup_functions(fake):
    path = Path(__file__).resolve().parents[1] / 'sig_operations/excel_setup_v3.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'save_po_setup']
    for node in nodes:
        node.decorator_list = []
    namespace = {'frappe': fake, 'json': json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def label_saver(writes, projects=('P',)):
    def throw(message):
        raise ValueError(message)
    fake = SimpleNamespace(db=SimpleNamespace(set_value=lambda *a: writes.append(a)), throw=throw)
    namespace = setup_functions(fake)
    state = {'projects': [{'project': p, 'csv_alias': 'OLD'} for p in projects], 'contacts': [], 'hash': 'HASH'}
    namespace.update(_require=lambda **k: None, _state=lambda **k: (SimpleNamespace(revision=8), {}),
                     _validated_v3=lambda d, w: d, _po_setup_state=lambda d: state)
    return namespace


def test_only_a_changed_csv_label_is_written():
    writes = []
    save = label_saver(writes)['save_po_setup']
    save([{'project': 'P', 'csv_alias': 'OLD'}], 8, 'HASH')
    assert writes == []
    save([{'project': 'P', 'csv_alias': 'NEW'}], 8, 'HASH')
    assert writes == [('Project', 'P', {'custom_excel_csv_alias': 'NEW'})]


def test_label_save_rejects_stale_incomplete_unknown_or_oversized_submissions():
    writes = []
    save = label_saver(writes, projects=('P', 'Q'))['save_po_setup']
    with pytest.raises(ValueError, match='another session'):
        save([], 7, 'HASH')
    with pytest.raises(ValueError, match='changed in another session'):
        save([], 8, 'OTHER')
    with pytest.raises(ValueError, match='complete visible Project list'):
        save([{'project': 'P', 'csv_alias': 'X'}], 8, 'HASH')
    with pytest.raises(ValueError, match='invalid'):
        save([{'project': 'P', 'csv_alias': 'X'}, {'project': 'ZZ', 'csv_alias': 'X'}], 8, 'HASH')
    with pytest.raises(ValueError, match='invalid'):
        save([{'project': 'P', 'csv_alias': 'X' * 141}, {'project': 'Q', 'csv_alias': ''}], 8, 'HASH')
    assert writes == []
