import importlib.util
import os
import sys
from datetime import datetime
from types import ModuleType

ROOT = os.path.join(os.path.dirname(__file__), "..", "sig_accounting")


class D(dict):
    __getattr__ = dict.get


def load():
    fake = ModuleType("frappe")
    fake._ = lambda s: s
    fake.whitelist = lambda **k: (lambda f: f)
    fake.parse_json = lambda v: v
    fake.get_list = lambda *a, **k: []
    utils = ModuleType("frappe.utils")
    utils.add_days = lambda d, n: d
    utils.flt = lambda v, *a: float(v or 0)
    utils.getdate = lambda v: v
    utils.now_datetime = lambda: datetime(2026, 11, 17, 12, 0)
    fake.utils = utils
    sys.modules.update({"frappe": fake, "frappe.utils": utils})
    plan_spec = importlib.util.spec_from_file_location("sig_warehouse.sig_accounting.bank_router.tawal_plan", os.path.join(ROOT, "bank_router", "tawal_plan.py"))
    plan = importlib.util.module_from_spec(plan_spec)
    plan_spec.loader.exec_module(plan)
    for name in ("sig_warehouse", "sig_warehouse.sig_accounting", "sig_warehouse.sig_accounting.bank_router"):
        sys.modules.setdefault(name, ModuleType(name))
    sys.modules["sig_warehouse.sig_accounting.bank_router"].tawal_plan = plan
    sys.modules["sig_warehouse.sig_accounting.bank_router.tawal_plan"] = plan
    spec = importlib.util.spec_from_file_location("tawal_router_under_test", os.path.join(ROOT, "tawal_router.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, fake, plan


RECV = "1331 - مدينون - SIG"
SETTINGS = {"legacy_before": "2026-01-01", "allow_bank_reference": True, "auto_draft_enabled": False, "auto_draft_from": ""}


def ctx(payments, credits, entries=(), index=None):
    return {"settings": SETTINGS, "payments": payments, "invoices": [], "index": index or {}, "credits": credits, "entries": list(entries), "receivable": RECV}


def payment(**kw):
    return {"payment_number": "202602717192", "payment_date": "2026-07-28", "amount": 1000.0, "portal_status": "Cleared", "invoice_raw": "SIG-SINV-26-068",
            "remit_account": "23659568000109", "reconcile": {"verdict": "RECONCILED"}, **kw}


def credit(**kw):
    return {"name": "C1", "event_date": "2026-07-29", "amount": 1000.0, "tail": "0109", "text": "", "erp_document": "", "modified": "m", **kw}


def test_existing_entry_offers_the_unlinked_bank_credit_to_link():
    mod, _fake, plan = load()
    entry = {"name": "ACC-PAY-1", "reference_no": "202602717192", "docstatus": 1, "unallocated_amount": 0, "paid_amount": 1000.0, "posting_date": "2026-07-29"}
    rows = mod._rows(ctx([payment()], [credit()], [entry]))
    assert rows[0]["state"] == plan.POSTED and rows[0]["credit_to_link"] == "C1"
    already = mod._rows(ctx([payment()], [credit(erp_document="ACC-PAY-1")], [entry]))
    assert already[0]["credit_to_link"] == ""


def test_public_row_is_small_and_names_the_next_step():
    mod, _fake, plan = load()
    index = {"SIG-SINV-26-068": {"name": "SIG-SINV-26-068", "docstatus": 1, "customer": plan.TAWAL_CUSTOMER, "debit_to": RECV, "outstanding_amount": 1000.0, "grand_total": 1000.0}}
    c = ctx([payment()], [credit()], index=index)
    row = mod._public(mod._rows(c)[0], {p["payment_number"]: p for p in c["payments"]})
    assert row["state"] == plan.READY and row["can_draft"] and row["credit"] == "C1" and row["references"] == ["SIG-SINV-26-068"]
    assert row["reconciled"] is True and "remarks" in row and "body" not in row


def test_invoice_index_prefers_the_copy_that_still_has_a_balance():
    mod, fake, plan = load()
    fake.get_list = lambda *a, **k: [D(name="SIG-SINV-26-054", docstatus=1, customer="T", debit_to=RECV, outstanding_amount=0.0, grand_total=5.0),
                                     D(name="SIG-SINV-26-054-1", docstatus=1, customer="T", debit_to=RECV, outstanding_amount=5.0, grand_total=5.0)]
    assert mod._erp_index()["SIG-SINV-26-054"]["name"] == "SIG-SINV-26-054-1"


def test_credit_text_joins_every_bank_narrative_field():
    mod, _fake, _plan = load()
    text = mod._credit_text({"detail_description": "CRF:202601001526", "reference": "123", "remarks": "x"})
    assert "202601001526" in text and "123" in text


def test_groups_partition_every_state():
    mod, _fake, plan = load()
    states = {plan.READY, plan.UNLINKED_READY, plan.BANK_RECEIVED, plan.WAITING_BANK, plan.HOLD_REVIEW, plan.POSSIBLE_EXISTING, plan.UNALLOCATED, plan.DRAFT, plan.POSTED, plan.LEGACY, plan.VOID}
    covered = set().union(*mod.GROUPS.values())
    assert covered == states
    assert sum(1 for g in mod.GROUPS.values() for s in g) == len(states)  # no state in two groups
