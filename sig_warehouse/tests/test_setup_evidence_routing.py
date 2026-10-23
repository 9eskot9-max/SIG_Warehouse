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
    exec(compile(patch.rewrite(source), '<reviewed resolver>', 'exec'), namespace)

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
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
             node.name in ('_effective_default_contact', 'save_po_setup')]
    for node in nodes:
        node.decorator_list = []
    namespace = {'frappe': fake, 'json': json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def test_existing_assignment_supplies_missing_project_field():
    fake = SimpleNamespace(get_all=lambda *a, **k: [SimpleNamespace(tawal_contact='CONTACT')])
    assert setup_functions(fake)['_effective_default_contact']('PROJECT', '') == 'CONTACT'


def test_conflicting_native_defaults_are_reported():
    def throw(message):
        raise ValueError(message)
    fake = SimpleNamespace(get_all=lambda *a, **k: [SimpleNamespace(tawal_contact='CONTACT')], throw=throw)
    with pytest.raises(ValueError, match='disagree'):
        setup_functions(fake)['_effective_default_contact']('PROJECT', 'OTHER')


@pytest.mark.parametrize('alias', ['', 'CSV label'])
def test_unrelated_save_preserves_inactive_default_and_assignments(alias):
    writes = []
    def unexpected_query(*args, **kwargs):
        raise AssertionError('Unchanged contact must not rewrite assignments')
    def throw(message):
        raise ValueError(message)
    fake = SimpleNamespace(db=SimpleNamespace(set_value=lambda *a: writes.append(a)),
                           get_all=unexpected_query, throw=throw)
    namespace = setup_functions(fake)
    state = {'projects': [{'project': 'P', 'csv_alias': '', 'default_contact': 'RETIRED'}],
             'contacts': [], 'hash': 'HASH'}
    namespace.update(_require=lambda **k: None, _state=lambda **k: (SimpleNamespace(revision=8), {}),
                     is_legacy=lambda d: False, _validated=lambda d: d, _po_setup_state=lambda d: state)
    namespace['save_po_setup']([{'project': 'P', 'csv_alias': alias, 'default_contact': 'RETIRED'}], 8, 'HASH')
    assert writes == ([('Project', 'P', {'custom_excel_csv_alias': alias})] if alias else [])
