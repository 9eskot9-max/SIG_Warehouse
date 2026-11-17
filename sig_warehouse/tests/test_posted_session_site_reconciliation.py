import ast
from pathlib import Path
from types import SimpleNamespace
import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'sig_warehouse' / 'site_visits.py'

class Denied(Exception):
    pass

class Record(SimpleNamespace):
    def save(self, **kwargs):
        self.saved = True
    def add_comment(self, *args, **kwargs):
        self.commented = True

@pytest.fixture
def repair():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'reconcile_posted_session_site')
    fn.decorator_list = []
    session = Record(modified='2026-11-17 01:00:00', posted=1, visit='V1', site=None, site_key='ZMC296', employee='E1', diagnostics='UNRESOLVED_SITE,HARD_CAP_24H')
    visit = Record(site='ZMC296', site_key='ZMC296', employee='E1')
    db = SimpleNamespace(sql=lambda *a, **k: None, exists=lambda *a: True, get_value=lambda *a, **k: visit)
    def deny(message, *args):
        raise Denied(message)
    frappe = SimpleNamespace(session=SimpleNamespace(user='Administrator'), db=db, get_doc=lambda *a: session, throw=deny, _=lambda s: s, PermissionError=Denied)
    scope = {'frappe': frappe, 'text_value': lambda v: '' if v is None else str(v)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(SOURCE), 'exec'), scope)
    return scope['reconcile_posted_session_site'], session, visit, frappe

def test_reconciles_only_site_diagnostic_and_preserves_posted(repair):
    run, session, _, _ = repair
    assert run('S1', '2026-11-17 01:00:00')['result'] == 'ok'
    assert (session.site, session.diagnostics, session.posted, session.visit) == ('ZMC296', 'HARD_CAP_24H', 1, 'V1')
    assert session.saved and session.commented

@pytest.mark.parametrize('case', ['non_admin','changed','not_posted','linked','missing_flag','different_site','different_employee','missing_site'])
def test_rejects_unsafe_cases(repair, case):
    run, session, visit, frappe = repair
    expected = '2026-11-17 01:00:00'
    if case == 'non_admin': frappe.session.user = 'someone@example.com'
    elif case == 'changed': expected = 'stale'
    elif case == 'not_posted': session.posted = 0
    elif case == 'linked': session.site = 'ZMC296'
    elif case == 'missing_flag': session.diagnostics = ''
    elif case == 'different_site': visit.site = 'OTHER'
    elif case == 'different_employee': visit.employee = 'OTHER'
    elif case == 'missing_site': frappe.db.exists = lambda *a: False
    with pytest.raises(Denied): run('S1', expected)
    assert not getattr(session, 'saved', False)
