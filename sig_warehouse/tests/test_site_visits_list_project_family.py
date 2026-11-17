import ast
import datetime
from pathlib import Path
from types import SimpleNamespace


SOURCE = Path(__file__).resolve().parents[1] / 'sig_warehouse' / 'site_visits.py'


def _load_get_visits(session):
    tree = ast.parse(SOURCE.read_text(encoding='utf8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {'get_visits', '_family_key'}]
    for node in functions:
        node.decorator_list = []
    cycles = [
        SimpleNamespace(name='C1', site_key='SITE-1', project='Basic', erp_project='PROJECT-1',
                        stage='Invoicing', wo='', po='', is_temporary=0),
        SimpleNamespace(name='C2', site_key='SITE-1', project='Capex', erp_project='',
                        stage='Plan', wo='', po='', is_temporary=0),
    ]

    def sql(query, values, **kwargs):
        if 'tabSIG Field Session' in query:
            return [session]
        if 'tabSIG Field Visit' in query:
            return [SimpleNamespace(name='VISIT-1', cycle='C1')] if session.visit else []
        if 'tabSIG Site Cycle' in query:
            return cycles
        raise AssertionError(query)

    class ProjectMeta:
        @staticmethod
        def has_field(field):
            return field in {'custom_project_family', 'custom_family'}

    db = SimpleNamespace(sql=sql, get_values=lambda *a, **k: [SimpleNamespace(name='EMP-1', employee_name='Test Person')],
                         get_value=lambda *a, **k: {'custom_project_family': 'Colocation',
                                                   'custom_family': '5G / Colocation'})
    utils = SimpleNamespace(nowdate=lambda: '2026-11-17', getdate=lambda value: datetime.date.fromisoformat(value),
                             add_days=lambda value, days: (datetime.date.fromisoformat(value) + datetime.timedelta(days=days)).isoformat())
    frappe = SimpleNamespace(session=SimpleNamespace(user='test@example.com'), get_roles=lambda user: ['Projects User'],
                             db=db, utils=utils, has_permission=lambda *a, **k: True,
                             get_meta=lambda doctype: ProjectMeta())
    scope = {'frappe': frappe, 'SITE_VISIT_ROLES': {'Projects User'}, 'STREAM_LABEL': {}, 'STREAM_PM': {},
             'normalize_family': lambda value: 'Colocation' if str(value).lower() in {'colocation', '5g / colocation'} else '',
             'resolve_project_family': lambda project: {'family': 'Colocation', 'conflict': False},
             'text_value': lambda value: '' if value is None else str(value)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])), str(SOURCE), 'exec'), scope)
    return scope['get_visits']


def _session(visit):
    return SimpleNamespace(name='SESSION-1', stream='ti5g', site_key='SITE-1', site='SITE-1', reporter='phone',
                           reporter_name='Raw WhatsApp Name', employee='EMP-1',
                           start_at=datetime.datetime(2026, 11, 17, 12), end_at=datetime.datetime(2026, 11, 17, 12, 10),
                           status='COMPLETED', hours=1 / 6, activity_code='UNSPECIFIED', photo_count=3,
                           diagnostics='', disposition='PENDING', posted=1 if visit else 0, visit=visit)


def test_list_uses_the_actual_linked_cycle_family_when_site_has_multiple_cycles():
    result = _load_get_visits(_session('VISIT-1'))()
    assert result['rows'][0]['cycle']['name'] == 'C1'
    assert result['rows'][0]['project_family'] == 'Colocation'


def test_unlinked_visit_does_not_guess_between_multiple_site_cycles():
    result = _load_get_visits(_session(None))()
    assert result['rows'][0]['cycle'] is None
    assert result['rows'][0]['project_family'] == ''
