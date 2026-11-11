"""Pure-function, data-path and access-gate tests for the Dispatch Queue read model."""
import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

TODAY = "2026-11-11"


def _op(f, v):
    return {"=": lambda a, b: a == b, "in": lambda a, b: a in b, ">=": lambda a, b: str(a) >= str(b)}[f](*v)


class FakeFrappe(ModuleType):
    """Tiny in-memory Frappe: tables of dict rows, get_list/get_all with simple filters."""

    def __init__(self):
        super().__init__("frappe")
        self.PermissionError = type("PermissionError", (Exception,), {})
        self.DoesNotExistError = type("DoesNotExistError", (Exception,), {})
        self.session = SimpleNamespace(user="u@x")
        self.roles = ["Stock Manager"]
        self.perms = {}
        self.deny_fields = set()
        self.tables = {}
        self.calls = []
        self.utils = SimpleNamespace(
            today=lambda: TODAY, now=lambda: TODAY + " 00:00:00",
            add_days=lambda d, n: str(date.fromisoformat(str(d)[:10]) + timedelta(days=n)))

    def whitelist(self, *a, **k):
        return lambda f: f

    def get_roles(self, user=None):
        return list(self.roles)

    def has_permission(self, doctype, ptype="read", doc=None, **k):
        return self.perms.get(doctype, True)

    def throw(self, message, exc=Exception):
        raise exc(message)

    def _query(self, doctype, filters=None, fields=None, limit_page_length=0, order_by=None, permitted=True, **k):
        flt = filters
        if isinstance(flt, dict):
            flt = [[kk, "in" if isinstance(vv, list) and vv and vv[0] == "in" else "=", vv[1] if isinstance(vv, list) else vv]
                   for kk, vv in flt.items()]
        rows = [r for r in self.tables.get(doctype, []) if all(_op(f, (r.get(c), v)) for c, f, v in (flt or []))]
        if permitted:   # get_list: Employee User Permission hides rows addressed to others
            rows = [r for r in rows if not r.get("_up_hidden")]
        if order_by and "creation desc" in order_by:
            rows = sorted(rows, key=lambda r: r.get("creation", ""), reverse=True)
        if limit_page_length:
            rows = rows[:limit_page_length]
        drop = self.deny_fields if permitted else set()   # get_list drops unreadable permlevel-1 fields
        return [{k2: v2 for k2, v2 in r.items() if (not fields or k2 in fields) and k2 not in drop and k2 != "_up_hidden"}
                for r in rows]

    def get_list(self, doctype, *a, **k):
        self.calls.append(("get_list", doctype, k.get("fields")))
        return self._query(doctype, *a, **k)

    def get_all(self, doctype, *a, **k):
        self.calls.append(("get_all", doctype, k.get("fields")))
        return self._query(doctype, *a, permitted=False, **k)


@pytest.fixture
def dq():
    saved = sys.modules.get("frappe")
    frappe = FakeFrappe()
    sys.modules["frappe"] = frappe
    try:
        source = Path(__file__).resolve().parents[1] / "sig_warehouse" / "dispatch_queue.py"
        spec = importlib.util.spec_from_file_location("dispatch_queue_under_test", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # binds `frappe` to the fake; restoring sys.modules below is safe
    finally:
        if saved is None:
            sys.modules.pop("frappe", None)
        else:
            sys.modules["frappe"] = saved
    return module, frappe


def line(parent="MR-1", item="A", wh="W1", qty=10, issued=0, cancelled=0, remaining=None, reason="", name=None):
    remaining = qty - issued - cancelled if remaining is None else remaining
    return {"name": name or f"{parent}-{item}", "parent": parent, "item_code": item, "warehouse": wh, "qty": qty,
            "custom_qty_issued": issued, "custom_qty_cancelled": cancelled, "custom_qty_remaining": remaining,
            "custom_cancel_reason": reason}


def mr(name, stage="PENDING", created="2026-11-10 09:00:00", modified=None, **extra):
    row = {"name": name, "docstatus": 1, "material_request_type": "Material Issue", "custom_dispatch_stage": stage,
           "creation": created, "modified": modified or created, "custom_mir_number": name[-4:], "custom_site": "S1"}
    row.update(extra)
    return row


# ---------------------------------------------------------------- pure helpers
def test_availability_green_yellow_red_and_none(dq):
    m, _ = dq
    bins = [{"item_code": "A", "warehouse": "W1", "actual_qty": 10}, {"item_code": "B", "warehouse": "W2", "actual_qty": 8},
            {"item_code": "C", "warehouse": "W3", "actual_qty": 1}]
    lines = [line("MR-G", "A", "W1", 5), line("MR-Y", "B", "W1", 5), line("MR-R", "C", "W1", 5),
             line("MR-DONE", "A", "W1", 5, issued=5)]
    assert m.classify_availability(lines, bins) == {"MR-G": "green", "MR-Y": "yellow", "MR-R": "red"}


def test_unknown_return_state_is_never_shown_as_pending(dq):
    m, _ = dq
    assert m.worst_return_state([{"name": "DN-1"}]) is None          # field absent = unreadable
    row = m.build_row(mr("MR-1", "DISPATCHED"), [line(qty=5, issued=5)], [{"name": "DN-1"}], None, TODAY)
    assert row["return"] is None and "return_blocks_close" not in row["flags"]


def test_worst_return_state(dq):
    m, _ = dq
    s = lambda *states: [{"custom_return_state": x} for x in states]  # noqa: E731
    assert m.worst_return_state([]) == "NONE"
    assert m.worst_return_state(s("DECLARED")) == "DECLARED"
    assert m.worst_return_state(s("DECLARED", "PENDING")) == "PENDING"
    assert m.worst_return_state(s("PENDING", "PARTIAL")) == "PARTIAL"
    assert m.worst_return_state(s(None)) == "PENDING"


def test_flags_cancelled_partial_and_waiver(dq):
    m, _ = dq
    assert "cancelled_partial" in m.row_flags("PARTIAL", [line(qty=10, issued=4, cancelled=6, reason="OPERATOR")], "PENDING")
    assert "cancelled_partial" not in m.row_flags("PARTIAL", [line(qty=10, issued=4, cancelled=6, reason="WH_CLOSED")], "PENDING")
    assert "cancelled_partial" not in m.row_flags("PARTIAL", [line(qty=10, cancelled=10, reason="OPERATOR")], "NONE")


def test_return_flag_needs_a_real_undeclared_dn(dq):
    m, _ = dq
    done = [line(qty=5, issued=5)]
    assert "return_blocks_close" in m.row_flags("DISPATCHED", done, "PARTIAL")
    assert "return_blocks_close" in m.row_flags("DISPATCHED", done, "PENDING")
    assert "return_blocks_close" not in m.row_flags("DISPATCHED", done, "DECLARED")
    # no DN record at all (e.g. dispatched before cutover) must not be flagged from missing data
    assert "return_blocks_close" not in m.row_flags("DISPATCHED", done, "NONE")
    assert "no_open_lines_but_open_stage" in m.row_flags("PENDING", done, "NONE")


def test_summarize_counts(dq):
    m, _ = dq
    s = m.summarize([{"stage": "PENDING", "availability": "red", "flags": []},
                     {"stage": "DISPATCHED", "flags": ["return_blocks_close"]},
                     {"stage": "CLOSED", "availability": "red", "flags": []}])
    assert (s["PENDING"], s["DISPATCHED"], s["CLOSED_RECENT"], s["return_pending"], s["red"]) == (1, 1, 1, 1, 1)


def test_closed_on_prefers_return_stamp_over_modified(dq):
    m, _ = dq
    header = {"modified": "2026-01-01 00:00:00"}
    dns = [{"custom_return_closed_on": "2026-11-09 10:00:00"}, {"custom_return_closed_on": "2026-11-10 08:00:00"}]
    assert m.closed_on(header, dns) == "2026-11-10 08:00:00"
    assert m.closed_on(header, []) == "2026-01-01 00:00:00"


def test_build_row_totals_last_dn_and_age(dq):
    m, _ = dq
    header = mr("MR-26-1256", "PARTIAL", created="2026-11-10 09:40:15")
    dns = [{"name": "DN-1", "posting_date": "2026-11-10", "custom_return_state": "PENDING"},
           {"name": "DN-2", "posting_date": "2026-11-11", "custom_return_state": "DECLARED"}]
    row = m.build_row(header, [line(qty=10, issued=4), line(item="B", qty=5, issued=5)], dns, "green", TODAY)
    assert row["qty"]["remaining"] == 6 and row["lines"] == {"total": 2, "open": 1, "issued": 2, "cancelled": 0}
    assert row["dn"]["last"] == "DN-2" and row["return"] == "PENDING" and row["age_days"] == 1
    assert m.build_row(dict(header, creation="garbage"), [], [], None, TODAY)["age_days"] == 0


# ------------------------------------------------------------------ access gate
def test_get_queue_gate(dq):
    m, f = dq
    f.session.user = "Guest"
    with pytest.raises(f.PermissionError):
        m.get_queue()
    f.session.user, f.roles = "u@x", ["Accounts User"]
    with pytest.raises(f.PermissionError):
        m.get_queue()
    f.roles, f.perms = ["Stock User"], {"Material Request": False}
    with pytest.raises(f.PermissionError):
        m.get_queue()


def test_unreadable_stage_field_is_reported_not_guessed(dq):
    m, f = dq
    f.tables = {"Material Request": [mr("MR-26-1")], "Material Request Item": [line("MR-26-1")]}
    f.deny_fields = {"custom_dispatch_stage"}
    with pytest.raises(f.PermissionError, match="permission level 1"):
        m.get_queue()


def test_act_roles_match_dispatch_operation(dq):
    m, _ = dq
    source = (Path(__file__).resolve().parents[1] / "sig_warehouse" / "dispatch_operation.py").read_text(encoding="utf-8")
    assert 'ALLOWED_DISPATCH_ROLES = ("Stock Manager", "System Manager")' in source
    assert set(m.ACT_ROLES) == {"Stock Manager", "System Manager"}
    assert m._can_act(["Stock User"]) is False and m._can_act(["Stock Manager"]) is True


# -------------------------------------------------------------------- data path
def _scenario(f):
    f.tables = {
        "Material Request": [
            mr("MR-26-1208", "PENDING", "2026-11-05 09:00:00"),
            mr("MR-26-1256", "PENDING", "2026-11-10 09:40:15"),
            mr("MR-26-1190", "PARTIAL", "2026-11-01 09:00:00"),
            mr("MR-26-1189", "DISPATCHED", "2026-10-30 09:00:00"),
            mr("MR-26-1100", "CLOSED", "2026-09-01 09:00:00", modified="2026-09-02 00:00:00"),   # closed long ago
            mr("MR-26-1101", "CLOSED", "2026-08-01 09:00:00", modified="2026-08-02 00:00:00"),   # old modified, closed recently
            mr("MR-26-1102", "CLOSED", "2026-11-09 09:00:00", modified="2026-11-09 09:00:00"),   # cancelled, no DN
        ],
        "Material Request Item": [
            line("MR-26-1208", qty=5), line("MR-26-1256", qty=3, item="B"),
            line("MR-26-1190", qty=10, issued=4), line("MR-26-1189", qty=5, issued=5),
            line("MR-26-1100", qty=5, issued=5), line("MR-26-1101", qty=5, issued=5),
            line("MR-26-1102", qty=5, cancelled=5, reason="OPERATOR"),
        ],
        "Stock Entry Detail": [
            {"parent": "DN-A", "material_request": "MR-26-1190", "docstatus": 1},
            {"parent": "DN-A", "material_request": "MR-26-1190", "docstatus": 1},   # duplicate detail row, same DN
            {"parent": "DN-B", "material_request": "MR-26-1189", "docstatus": 1},
            {"parent": "DN-C", "material_request": "MR-26-1100", "docstatus": 1},
            {"parent": "DN-D", "material_request": "MR-26-1101", "docstatus": 1},
        ],
        "Stock Entry": [
            {"name": "DN-A", "docstatus": 1, "is_return": 0, "purpose": "Material Issue", "posting_date": "2026-11-02",
             "custom_return_state": "PENDING", "custom_return_closed_on": None},
            {"name": "DN-B", "docstatus": 1, "is_return": 0, "purpose": "Material Issue", "posting_date": "2026-10-31",
             "custom_return_state": "PARTIAL", "custom_return_closed_on": None},
            {"name": "DN-C", "docstatus": 1, "is_return": 0, "purpose": "Material Issue", "posting_date": "2026-09-01",
             "custom_return_state": "DECLARED", "custom_return_closed_on": "2026-09-02 00:00:00"},
            {"name": "DN-D", "docstatus": 1, "is_return": 0, "purpose": "Material Issue", "posting_date": "2026-08-01",
             "custom_return_state": "DECLARED", "custom_return_closed_on": "2026-11-08 12:00:00"},
        ],
        "Bin": [{"item_code": "A", "warehouse": "W1", "actual_qty": 20}, {"item_code": "B", "warehouse": "W1", "actual_qty": 0}],
    }


def test_queue_returns_newest_first_with_full_counts(dq):
    m, f = dq
    _scenario(f)
    out = m.get_queue()
    names = [r["name"] for r in out["rows"]]
    assert names[0] == "MR-26-1256" and names == sorted(names, key=lambda n: next(
        r["created"] for r in out["rows"] if r["name"] == n), reverse=True)
    assert out["summary"]["PENDING"] == 2 and out["summary"]["PARTIAL"] == 1 and out["summary"]["DISPATCHED"] == 1
    assert out["summary"]["CLOSED_RECENT"] == 0 and out["complete"] is True
    by = {r["name"]: r for r in out["rows"]}
    assert by["MR-26-1208"]["availability"] == "green" and by["MR-26-1256"]["availability"] == "red"
    assert by["MR-26-1190"]["dn"]["count"] == 1, "duplicate detail rows must not duplicate the DN"
    assert by["MR-26-1189"]["return"] == "PARTIAL" and "return_blocks_close" in by["MR-26-1189"]["flags"]
    assert out["access"] == {"dn": True, "availability": True, "can_dispatch": True}


def test_recently_closed_uses_return_stamp_not_modified(dq):
    m, f = dq
    _scenario(f)
    out = m.get_queue(include_closed=1, closed_days=30)
    closed = {r["name"] for r in out["rows"] if r["stage"] == "CLOSED"}
    assert closed == {"MR-26-1101", "MR-26-1102"}   # 1100 closed in Sept: out; 1101 stamped 8 Nov: in; 1102 no DN, modified 9 Nov: in
    assert m.get_queue(include_closed=0)["summary"]["CLOSED_RECENT"] == 0


def test_closed_candidate_cap_marks_result_incomplete(dq):
    m, f = dq
    _scenario(f)
    m.CLOSED_CANDIDATES = 2
    assert m.get_queue(include_closed=1)["complete"] is False
    m.CLOSED_CANDIDATES = 1000
    m.MAX_ROWS = 3
    assert m.get_queue()["complete"] is False


def test_without_stock_entry_or_bin_access_fields_are_hidden(dq):
    m, f = dq
    _scenario(f)
    f.perms = {"Stock Entry": False, "Bin": False}
    out = m.get_queue()
    assert out["access"]["dn"] is False and out["access"]["availability"] is False
    assert all(r["return"] is None and r["availability"] is None for r in out["rows"])
    assert not any("return_blocks_close" in r["flags"] for r in out["rows"])
    assert not any(c[:2] == ("get_all", "Bin") for c in f.calls)


def test_viewer_cannot_dispatch(dq):
    m, f = dq
    _scenario(f)
    f.roles = ["Stock User"]
    assert m.get_queue()["access"]["can_dispatch"] is False


def test_detail_denied_without_document_permission(dq):
    m, f = dq
    _scenario(f)
    f.perms = {"Material Request": False}
    with pytest.raises(f.PermissionError):
        m.get_mr_detail("MR-26-1190")


def test_viewer_without_stock_entry_level_1_still_gets_return_state(dq):
    """Hamid (Stock User) cannot read Stock Entry permlevel-1 fields; get_list would drop them."""
    m, f = dq
    _scenario(f)
    f.roles = ["Stock User"]
    f.deny_fields = {"custom_return_state", "custom_return_closed_on"}
    out = m.get_queue()
    by = {r["name"]: r for r in out["rows"]}
    assert by["MR-26-1189"]["return"] == "PARTIAL" and "return_blocks_close" in by["MR-26-1189"]["flags"]
    assert out["summary"]["return_pending"] == 1


def test_employee_user_permission_does_not_hide_dns(dq):
    """Users with an Employee User Permission must see the same DNs as everyone else."""
    m, f = dq
    _scenario(f)
    for se in f.tables["Stock Entry"]:
        if se["name"] in ("DN-A", "DN-B"):
            se["_up_hidden"] = True   # dispatched to / approved by another employee
    by = {r["name"]: r for r in m.get_queue()["rows"]}
    assert by["MR-26-1190"]["dn"]["count"] == 1 and by["MR-26-1190"]["return"] == "PENDING"
    assert by["MR-26-1189"]["return"] == "PARTIAL"
    detail = m.get_mr_detail("MR-26-1189")
    assert [d["name"] for d in detail["dns"]] == ["DN-B"]


def test_dn_reads_request_workflow_fields_only(dq):
    """The permission-bypassing DN reads must not carry employee, party or amount fields."""
    m, f = dq
    _scenario(f)
    m.get_queue()
    m.get_mr_detail("MR-26-1190")
    forbidden = {"custom_dispatched_to", "custom_approved_by", "custom_initiated_by", "custom_requestor_pm",
                 "owner", "total_amount", "supplier", "customer"}
    bypass = [c for c in f.calls if c[0] == "get_all" and c[1] in ("Stock Entry", "Stock Entry Detail")]
    assert bypass, "DN reads should use get_all"
    for _, doctype, fields in bypass:
        assert fields and not forbidden.intersection(fields), (doctype, fields)


def test_dn_reads_only_follow_readable_requests(dq):
    """DN lookups are keyed by MIR names that came from the permission-filtered MR list."""
    m, f = dq
    _scenario(f)
    f.tables["Material Request"][0]["_up_hidden"] = True       # MR-26-1208 is not readable by this user
    names = {r["name"] for r in m.get_queue()["rows"]}
    assert "MR-26-1208" not in names
