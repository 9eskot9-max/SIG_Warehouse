import ast
from pathlib import Path
from types import SimpleNamespace
import pytest

PATH = Path(__file__).parents[1] / 'sig_warehouse/patches/v1_0/pr_owner_submit_limit.py'
tree = ast.parse(PATH.read_text(encoding='utf-8-sig'))
script = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCRIPT' for t in n.targets)))

def run(user, lines):
    def fail(msg): raise PermissionError(msg)
    frappe = SimpleNamespace(session=SimpleNamespace(user=user), throw=fail)
    exec(script, {'frappe': frappe, 'doc': SimpleNamespace(items=[SimpleNamespace(**line) for line in lines])})

def test_limit_applies_only_above_20000_for_no_po():
    run('tahir', [{'purchase_order': None, 'qty': 1, 'rate': 20000}])
    with pytest.raises(PermissionError): run('tahir', [{'purchase_order': None, 'qty': 1, 'rate': 20001}])
    run('tahir', [{'purchase_order': 'PO-1', 'qty': 1, 'rate': 20001}])

def test_only_explicit_owner_logins_may_exceed_limit():
    lines = [{'purchase_order': None, 'qty': 2, 'rate': 10001}]
    for user in ('Administrator','9eskot9@gmail.com'): run(user, lines)
    for user in ('tahir','m.ramzan@sigtele.com','other-system-manager'):
        with pytest.raises(PermissionError): run(user, lines)


def test_patch_changes_only_unchanged_live_script_and_is_repeatable(monkeypatch):
    import importlib.util
    import sys
    import types
    import hashlib
    doc = SimpleNamespace(script_type='DocType Event', reference_doctype='Purchase Receipt',
                          disabled=0, doctype_event='Before Validate', script='prior script')
    saves=[]
    doc.save=lambda **kwargs: saves.append(kwargs)
    fake=types.ModuleType('frappe');fake.db=SimpleNamespace(exists=lambda *args: True)
    fake.get_doc=lambda *args: doc
    fake.throw=lambda msg: (_ for _ in ()).throw(ValueError(msg))
    fake.clear_cache=lambda **kwargs: None
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    spec=importlib.util.spec_from_file_location('pr_patch_test',PATH);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.PRIOR_SHA256=hashlib.sha256(b'prior script').hexdigest()
    mod.execute();mod.execute()
    assert doc.doctype_event=='Before Submit' and doc.script==mod.SCRIPT and len(saves)==1
    doc.doctype_event='Before Validate';doc.script='changed concurrently'
    with pytest.raises(ValueError): mod.execute()


def test_permission_patch_preserves_existing_rows_and_is_repeatable(monkeypatch):
    import importlib.util, sys, types
    class Row(dict):
        __getattr__ = dict.__getitem__
    baseline=Row(name='existing',role='Stock Manager',permlevel=0,if_owner=0,read=1,write=1,create=1,submit=1)
    rows=[baseline]
    before=dict(baseline)
    fake=types.ModuleType('frappe');fake.db=SimpleNamespace(exists=lambda *args: True)
    fake.get_all=lambda *args,**kwargs: rows[:]
    def get_doc(values):
        d=Row(values);d.name='new-'+d.role
        return SimpleNamespace(insert=lambda **kwargs: rows.append(d))
    fake.get_doc=get_doc;fake.throw=lambda message: (_ for _ in ()).throw(ValueError(message))
    fake.clear_cache=lambda **kwargs: None
    monkeypatch.setitem(sys.modules,'frappe',fake)
    path=PATH.parent/'pr_po_issuer_draft_access.py'
    spec=importlib.util.spec_from_file_location('pr_access_test',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.execute();mod.execute()
    assert dict(baseline)==before and len(rows)==4
    for row in rows[1:]:
        assert (row['read'],row['write'],row['create'],row['submit'])==(1,1,1,0)
    rows[1]['submit']=1
    with pytest.raises(ValueError):mod.execute()
