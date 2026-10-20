"""Payment Terms Template keeps the reviewed role matrix after app migrations."""
import importlib.util
import pathlib
import sys
import types

import pytest


MODULE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "sig_warehouse" / "permissions.py"
)
PTYPES = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "import", "print", "email", "share", "select",
)
EXPECTED_ALL = {
    "read": 0, "write": 0, "create": 0, "delete": 0, "submit": 0,
    "cancel": 0, "amend": 0, "report": 1, "export": 1, "import": 0,
    "print": 1, "email": 1, "share": 1, "select": 1,
}


class FakeDoc(dict):
    __getattr__ = dict.get

    def __init__(self, data, db):
        super().__init__(data)
        self.db = db

    def set(self, key, value):
        self[key] = value

    def save(self, **_):
        self.db.rows[self["name"]] = dict(self)
        self.db.saves.append(self["name"])

    def insert(self, **_):
        self["name"] = "payment-terms-all"
        self.db.rows[self["name"]] = dict(self)
        self.db.inserts.append(self["role"])
        return self


class FakeDB:
    def __init__(self, approved):
        self.rows = {}
        self.inserts = []
        self.saves = []
        for idx, (role, grants) in enumerate(approved.items()):
            if role == "All":
                continue
            self.rows[role] = {
                "doctype": "Custom DocPerm", "name": f"perm-{idx}",
                "parent": "Payment Terms Template", "role": role,
                "permlevel": 0, "if_owner": 0,
                **{ptype: grants.get(ptype, 0) for ptype in PTYPES},
            }


def _load_module(db):
    fake = types.ModuleType("frappe")
    fake.get_all = lambda _doctype, filters, fields, order_by: [
        FakeDoc(row, db) for row in db.rows.values()
        if row.get("parent") == filters["parent"]
    ]

    def get_doc(spec, name=None):
        if isinstance(spec, str):
            return FakeDoc(next(row for row in db.rows.values() if row["name"] == name), db)
        return FakeDoc(spec, db)

    fake.get_doc = get_doc
    fake.clear_cache = lambda **_: None
    fake.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
    sys.modules["frappe"] = fake
    spec = importlib.util.spec_from_file_location("payment_terms_permission_reconcile", MODULE)
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


def test_restores_exact_previous_all_row_and_is_idempotent(restore_frappe):
    module = _load_module(FakeDB({}))
    db = FakeDB(module.APPROVED)
    module = _load_module(db)

    module.reconcile_payment_terms_template_permissions()
    row = db.rows["payment-terms-all"]
    assert row["role"] == "All"
    assert {ptype: row[ptype] for ptype in PTYPES} == EXPECTED_ALL
    assert len(db.rows) == len(module.APPROVED)

    module.reconcile_payment_terms_template_permissions()
    assert len(db.rows) == len(module.APPROVED)
    assert db.inserts == ["All"]
    assert db.saves == []


def test_stops_on_unreviewed_role_without_mutation(restore_frappe):
    module = _load_module(FakeDB({}))
    db = FakeDB(module.APPROVED)
    db.rows["unexpected"] = {
        "doctype": "Custom DocPerm", "name": "unexpected",
        "parent": "Payment Terms Template", "role": "Unreviewed Role",
        "permlevel": 0, "if_owner": 0,
    }
    module = _load_module(db)

    with pytest.raises(RuntimeError, match="unreviewed role"):
        module.reconcile_payment_terms_template_permissions()
    assert db.inserts == []
    assert db.saves == []
