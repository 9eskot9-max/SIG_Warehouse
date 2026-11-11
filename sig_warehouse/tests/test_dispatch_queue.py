"""Pure-function and access-gate tests for the Dispatch Queue read model."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _module(user="Stock Manager@x", roles=("Stock Manager",), perms=True):
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda *a, **k: (lambda f: f)
    frappe.PermissionError = type("PermissionError", (Exception,), {})
    frappe.DoesNotExistError = type("DoesNotExistError", (Exception,), {})
    frappe.session = SimpleNamespace(user=user)
    frappe.get_roles = lambda u=None: list(roles)
    frappe.has_permission = lambda *a, **k: perms

    def throw(message, exc=Exception):
        raise exc(message)
    frappe.throw = throw
    frappe.utils = SimpleNamespace(today=lambda: "2026-11-11")
    sys.modules["frappe"] = frappe
    source = Path(__file__).resolve().parents[1] / "sig_warehouse" / "dispatch_queue.py"
    spec = importlib.util.spec_from_file_location("dispatch_queue_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, frappe


def line(parent="MR-1", item="A", wh="W1", qty=10, issued=0, cancelled=0, remaining=None, reason=""):
    remaining = qty - issued - cancelled if remaining is None else remaining
    return {"parent": parent, "item_code": item, "warehouse": wh, "qty": qty, "custom_qty_issued": issued,
            "custom_qty_cancelled": cancelled, "custom_qty_remaining": remaining, "custom_cancel_reason": reason}


def test_availability_green_yellow_red_and_none():
    dq, _ = _module()
    bins = [{"item_code": "A", "warehouse": "W1", "actual_qty": 10},
            {"item_code": "B", "warehouse": "W2", "actual_qty": 8},
            {"item_code": "C", "warehouse": "W3", "actual_qty": 1}]
    lines = [line("MR-G", "A", "W1", 5), line("MR-Y", "B", "W1", 5), line("MR-R", "C", "W1", 5),
             line("MR-DONE", "A", "W1", 5, issued=5)]
    out = dq.classify_availability(lines, bins)
    assert out == {"MR-G": "green", "MR-Y": "yellow", "MR-R": "red"}
    assert "MR-DONE" not in out


def test_worst_return_state():
    dq, _ = _module()
    assert dq.worst_return_state([]) == "NONE"
    assert dq.worst_return_state([{"custom_return_state": "DECLARED"}]) == "DECLARED"
    assert dq.worst_return_state([{"custom_return_state": "DECLARED"}, {"custom_return_state": "PENDING"}]) == "PENDING"
    assert dq.worst_return_state([{"custom_return_state": "PENDING"}, {"custom_return_state": "PARTIAL"}]) == "PARTIAL"
    assert dq.worst_return_state([{"custom_return_state": None}]) == "PENDING"


def test_flags_cancelled_partial_and_waiver():
    dq, _ = _module()
    operator = [line(qty=10, issued=4, cancelled=6, reason="OPERATOR")]
    waived = [line(qty=10, issued=4, cancelled=6, reason="WH_CLOSED")]
    assert "cancelled_partial" in dq.row_flags("PARTIAL", operator, "PENDING")
    assert "cancelled_partial" not in dq.row_flags("PARTIAL", waived, "PENDING")
    never_issued = [line(qty=10, issued=0, cancelled=10, reason="OPERATOR")]
    assert "cancelled_partial" not in dq.row_flags("PARTIAL", never_issued, "NONE")


def test_flags_return_blocks_close_and_inconsistency():
    dq, _ = _module()
    done = [line(qty=5, issued=5)]
    assert "return_blocks_close" in dq.row_flags("DISPATCHED", done, "PARTIAL")
    assert "return_blocks_close" not in dq.row_flags("DISPATCHED", done, "DECLARED")
    assert "no_open_lines_but_open_stage" in dq.row_flags("PENDING", done, "NONE")


def test_sort_newest_first_puts_latest_mir_on_top():
    dq, _ = _module()
    rows = [{"name": "MR-26-1208", "created": "2026-11-05 09:00:00"},
            {"name": "MR-26-1256", "created": "2026-11-10 09:40:15"},
            {"name": "MR-26-1100", "created": "2026-10-01 09:00:00"}]
    assert [r["name"] for r in dq.sort_rows(rows, "newest")][0] == "MR-26-1256"
    assert [r["name"] for r in dq.sort_rows(rows, "bogus")][0] == "MR-26-1256"


def test_sort_waiting_and_attention():
    dq, _ = _module()
    rows = [{"name": "a", "stage": "PENDING", "required_by": "2026-12-01", "created": "2026-11-01", "age_days": 10},
            {"name": "b", "stage": "PARTIAL", "required_by": "2026-11-20", "created": "2026-11-05", "age_days": 6},
            {"name": "c", "stage": "DISPATCHED", "created": "2026-11-09", "availability": "red", "flags": ["return_blocks_close"], "age_days": 2}]
    assert [r["name"] for r in dq.sort_rows(rows, "waiting")] == ["b", "a", "c"]
    assert dq.sort_rows(rows, "attention")[0]["name"] == "c"


def test_summarize_counts_and_return_pending():
    dq, _ = _module()
    rows = [{"stage": "PENDING", "availability": "red", "flags": []},
            {"stage": "DISPATCHED", "availability": None, "flags": ["return_blocks_close"]},
            {"stage": "CLOSED", "availability": "red", "flags": []}]
    s = dq.summarize(rows)
    assert (s["PENDING"], s["DISPATCHED"], s["CLOSED_RECENT"], s["return_pending"], s["red"]) == (1, 1, 1, 1, 1)


def test_build_row_totals_and_last_dn():
    dq, _ = _module()
    header = {"name": "MR-1", "custom_mir_number": "1256", "custom_site": "ZRI439",
              "custom_dispatch_stage": "PARTIAL", "creation": "2026-11-10 09:40:15"}
    lines = [line(qty=10, issued=4), line(qty=5, issued=5)]
    dns = [{"name": "DN-1", "posting_date": "2026-11-10", "custom_return_state": "PENDING"},
           {"name": "DN-2", "posting_date": "2026-11-11", "custom_return_state": "DECLARED"}]
    row = dq.build_row(header, lines, dns, "green", "2026-11-11")
    assert row["qty"]["remaining"] == 6 and row["lines"]["open"] == 1 and row["lines"]["total"] == 2
    assert row["dn"]["last"] == "DN-2" and row["return"] == "PENDING" and row["age_days"] == 1


def test_search_haystack_finds_mir_number():
    dq, _ = _module()
    assert "1256" in dq.search_haystack({"name": "MR-26-1256", "mir": "1256", "site": "ZRI439"})


def test_get_queue_denied_for_guest_and_for_non_warehouse_role():
    dq, frappe = _module(user="Guest", roles=())
    with pytest.raises(frappe.PermissionError):
        dq.get_queue()
    dq, frappe = _module(roles=("Accounts User",))
    with pytest.raises(frappe.PermissionError):
        dq.get_queue()
    dq, frappe = _module(roles=("Stock User",), perms=False)
    with pytest.raises(frappe.PermissionError):
        dq.get_queue()


def test_act_roles_match_dispatch_operation():
    dq, _ = _module()
    source = (Path(__file__).resolve().parents[1] / "sig_warehouse" / "dispatch_operation.py").read_text(encoding="utf-8")
    assert 'ALLOWED_DISPATCH_ROLES = ("Stock Manager", "System Manager")' in source
    assert set(dq.ACT_ROLES) == {"Stock Manager", "System Manager"}
    assert dq._can_act(["Stock User"]) is False and dq._can_act(["Stock Manager"]) is True
