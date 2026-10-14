"""Offline scheduler tests for the DN return-window closure policy."""
import datetime as dt
import sys
import types


TODAY = dt.date(2026, 10, 12)
POLICY_START = "2026-09-30 00:00:00"


def _date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _datetime(value=None):
    if value is None:
        return dt.datetime.combine(TODAY, dt.time(12))
    if isinstance(value, dt.datetime):
        return value
    return dt.datetime.fromisoformat(str(value))


# The production Frappe runtime is not installed in the local test environment.
frappe_stub = types.ModuleType("frappe")
frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn)
frappe_stub.session = types.SimpleNamespace(user="Administrator")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.add_days = lambda value, days: _date(value) + dt.timedelta(days=days)
utils_stub.getdate = _date
utils_stub.now = lambda: "2026-10-12 12:00:00"
data_stub = types.ModuleType("frappe.utils.data")
data_stub.get_datetime = _datetime
data_stub.get_datetime_in_timezone = lambda _timezone: dt.datetime.combine(TODAY, dt.time(12))
data_stub.get_system_timezone = lambda: "Asia/Riyadh"
frappe_stub.utils = utils_stub
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub
sys.modules["frappe.utils.data"] = data_stub
try:
    import pytz  # noqa: F401
except ImportError:
    pytz_stub = types.ModuleType("pytz")
    pytz_stub.timezone = lambda _name: dt.timezone.utc
    sys.modules["pytz"] = pytz_stub

from sig_warehouse.sig_warehouse import return_closure  # noqa: E402


class FakeRecord:
    def __init__(self, fake, values):
        self.fake = fake
        self.values = dict(values)

    def insert(self, **_kwargs):
        if self.values["doctype"] == "SIG Dispatch Operation":
            self.fake.db.operations[self.values["operation_id"]] = self.values
        elif self.values["doctype"] == "Comment":
            self.fake.db.comments.append(self.values)
        elif self.values["doctype"] == "Stock Entry":
            self.fake.stock_entries.append(self.values)
        return self


class FakeDB:
    def __init__(self, sources, lines):
        self.sources = sources
        self.lines = {row["name"]: row for row in lines}
        self.operations = {}
        self.comments = []
        self.commits = 0

    def exists(self, doctype, name):
        return doctype == "SIG Dispatch Operation" and name in self.operations

    def get_value(self, doctype, name, fieldname):
        if doctype == "SIG Dispatch Operation" and name == return_closure.POLICY_START_ID:
            return POLICY_START if fieldname == "created_at" else None
        return None

    def sql(self, _query, params=()):
        return [(params[0],)] if params and params[0] in self.sources else []

    def set_value(self, doctype, name, fieldname, value, update_modified=True):
        assert doctype == "Stock Entry Detail"
        assert fieldname == "custom_return_closed"
        assert update_modified is False
        self.lines[name][fieldname] = value

    def commit(self):
        self.commits += 1

    def rollback(self):
        raise AssertionError("unexpected scheduler rollback")


class FakeFrappe:
    def __init__(self, sources, lines):
        self.db = FakeDB(sources, lines)
        self.session = frappe_stub.session
        self.stock_entries = []
        self.error_logs = []
        self.cache_clears = []

    def get_all(self, doctype, filters=None, fields=None, **_kwargs):
        if doctype == "Stock Entry":
            return [types.SimpleNamespace(name=name) for name in self.db.sources]
        if doctype == "Comment":
            return []
        if doctype == "Stock Entry Detail":
            parent = (filters or {}).get("parent")
            rows = [row for row in self.db.lines.values() if row.get("parent") == parent]
            return [types.SimpleNamespace(**{key: row.get(key) for key in fields}) for row in rows]
        raise AssertionError(f"unexpected DocType query: {doctype}")

    def get_doc(self, doctype_or_values, name=None):
        if doctype_or_values == "Stock Entry":
            return self.db.sources[name]
        return FakeRecord(self, doctype_or_values)

    def clear_document_cache(self, doctype, name):
        self.cache_clears.append((doctype, name))

    def log_error(self, **kwargs):
        self.error_logs.append(kwargs)

    def get_traceback(self):
        return "unexpected scheduler error"

    def logger(self, _name):
        return types.SimpleNamespace(info=lambda *_args, **_kwargs: None)


def _source(name, *, creation="2026-10-01 09:00:00", posting_date="2026-10-01"):
    return types.SimpleNamespace(
        name=name, creation=creation, posting_date=posting_date, docstatus=1,
        is_return=0, purpose="Material Issue",
    )


def _line(name, parent, qty=0.01, returned=0.0, custody=0.0):
    return {
        "name": name, "parent": parent, "parenttype": "Stock Entry",
        "qty": qty, "custom_qty_returned": returned, "custom_qty_custody": custody,
        "custom_return_closed": 0,
    }


def _run(monkeypatch, fake):
    monkeypatch.setattr(return_closure, "frappe", fake)
    monkeypatch.setattr(return_closure, "_policy_date", _date)
    monkeypatch.setattr(return_closure.rollup, "recompute_return_state", lambda _name: "CLOSED")
    monkeypatch.setattr(return_closure.rollup, "_linked_mr_names", lambda _source: ["MR-TEST"])
    monkeypatch.setattr(return_closure.rollup, "recompute_mr_lifecycle_state", lambda _name: "CLOSED")
    return_closure.close_expired_return_windows()


def test_due_dn_closes_only_undeclared_lines_and_is_idempotent(monkeypatch):
    source = _source("DN-MOCK-001")
    lines = [
        _line("ROW-OPEN", source.name),
        _line("ROW-RETURNED", source.name, qty=1, returned=1),
    ]
    fake = FakeFrappe({source.name: source}, lines)

    _run(monkeypatch, fake)

    assert fake.db.lines["ROW-OPEN"]["custom_return_closed"] == 1
    assert fake.db.lines["ROW-RETURNED"]["custom_return_closed"] == 0
    assert fake.db.lines["ROW-OPEN"]["custom_qty_returned"] == 0
    assert "SIG-AUTO-CLOSE-DN-MOCK-001" in fake.db.operations
    assert fake.db.operations["SIG-AUTO-CLOSE-DN-MOCK-001"]["line_count"] == 1
    assert len(fake.db.comments) == 1
    assert "No stock movement was created" in fake.db.comments[0]["content"]
    assert fake.stock_entries == []

    _run(monkeypatch, fake)

    assert len(fake.db.comments) == 1
    assert len(fake.db.operations) == 1
    assert fake.stock_entries == []


def test_pre_policy_dn_is_not_closed(monkeypatch):
    source = _source("DN-PRE-POLICY", creation="2026-09-29 09:00:00", posting_date="2026-09-29")
    line = _line("ROW-PRE-POLICY", source.name)
    fake = FakeFrappe({source.name: source}, [line])

    _run(monkeypatch, fake)

    assert line["custom_return_closed"] == 0
    assert fake.db.operations == {}
    assert fake.db.comments == []


def test_overdue_backdated_dn_gets_review_note_not_auto_close(monkeypatch):
    source = _source("DN-BACKDATED", creation="2026-10-05 09:00:00", posting_date="2026-09-20")
    line = _line("ROW-BACKDATED", source.name)
    fake = FakeFrappe({source.name: source}, [line])

    _run(monkeypatch, fake)

    assert line["custom_return_closed"] == 0
    assert fake.db.operations == {}
    assert len(fake.db.comments) == 1
    assert "SIG_RETURN_WINDOW_REVIEW_REQUIRED" in fake.db.comments[0]["content"]
