"""Invoice-reversal baseline patch (2026-10-07): idempotency, bare-site safety and the credit-note guard.

Runs without Frappe: a small in-memory stand-in for the frappe API is injected before the patch module
is imported, so the same file runs on any developer machine."""
import importlib.util
import pathlib
import sys
import types

import pytest

PATCH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "sig_warehouse" / "patches" / "v1_0" / "add_invoice_reversal_role_and_credit_note_guard.py"
)


class FakeDoc(dict):
    __getattr__ = dict.get

    def append(self, table, row):
        self.setdefault(table, []).append(types.SimpleNamespace(**row))

    def save(self, **_):
        self.db.saves.append((self["doctype"], self.get("name")))

    def insert(self, **_):
        label = self.get("name") or self.get("role_name") or self.get("role_profile") or self.get("role")
        self.db.inserts.append((self["doctype"], label))
        row = {k: v for k, v in self.items() if k != "roles"}
        if self.get("roles"):
            row["roles"] = [r["role"] if isinstance(r, dict) else r.role for r in self["roles"]]
        self.db.rows[(self["doctype"], label)] = row
        return self


class FakeDB:
    def __init__(self):
        self.rows = {}  # (doctype, name) -> dict
        self.saves, self.inserts, self.sets = [], [], []

    def add(self, doctype, name, **fields):
        self.rows[(doctype, name)] = dict(fields, doctype=doctype, name=name)

    def _match(self, doctype, filt):
        for (dt, name), row in self.rows.items():
            if dt != doctype:
                continue
            if isinstance(filt, str):
                if name == filt:
                    yield name, row
            elif all(row.get(k) == v for k, v in filt.items()):
                yield name, row

    def exists(self, doctype, filt):
        return next(self._match(doctype, filt), None) is not None

    def get_value(self, doctype, filt, field):
        hit = next(self._match(doctype, filt), None)
        return hit[1].get(field) if hit else None

    def set_value(self, doctype, name, field, value=None, update_modified=True):
        values = field if isinstance(field, dict) else {field: value}
        self.rows[(doctype, name)].update(values)
        self.sets.append((doctype, name, values))


def _install_fake_frappe(db):
    fake = types.ModuleType("frappe")
    fake.db = db

    def get_doc(spec, name=None):
        if isinstance(spec, str):
            row = db.rows[(spec, name)]
            doc = FakeDoc(row)
            doc.db = db
            doc["roles"] = [types.SimpleNamespace(role=r) for r in row.get("roles", [])]
            return doc
        doc = FakeDoc(spec)
        doc.db = db
        return doc

    fake.get_doc = get_doc
    fake.clear_cache = lambda **_: None
    fake.logger = lambda: types.SimpleNamespace(warning=lambda *_: None)
    sys.modules["frappe"] = fake
    return fake


def _load_patch():
    spec = importlib.util.spec_from_file_location("invoice_reversal_patch", PATCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _live_before_state():
    db = FakeDB()
    db.add("Custom DocPerm", "am0", parent="Sales Invoice", role="Accounts Manager", permlevel=0, cancel=1)
    db.add("Custom DocPerm", "au0", parent="Sales Invoice", role="Accounts User", permlevel=0, cancel=0)
    db.add("Role Profile", "ERP Admin", roles=["System Manager", "Accounts Manager"])
    db.add("Role Profile", "Finance User", roles=["Accounts User", "SIG Stock Viewer"])
    db.add("User", "baligh.hamdi@sigtele.com", role_profile_name="Finance User")
    db.add("User", "mahmoud.muhammad@sigtele.com", role_profile_name="Finance User")
    return db


@pytest.fixture
def patch_module():
    saved = sys.modules.get("frappe")
    yield
    if saved is None:
        sys.modules.pop("frappe", None)
    else:
        sys.modules["frappe"] = saved


def test_patch_converges_and_is_idempotent(patch_module):
    db = _live_before_state()
    _install_fake_frappe(db)
    patch = _load_patch()

    patch.execute()
    assert db.exists("Role", "SIG Invoice Reversal")
    assert ("Custom DocPerm", "SIG Invoice Reversal") in db.inserts
    row = db.rows[("Custom DocPerm", "SIG Invoice Reversal")]
    assert (row["read"], row["cancel"]) == (1, 1)
    assert all(row[p] == 0 for p in ("write", "create", "delete", "submit", "amend", "report", "export", "import", "print", "email", "share"))
    assert db.rows[("Custom DocPerm", "am0")]["cancel"] == 0
    assert db.rows[("Custom DocPerm", "au0")]["cancel"] == 0
    assert ("Role Profile", "ERP Admin") in db.saves
    assert ("Role Profile", "Finance User + Invoice Reversal") in db.inserts
    assert ("User", "baligh.hamdi@sigtele.com") in db.saves
    assert ("User", "mahmoud.muhammad@sigtele.com") not in db.saves  # other Finance User untouched
    assert ("Server Script", "SIG Credit Note Restriction") in db.inserts


def test_second_run_does_not_resave_profiles_or_users(patch_module):
    patch = None
    db = FakeDB()  # the live state after the patch, with one drifted ptype to prove convergence
    db.add("Role", "SIG Invoice Reversal")
    db.add("Custom DocPerm", "am0", parent="Sales Invoice", role="Accounts Manager", permlevel=0, cancel=0)
    db.add("Custom DocPerm", "rev", parent="Sales Invoice", role="SIG Invoice Reversal", permlevel=0,
           read=1, cancel=1, export=1)
    db.add("Role Profile", "ERP Admin", roles=["System Manager", "Accounts Manager", "SIG Invoice Reversal"])
    db.add("Role Profile", "Finance User", roles=["Accounts User"])
    db.add("Role Profile", "Finance User + Invoice Reversal", roles=["Accounts User", "SIG Invoice Reversal"])
    db.add("User", "baligh.hamdi@sigtele.com", role_profile_name="Finance User + Invoice Reversal")
    _install_fake_frappe(db)
    patch = _load_patch()
    db.add("Server Script", "SIG Credit Note Restriction", script=patch.SCRIPT_BODY)

    patch.execute()
    assert db.saves == []  # no profile/user re-save, so no role re-derivation for anybody
    assert db.inserts == []
    assert db.rows[("Custom DocPerm", "rev")]["export"] == 0  # drift corrected
    assert db.rows[("Custom DocPerm", "am0")]["cancel"] == 0


def test_bare_site_gets_no_sparse_permission_rows(patch_module):
    db = FakeDB()  # no Custom DocPerm for Sales Invoice at all
    _install_fake_frappe(db)
    patch = _load_patch()
    patch.execute()
    assert not any(dt == "Custom DocPerm" for dt, _ in db.inserts)
    assert db.exists("Role", "SIG Invoice Reversal")


class _Thrown(Exception):
    pass


def _run_guard(body, *, is_return, user, roles, stored_docstatus):
    db = types.SimpleNamespace(
        get_value=lambda *_: stored_docstatus,
        exists=lambda doctype, filt: user in roles and filt["role"] == "SIG Invoice Reversal" and filt["parent"] == user,
    )

    def throw(message):
        raise _Thrown(message)

    frappe = types.SimpleNamespace(db=db, session=types.SimpleNamespace(user=user), throw=throw)
    scope = {"doc": types.SimpleNamespace(is_return=is_return, name="SIG-SINV-26-999"), "frappe": frappe}
    exec(compile(body, "guard", "exec"), scope)


def test_credit_note_guard_paths(patch_module):
    db = _live_before_state()
    _install_fake_frappe(db)
    body = _load_patch().SCRIPT_BODY
    allowed = {"baligh.hamdi@sigtele.com", "mohammed.gain@sigtele.com"}

    with pytest.raises(_Thrown):  # other finance user, new credit note
        _run_guard(body, is_return=1, user="mahmoud.muhammad@sigtele.com", roles=allowed, stored_docstatus=None)
    with pytest.raises(_Thrown):  # other finance user, submitting a draft credit note
        _run_guard(body, is_return=1, user="mahmoud.muhammad@sigtele.com", roles=allowed, stored_docstatus=0)
    _run_guard(body, is_return=1, user="baligh.hamdi@sigtele.com", roles=allowed, stored_docstatus=None)
    _run_guard(body, is_return=1, user="Administrator", roles=allowed, stored_docstatus=None)
    # already-submitted return (ZATCA/QR/payment-state post-submit updates) is never blocked
    _run_guard(body, is_return=1, user="mahmoud.muhammad@sigtele.com", roles=allowed, stored_docstatus=1)
    # ordinary invoices are never affected
    _run_guard(body, is_return=0, user="mahmoud.muhammad@sigtele.com", roles=allowed, stored_docstatus=None)
