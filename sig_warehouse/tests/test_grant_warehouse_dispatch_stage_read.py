import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

path = Path(__file__).resolve().parents[1] / 'sig_warehouse/patches/v1_0/grant_warehouse_dispatch_stage_read.py'
spec = importlib.util.spec_from_file_location('dispatch_access_patch', path)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class FakeFrappe:
    def __init__(self, rows):
        self.rows = rows
        self.db = self
        self.inserted = []
        self.changed = []

    def get_meta(self, _):
        return SimpleNamespace(get_field=lambda _: SimpleNamespace(permlevel=1, read_only=1))

    def exists(self, *_):
        return True

    def get_all(self, *_args, **_kwargs):
        return self.rows

    def throw(self, message):
        raise ValueError(message)

    def get_doc(self, data):
        return SimpleNamespace(insert=lambda **_: self.inserted.append(data))

    def set_value(self, *args, **kwargs):
        self.changed.append((args, kwargs))

    def clear_cache(self, **_):
        pass


def test_adds_only_level_one_read_and_preserves_matrix(monkeypatch):
    rows = [{'name': 'baseline', 'role': 'Stock User', 'permlevel': 0, 'if_owner': 0, 'read': 1}]
    fake = FakeFrappe(rows)
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    patch.execute()
    row = fake.inserted[0]
    assert row['role'] == 'Warehouse Manager' and row['permlevel'] == 1 and row['read'] == 1
    assert all(row[p] == 0 for p in patch.PTYPES if p != 'read')
    assert rows == [{'name': 'baseline', 'role': 'Stock User', 'permlevel': 0, 'if_owner': 0, 'read': 1}]
    fake.rows.append({'name': 'added', 'role': 'Warehouse Manager', 'permlevel': 1, 'if_owner': 0, 'read': 1})
    patch.execute()
    assert len(fake.inserted) == 1 and fake.changed == []


def test_refuses_first_custom_row(monkeypatch):
    fake = FakeFrappe([])
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    with pytest.raises(ValueError, match='no Custom DocPerm baseline'):
        patch.execute()
    assert fake.inserted == []

