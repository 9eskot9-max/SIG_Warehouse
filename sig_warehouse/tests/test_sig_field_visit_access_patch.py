"""The full SIG Field Visit Custom DocPerm repair is safe and repeatable."""
import importlib.util
import pathlib
import sys
import types

import pytest


PATCH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "sig_warehouse" / "patches" / "v1_0" / "restore_sig_field_visit_access.py"
)
PTYPES = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)


class FakeDoc(dict):
    __getattr__ = dict.get

    def set(self, key, value):
        self[key] = value

    def save(self, **_):
        self.db.rows[(self["doctype"], self["name"])] = dict(self)
        self.db.saves.append(self["name"])

    def insert(self, **_):
        self["name"] = "perm-" + self["role"]
        self.db.rows[(self["doctype"], self["name"])] = dict(self)
        self.db.inserts.append(self["role"])
        return self


class FakeDB:
    def __init__(self):
        self.rows = {}
        self.inserts = []
        self.saves = []

    def add(self, name, role, **permissions):
        self.rows[("Custom DocPerm", name)] = {
            "doctype": "Custom DocPerm", "name": name, "parent": "SIG Field Visit",
            "role": role, "permlevel": 0, "if_owner": 0,
            **{ptype: 0 for ptype in PTYPES}, **permissions,
        }


def _load_patch(db):
    fake = types.ModuleType("frappe")
    fake.get_all = lambda _doctype, filters, fields, order_by: [
        types.SimpleNamespace(**row)
        for (doctype, _), row in db.rows.items()
        if doctype == "Custom DocPerm" and row.get("parent") == filters["parent"]
    ]

    def get_doc(spec, name=None):
        if isinstance(spec, str):
            return FakeDoc(db.rows[(spec, name)], db=db)
        return FakeDoc(spec, db=db)

    fake.get_doc = get_doc
    fake.clear_cache = lambda **_: None
    fake.logger = lambda *_: types.SimpleNamespace(info=lambda *_: None)
    fake.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
    sys.modules["frappe"] = fake
    spec = importlib.util.spec_from_file_location("sig_field_visit_access_patch", PATCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def restore_frappe():
    previous = sys.modules.get("frappe")
    yield
    if previous is None:
        sys.modules.pop("frappe", None)
    else:
        sys.modules["frappe"] = previous


def test_patch_restores_all_declared_audiences_and_is_idempotent(restore_frappe):
    db = FakeDB()
    db.add("sig-field-ops", "SIG Field Ops", read=1, export=1)
    patch = _load_patch(db)

    patch.execute()
    assert set(db.inserts) == {"System Manager", "Projects Manager", "Projects User", "Warehouse Manager"}
    assert db.rows[("Custom DocPerm", "sig-field-ops")]["read"] == 1
    assert db.rows[("Custom DocPerm", "sig-field-ops")]["export"] == 1
    assert len([r for (dt, _), r in db.rows.items() if dt == "Custom DocPerm"]) == 5
    for role in ("Projects Manager", "Projects User", "Warehouse Manager"):
        row = next(r for (dt, _), r in db.rows.items() if dt == "Custom DocPerm" and r["role"] == role)
        assert row["read"] == row["report"] == row["export"] == 1
        assert all(row[p] == 0 for p in set(PTYPES) - {"read", "report", "export"})

    patch.execute()
    assert len(db.inserts) == 4
    assert len(db.saves) == 0


def test_patch_stops_on_unknown_custom_audience_without_mutation(restore_frappe):
    db = FakeDB()
    db.add("known", "SIG Field Ops", read=1, export=1)
    db.add("unknown", "Unexpected Role", read=1)
    patch = _load_patch(db)

    with pytest.raises(RuntimeError, match="unreviewed custom permission rows"):
        patch.execute()
    assert db.inserts == []
    assert db.saves == []
