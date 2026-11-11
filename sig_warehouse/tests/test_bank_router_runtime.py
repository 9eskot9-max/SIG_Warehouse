"""Transaction boundaries in the Frappe adapter around each draft insert."""
import importlib
import sys
import types
import datetime as dt
from pathlib import Path
from bank_router.text import account_scope

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "sig_accounting"))


@pytest.fixture
def runtime(monkeypatch):
    frappe = types.ModuleType("frappe")
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda value: int(value or 0)
    utils.flt = lambda value: float(value or 0)
    utils.getdate = lambda value: value
    utils.now_datetime = lambda: None
    frappe.utils = utils
    monkeypatch.setitem(sys.modules, "frappe", frappe)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    sys.modules.pop("bank_router.runtime", None)
    module = importlib.import_module("bank_router.runtime")
    yield module, frappe
    sys.modules.pop("bank_router.runtime", None)


def test_failed_main_draft_insert_rolls_back_before_error_escapes(runtime):
    module, frappe = runtime
    db_calls = []
    frappe.db = types.SimpleNamespace(
        savepoint=lambda name: db_calls.append(("savepoint", name)),
        rollback=lambda **kwargs: db_calls.append(("rollback", kwargs["save_point"])),
        release_savepoint=lambda name: db_calls.append(("release", name)),
    )
    class PartialDraft:
        name = "PE-PARTIAL"
        def insert(self):
            raise RuntimeError("validation failed after partial write")
    frappe.get_doc = lambda body: PartialDraft()
    registered = []
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "bank"}, draft_fees=False,
                                         fee_account="", vat_account="")
    ctx.ledger = types.SimpleNamespace(register=lambda *args: registered.append(args))
    ctx._existing = lambda *args: None
    mv = {"key": "K1", "amount": -10, "date": "2026-11-09", "scope": "scope", "source": {}}
    with pytest.raises(RuntimeError, match="partial write"):
        ctx.create("EXPENSE_PAYMENT", mv, {"expense_account": "Travel", "label": "Person"}, [])
    assert db_calls == [("savepoint", "bank_router_main_draft"), ("rollback", "bank_router_main_draft"),
                        ("release", "bank_router_main_draft")]
    assert registered == []


def test_failed_fee_draft_insert_rolls_back_its_own_savepoint(runtime):
    module, frappe = runtime
    db_calls = []
    frappe.db = types.SimpleNamespace(
        savepoint=lambda name: db_calls.append(("savepoint", name)),
        rollback=lambda **kwargs: db_calls.append(("rollback", kwargs["save_point"])),
        release_savepoint=lambda name: db_calls.append(("release", name)),
    )
    class PartialDraft:
        def insert(self):
            raise RuntimeError("fee validation failed")
    frappe.get_doc = lambda body: PartialDraft()
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "bank"}, fee_account="Fees", vat_account="")
    ctx._existing = lambda *args: None
    mv = {"key": "K1", "amount": -10, "date": "2026-11-09", "scope": "scope", "source": {}}
    with pytest.raises(RuntimeError, match="fee validation"):
        ctx.create_fee_journal(mv, [{"amount": -1, "family": "BANK_FEE"}])
    assert db_calls == [("savepoint", "bank_router_fee_draft"), ("rollback", "bank_router_fee_draft"),
                        ("release", "bank_router_fee_draft")]


def test_payment_entry_reference_is_rechecked_and_carried_forward(runtime):
    module, frappe = runtime
    class PurchaseInvoice:
        name = "PINV-1"
        docstatus = 1
        company = module.documents.COMPANY
        currency = "SAR"
        supplier = "SUP-1"
        grand_total = 1150
        def get(self, field):
            return 900 if field == "outstanding_amount" else None
        def check_permission(self, permission):
            assert permission == "read"
    frappe.get_doc = lambda doctype, name: PurchaseInvoice()
    ctx = module.Context.__new__(module.Context)
    mv = {"amount": -500, "recognition": {"transfer_request": {"allocation_json":
          '[{"reference_doctype":"Purchase Invoice","reference_name":"PINV-1","allocated_amount":500}]'}}}
    refs = ctx._payment_references(mv, {"party_type": "Supplier", "party": "SUP-1"})
    assert refs == [{"reference_doctype": "Purchase Invoice", "reference_name": "PINV-1", "allocated_amount": 500}]


def test_payment_entry_reference_stops_if_outstanding_became_too_small(runtime):
    module, frappe = runtime
    class PurchaseInvoice:
        docstatus = 1
        company = module.documents.COMPANY
        currency = "SAR"
        supplier = "SUP-1"
        def get(self, field):
            return 200 if field == "outstanding_amount" else None
        def check_permission(self, permission):
            pass
    frappe.get_doc = lambda doctype, name: PurchaseInvoice()
    ctx = module.Context.__new__(module.Context)
    mv = {"amount": -500, "recognition": {"transfer_request": {"allocation_json":
          '[{"reference_doctype":"Purchase Invoice","reference_name":"PINV-1","allocated_amount":500}]'}}}
    with pytest.raises(ValueError, match="exceeds the current available"):
        ctx._payment_references(mv, {"party_type": "Supplier", "party": "SUP-1"})


def test_review_only_disables_drafting_even_when_settings_enable_it(runtime, monkeypatch):
    module, frappe = runtime
    row = types.SimpleNamespace(name="movement", event_date="2026-11-09")
    frappe.db = types.SimpleNamespace(sql=lambda *a, **k: [row], savepoint=lambda *a: None,
                                      rollback=lambda **k: None, release_savepoint=lambda *a: None)
    frappe.session = types.SimpleNamespace(user="owner")
    monkeypatch.setattr(module, "Context", lambda *a: types.SimpleNamespace(settings=types.SimpleNamespace(_enabled=True), registry=None))
    monkeypatch.setattr(module, "load_index", lambda: ({}, {}))
    monkeypatch.setattr(module, "to_engine", lambda *a: {})
    monkeypatch.setattr(module, "apply", lambda *a: False)
    observed = []
    monkeypatch.setattr(module.engine, "process", lambda mv, ctx: observed.append(ctx.settings._enabled) or {"engine_state": "NEEDS_YOU"})
    result = module.run(review_only=True)
    assert observed == [False]
    assert result["errors"] == 0


def test_own_account_transfer_pairing_requires_one_mutual_opposite_leg(runtime):
    module, _ = runtime
    own_a, own_b = "01400010326605", "23659568000109"
    scope_a, scope_b = "scope-a", "scope-b"
    settings = types.SimpleNamespace(scopes={scope_a: "13121 - SNB A", scope_b: "13221 - SNB B"},
                                    company_scopes=frozenset({account_scope(own_a), account_scope(own_b)}))

    def entry(name, account, amount, family, desc, detail):
        row = types.SimpleNamespace(name=name, source_key=name, event_date=dt.date(2026, 11, 8), amount=amount,
                                    account_scope_hash=scope_a if account == own_a else scope_b)
        return {"row": row, "source": {"parser_family": family, "transaction_description": desc,
                                          "detail_description": detail, "direction": "CREDIT" if amount > 0 else "DEBIT"},
                "recognition": {}}

    debit = entry("OUT", own_a, -5000, "INTERNAL_BEN_ID", "Outgoing Internal Transfer", f"{own_b} BEN ID:123456")
    credit = entry("IN", own_b, 5000, "INCOMING_LOCAL", "Incoming Internal Transfer", f"{own_a} DEP ID:123456")
    paired = module.pair_own_transfers({"OUT": debit, "IN": credit}, settings)
    assert paired["OUT"]["name"] == "IN" and paired["IN"]["name"] == "OUT"

    second_credit = entry("IN2", own_b, 5000, "INCOMING_LOCAL", "Incoming Internal Transfer", f"{own_a} DEP ID:654321")
    ambiguous = module.pair_own_transfers({"OUT": debit, "IN": credit, "IN2": second_credit}, settings)
    assert ambiguous == {}


def test_same_amount_matching_requires_every_competing_payee_to_be_verified(runtime):
    module, _ = runtime
    def item(counterparty, route_source="MANUAL"):
        return {"row": types.SimpleNamespace(account_scope_hash="S", event_date="2026-11-10", amount=-1000,
                                             counterparty=counterparty, route_source=route_source), "recognition": {}}
    registry = types.SimpleNamespace(facts=lambda cp: {"status": "ACTIVE", "custody_account": {"A": "13221 - A", "B": "13222 - B"}.get(cp, "")})
    index = {"a": item("A"), "b": item("B")}
    module.mark_unique_verified_payees(index, registry)
    assert index["a"]["unique_statement_payee"] and index["b"]["unique_statement_payee"]
    index = {"a": item("A"), "unknown": item("", "")}
    module.mark_unique_verified_payees(index, registry)
    assert not index["a"].get("unique_statement_payee")
    index = {"a": item("A"), "same": item("A")}
    module.mark_unique_verified_payees(index, registry)
    assert not index["a"]["unique_statement_payee"]
    mixed = types.SimpleNamespace(facts=lambda cp: {"status": "ACTIVE", "custody_account": "13221 - A"} if cp == "A" else {"status": "ACTIVE", "supplier": "SUP-B"})
    index = {"a": item("A"), "b": item("B")}
    module.mark_unique_verified_payees(index, mixed)
    assert not index["a"].get("unique_statement_payee")
    inactive = types.SimpleNamespace(facts=lambda cp: {"status": "INACTIVE", "custody_account": "13221 - A"})
    index = {"a": item("A"), "b": item("B")}
    module.mark_unique_verified_payees(index, inactive)
    assert not index["a"].get("unique_statement_payee")


def test_customer_receipt_invoice_allocation_is_revalidated(runtime):
    module, frappe = runtime
    invoice = types.SimpleNamespace(docstatus=1, company=module.documents.COMPANY, currency="SAR",
                                    customer="CUST-1", outstanding_amount=300,
                                    check_permission=lambda permission: None)
    frappe.get_doc = lambda doctype, name: invoice
    ctx = module.Context.__new__(module.Context)
    mv = {"amount": 500, "payment_reference_doctype": "Sales Invoice", "payment_reference": "INV-1", "payment_reference_amount": 300}
    assert ctx._payment_references(mv, {"party_type": "Customer", "party": "CUST-1"}) == [
        {"reference_doctype": "Sales Invoice", "reference_name": "INV-1", "allocated_amount": 300}]
    invoice.outstanding_amount = 200
    with pytest.raises(ValueError, match="outstanding"):
        ctx._payment_references(mv, {"party_type": "Customer", "party": "CUST-1"})
    invoice.outstanding_amount = 300
    invoice.customer = "OTHER"
    with pytest.raises(ValueError, match="customer"):
        ctx._payment_references(mv, {"party_type": "Customer", "party": "CUST-1"})


def test_batch_routing_never_auto_drafts_even_if_settings_are_enabled(runtime, monkeypatch):
    module, frappe = runtime
    class Settings:
        _enabled = True
        def auto_draft(self, day): return self._enabled
    contexts = []
    def make_context(*args):
        context = types.SimpleNamespace(settings=Settings(), registry=None)
        contexts.append(context)
        return context
    frappe.db = types.SimpleNamespace(sql=lambda *a, **k: [types.SimpleNamespace(name="ROW", event_date="2026-11-09")],
                                      savepoint=lambda *a: None, release_savepoint=lambda *a: None)
    monkeypatch.setattr(module, "Context", make_context)
    monkeypatch.setattr(module, "load_index", lambda: ({"ROW": {"row": {}}}, {}))
    monkeypatch.setattr(module, "mark_unique_verified_payees", lambda *args: None)
    monkeypatch.setattr(module, "pair_own_transfers", lambda *args: {})
    monkeypatch.setattr(module, "to_engine", lambda *args: {})
    monkeypatch.setattr(module, "apply", lambda *args: False)
    seen = []
    monkeypatch.setattr(module.engine, "process", lambda movement, context: seen.append(context.settings.auto_draft(None)) or {"engine_state": "PENDING"})
    module.run(names=["ROW"])
    module.run(names=["ROW"], manual_draft=True)
    assert seen == [False, True]
    assert contexts[1].settings.draft_fees is True


def test_supplier_purchase_order_reference_cannot_exceed_available(runtime):
    module, frappe = runtime
    order = types.SimpleNamespace(docstatus=1, company=module.documents.COMPANY, currency="SAR", supplier="SUP-1", grand_total=1000,
                                  get=lambda field: 400 if field == "advance_paid" else None,
                                  check_permission=lambda permission: None)
    frappe.get_doc = lambda doctype, name: order
    ctx = module.Context.__new__(module.Context)
    mv = {"amount": -700, "payment_reference_doctype": "Purchase Order", "payment_reference": "PO-1", "payment_reference_amount": 600}
    assert ctx._payment_references(mv, {"party_type": "Supplier", "party": "SUP-1"})[0]["allocated_amount"] == 600
    mv["payment_reference_amount"] = 601
    with pytest.raises(ValueError, match="outstanding"):
        ctx._payment_references(mv, {"party_type": "Supplier", "party": "SUP-1"})


def test_petty_cash_draft_rechecks_custody_before_inserting(runtime, monkeypatch):
    module, frappe = runtime
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._active_employee = lambda employee, company: "ACTUAL-CUSTODY"
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    employee = types.SimpleNamespace(check_permission=lambda permission: None)
    created = []
    frappe.get_doc = lambda *args: employee if args[0] == "Employee" else created.append(args)
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "bank"}, draft_fees=False, fee_account="Fees", vat_account="VAT")
    mv = {"key": "K1", "amount": -10, "date": "2026-11-09", "scope": "scope", "source": {}}
    with pytest.raises(ValueError, match="changed"):
        ctx.create("PETTY_CASH", mv, {"employee": "EMP-1", "custody_account": "OLD-CUSTODY", "label": "Employee"}, [])
    assert created == []


def test_reviewed_petty_cash_draft_contains_employee_and_statement_key(runtime, monkeypatch):
    module, frappe = runtime
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._active_employee = lambda employee, company: "CUSTODY"
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    inserted = []
    employee = types.SimpleNamespace(check_permission=lambda permission: None)
    def get_doc(*args):
        if args[0] == "Employee":
            return employee
        body = args[0]
        return types.SimpleNamespace(name="JV-NEW", insert=lambda: inserted.append(body))
    frappe.get_doc = get_doc
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope": "BANK"}, draft_fees=False, fee_account="Fees", vat_account="VAT")
    ctx._existing = lambda *args: None
    registrations = []
    ctx.ledger = types.SimpleNamespace(register=lambda *args: registrations.append(args))
    mv = {"key": "BANK-KEY", "amount": -1000, "date": "2026-11-09", "scope": "scope", "source": {"reference": "REF-1"}}
    assert ctx.create("PETTY_CASH", mv, {"employee": "EMP-1", "custody_account": "CUSTODY", "label": "Employee"}, []) == ("Journal Entry", "JV-NEW")
    assert inserted[0]["custom_pc_employee"] == "EMP-1" and inserted[0]["custom_pc_top_up"] == 1
    assert inserted[0]["custom_pc_statement_key"] == "BANK-KEY" and len(registrations) == 1


def test_explicit_nonemployee_custody_draft_has_no_employee_funding_designation(runtime, monkeypatch):
    module, frappe = runtime
    router = types.ModuleType("sig_warehouse.sig_accounting.snb_movement_router")
    router._verified_custody_account = lambda account: account
    monkeypatch.setitem(sys.modules, router.__name__, router)
    inserted = []
    frappe.get_doc = lambda body: types.SimpleNamespace(name="JV-1", insert=lambda: inserted.append(body))
    ctx = module.Context.__new__(module.Context)
    ctx.settings = types.SimpleNamespace(scopes={"scope":"BANK"}, draft_fees=False, fee_account="FEE", vat_account="VAT")
    ctx._existing = lambda *args: None
    ctx.ledger = types.SimpleNamespace(register=lambda *args: None)
    mv = {"key":"KEY", "amount":-20000, "date":"2026-11-10", "scope":"scope", "source":{}}
    ctx.create("PETTY_CASH", mv, {"employee":"", "custody_account":"1322 - Rajhi", "label":"Owner bank"}, [])
    assert inserted[0]["accounts"][0]["account"] == "1322 - Rajhi"
    assert not inserted[0].get("custom_pc_employee") and not inserted[0].get("custom_pc_top_up")
