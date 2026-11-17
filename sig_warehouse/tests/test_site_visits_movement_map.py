import ast, datetime, sys, types
from pathlib import Path
from types import SimpleNamespace
import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'sig_warehouse' / 'site_visits.py'

@pytest.fixture
def environment(monkeypatch):
    tree = ast.parse(SOURCE.read_text(encoding='utf8'))
    fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'get_movement_map')
    fn.decorator_list = []
    session = lambda **kw: SimpleNamespace(**kw)
    rows = [session(name='S1', site_key='A', employee='E1', start_at=datetime.datetime(2026,11,16,10), status='COMPLETED', posted=1), session(name='S2', site_key='B', employee='E2', start_at=datetime.datetime(2026,11,16,11), status='COMPLETED', posted=1)]
    seen = {}
    def sql(query, values, **kwargs): seen['dates'] = values; return rows
    db = SimpleNamespace(sql=sql, get_values=lambda *a, **k: [session(name='E1',employee_name='Leader'),session(name='E2',employee_name='Visitor')])
    utils = SimpleNamespace(getdate=lambda value: value if isinstance(value, datetime.date) else datetime.date.fromisoformat(value), nowdate=lambda: '2026-11-17', add_months=lambda d,n: datetime.date(d.year+(d.month==12),1 if d.month==12 else d.month+1,1))
    def throw(message, *a): raise ValueError(message)
    frappe = SimpleNamespace(get_roles=lambda: ['Projects User'], db=db, utils=utils, get_list=lambda *a, **k: [session(name='A',site_latitude=24.7,site_longitude=46.7)], throw=throw, PermissionError=PermissionError)
    mod=types.ModuleType('sig_warehouse.sig_warehouse.field_planner_api')
    mod._team_setup=lambda:[{'team_id':'T1','leader':'E1','team':'Leader','leader_periods':[{'employee':'E1','from':'2026-11-01','to':''}]}]
    monkeypatch.setitem(sys.modules,mod.__name__,mod)
    scope={'frappe':frappe,'SITE_VISIT_ROLES':{'Projects User'}}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(SOURCE),'exec'),scope)
    return scope['get_movement_map'],frappe,seen

def test_week_maps_roster_and_preserves_missing_coordinates(environment):
    call, _, seen=environment
    result=call('week','2026-11-17')
    assert (result['start'],result['end'])==('2026-11-16','2026-11-22')
    assert seen['dates']==(datetime.date(2026,11,16),datetime.date(2026,11,23))
    assert result['visits'][0]['team']=='T1' and result['visits'][0]['lat']==24.7
    assert result['visits'][1]['team']=='' and result['visits'][1]['lat'] is None

def test_month_and_invalid_period(environment):
    call, _, _=environment
    result=call('month','2026-11-17')
    assert (result['start'],result['end'])==('2026-11-01','2026-11-30')
    with pytest.raises(ValueError): call('year','2026-11-17')

def test_access_gate(environment):
    call, frappe, _=environment
    frappe.get_roles=lambda: []
    with pytest.raises(ValueError): call('week','2026-11-17')
