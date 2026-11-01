import importlib.util
import sys
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / 'sig_warehouse/patches/v1_0/reconcile_v16_hr_default_exports.py'
spec = importlib.util.spec_from_file_location('hr_export_patch', path)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class FakeFrappe:
    def __init__(self):
        self.db = self
        self.writes = []
        self.rows = {}
        for dt, roles in patch.ROLES.items():
            self.rows[dt] = []
            for role in roles:
                rights = patch.expected_rights(dt)
                self.rows[dt].append({'name': dt + role, 'role': role, 'permlevel': 0, 'if_owner': 0,
                                      **{p: int(p in rights or p == 'export') for p in patch.PTYPES}})

    def get_all(self, _doctype, filters, fields):
        return self.rows[filters['parent']]

    def set_value(self, _doctype, name, field, value, **_kwargs):
        assert field == 'export' and value == 0
        self.writes.append(name)
        for rows in self.rows.values():
            for row in rows:
                if row['name'] == name:
                    row[field] = value

    def clear_cache(self, **_):
        pass

    def throw(self, message):
        raise ValueError(message)


def test_removes_only_default_exports_and_is_repeatable(monkeypatch):
    fake = FakeFrappe()
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    patch.execute()
    assert len(fake.writes) == 9
    for dt, rows in fake.rows.items():
        for row in rows:
            assert row['export'] == 0
            assert {p for p in patch.PTYPES if p != 'export' and row[p]} == patch.expected_rights(dt)
    patch.execute()
    assert len(fake.writes) == 9


def test_preflights_all_rows_before_writing(monkeypatch):
    fake = FakeFrappe()
    fake.rows['Email Account'][0]['write'] = 1
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    with pytest.raises(ValueError, match='Unexpected HR Manager permission matrix'):
        patch.execute()
    assert fake.writes == []


def test_refuses_missing_custom_matrix(monkeypatch):
    fake = FakeFrappe()
    fake.rows['Task'] = []
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    with pytest.raises(ValueError, match='no custom permission matrix'):
        patch.execute()
    assert fake.writes == []
