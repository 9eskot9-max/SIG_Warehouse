"""API guards, ingestion and party creation, against a fake Frappe. Engine logic is tested elsewhere."""
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.fixture
def api(monkeypatch):
    fake = types.ModuleType("frappe")
    fake._ = lambda value: value
    fake.parse_json = json.loads
    fake.whitelist = lambda **kwargs: (lambda fn: fn)
    fake.session = types.SimpleNamespace(user="9eskot9@gmail.com")
    fake.PermissionError = PermissionError
    fake.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
    fake.has_permission = lambda doctype, permission: True
    fake.get_roles = lambda: ["Accounts Manager"]
    utils = types.ModuleType("frappe.utils")
    utils.flt, utils.now_datetime, utils.nowdate = float, lambda: None, lambda: "2026-11-09"
    fake.utils = utils
    owner = types.ModuleType("sig_warehouse.sig_operations.app_connections")
    owner.TODOIST_OWNER = "9eskot9@gmail.com"
    runtime = types.ModuleType("sig_warehouse.sig_accounting.bank_router.runtime")
    runtime.documents = types.SimpleNamespace(COMPANY="Co")
    runtime.run = lambda *a, **k: {"processed": 0}
    runtime.identity_key = lambda kind, value: f"{kind}|{value}"
    for name, module in (("frappe", fake), ("frappe.utils", utils), (owner.__name__, owner), (runtime.__name__, runtime)):
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.syspath_prepend(str(ROOT))
    path = ROOT / "sig_warehouse/sig_accounting/snb_movement_router.py"
    spec = importlib.util.spec_from_file_location("router_api_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Doc:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.flags = types.SimpleNamespace()

    def check_permission(self, permission):
        pass

    def save(self):
        self.saved = True

    def get(self, key):
        return getattr(self, key, None)

    def set(self, key, value):
        setattr(self, key, value)


def test_purpose_defaults_are_scoped(api):
    cp = {"purpose_defaults_json": '{"XXMT":"PAYMENT_ENTRY","XXSC":"JOURNAL_ENTRY"}', "default_treatment": "FINANCE_HANDLES"}
    assert api._purpose_default(cp, "XXMT") == "PAYMENT_ENTRY"
    assert api._purpose_default(cp, "XXSC") == "JOURNAL_ENTRY"
    assert api._purpose_default(cp, "XXMR") == ""
    assert api._purpose_default(cp, "") == "FINANCE_HANDLES"
    cp["purpose_defaults_json"] = '{"XXMT":{"treatment":"JOURNAL_ENTRY","account":"MAINT"}}'
    assert api._purpose_default(cp, "XXMT") == "JOURNAL_ENTRY"


def test_remember_business_route_requires_matching_party_and_direction(api):
    cp = Doc(employee="", confirmed_routes=[])
    def append(field, values):
        row = Doc(**values)
        row.update = lambda updates: row.__dict__.update(updates)
        cp.confirmed_routes.append(row)
        return row
    cp.append = append
    movement = Doc(direction="DEBIT")
    target = {"business_route": "supplier", "business_purpose": "XXMR"}
    with pytest.raises(ValueError, match="Supplier"):
        api._remember_business_route(cp, movement, target, "PAYMENT_ENTRY", {"party_type": "Customer", "party": "C1"})
    assert cp.confirmed_routes == []
    api._remember_business_route(cp, movement, target, "PAYMENT_ENTRY", {"party_type": "Supplier", "party": "S1"})
    assert cp.confirmed_routes[0].route == "supplier"
    assert cp.confirmed_routes[0].confirmed_by == "9eskot9@gmail.com"
    with pytest.raises(ValueError, match="direction"):
        api._remember_business_route(cp, Doc(direction="CREDIT"), target, "PAYMENT_ENTRY", {"party_type": "Supplier", "party": "S1"})


def test_entry_preview_checks_linked_account_access(api, monkeypatch):
    movement = Doc(erp_doctype="Journal Entry", erp_document="JV-1", modified="movement-v1")
    entry = Doc(name="JV-1", modified="entry-v1", docstatus=0, posting_date="2026-11-10", accounts=[
        Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=50, account_currency="SAR"),
        Doc(account="EXPENSE", debit_in_account_currency=50, credit_in_account_currency=0, account_currency="SAR"),
    ])
    entry.has_permission = lambda permission: permission == "submit"
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda doctype, name: movement if doctype == api.DOCTYPE else entry, raising=False)
    checked = []
    monkeypatch.setattr(api, "_check_link", lambda doctype, name: checked.append((doctype, name)))
    preview = api.preview_linked_document("movement")
    assert preview["can_submit"] is True
    assert preview["lines"][0]["credit"] == 50
    assert checked == [("Account", "BANK"), ("Account", "EXPENSE")]


def test_route_preview_includes_fee_and_vat_accounts(api, monkeypatch):
    movement = Doc(name="M1", direction="DEBIT", amount=-100, currency="SAR", account_scope_hash="scope")
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda doctype, name: movement, raising=False)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(get_value=lambda *args, **kwargs: {"account": "ok"}), raising=False)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_expense_account_allowed", lambda *args, **kwargs: True)
    monkeypatch.setattr(api.runtime, "Settings", lambda: types.SimpleNamespace(scopes={"scope": "BANK"}, fee_account="FEE", vat_account="VAT"), raising=False)
    monkeypatch.setattr(api, "_fees_for", lambda names: {"M1": [{"amount": -1, "family": "BANK_FEE"}, {"amount": -.15, "family": "FEE_VAT"}]})
    preview = api.preview_route("M1", {"treatment": "JOURNAL_ENTRY", "account": "EXPENSE"})
    assert (preview["debit"], preview["credit"]) == ("EXPENSE", "BANK")
    assert [(line["debit"], line["credit"]) for line in preview["fees"]] == [("FEE", "BANK"), ("VAT", "BANK")]


def test_posting_requires_bank_amount_and_submit_permission(api, monkeypatch):
    movement = Doc(erp_doctype="Journal Entry", erp_document="JV-1", name="M1", amount=-100, engine_state="DRAFT_READY", decision_type="")
    movement.append = lambda *args: None
    entry = Doc(doctype="Journal Entry", name="JV-1", docstatus=0, company="Co",
                accounts=[Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=90)])
    submitted = []
    entry.submit = lambda: submitted.append(entry.name)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None), raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: entry, raising=False)
    monkeypatch.setattr(api, "_bank_gl", lambda *args: "BANK")
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    with pytest.raises(ValueError, match="bank account and amount"):
        api.post_reviewed_draft("M1", "modified")
    assert submitted == []


def test_posting_checks_document_submit_permission_before_submit(api, monkeypatch):
    movement = Doc(erp_doctype="Journal Entry", erp_document="JV-1", name="M1", amount=-100, engine_state="DRAFT_READY", decision_type="")
    entry = Doc(doctype="Journal Entry", name="JV-1", docstatus=0, company="Co", accounts=[])
    def check(permission):
        if permission == "submit":
            raise PermissionError("submit denied")
    entry.check_permission = check
    submitted = []
    entry.submit = lambda: submitted.append(True)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None), raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: entry, raising=False)
    with pytest.raises(PermissionError, match="submit denied"):
        api.post_reviewed_draft("M1", "modified")
    assert submitted == []


def test_fee_validation_requires_distinct_bank_lines(api):
    entry = Doc(accounts=[Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=100),
                          Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=1)])
    fees = [{"amount": -1}, {"amount": -1}]
    assert not api._fee_lines_match(entry, "BANK", fees, -100)
    entry.accounts.append(Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=1))
    assert api._fee_lines_match(entry, "BANK", fees, -100)
    entry.accounts.append(Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=50))
    assert not api._fee_lines_match(entry, "BANK", fees, -100)


def test_changed_reviewed_draft_cannot_be_posted(api, monkeypatch):
    movement = Doc(erp_doctype="Journal Entry", erp_document="JV-1", engine_state="DRAFT_READY", decision_type="")
    entry = Doc(name="JV-1", modified="new-version")
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None), raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: entry, raising=False)
    with pytest.raises(ValueError, match="changed after review"):
        api.post_reviewed_draft("M1", "v1", "JV-1", "old-version")


def test_changed_reviewed_accounts_cannot_create_draft(api, monkeypatch):
    monkeypatch.setattr(api, "preview_route", lambda *args: {"debit": "NEW"})
    with pytest.raises(ValueError, match="accounts changed"):
        api.decide_business_route("M1", "v1", {"reviewed_preview": {"debit": "OLD"}}, "draft")


def test_confirmation_fee_snapshot_uses_current_accounts(api, monkeypatch):
    monkeypatch.setattr(api, "_fees_for", lambda names: {"M1": [{"family": "FEE_VAT", "amount": -0.15}]})
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    settings = types.SimpleNamespace(vat_account="VAT-2", fee_account="FEE")
    assert api._confirmation_fees({"fee_parent": "M1"}, settings) == [{"account": "VAT-2", "family": "FEE_VAT", "amount": -0.15}]


def test_fee_creation_requires_configured_vat_account(api, monkeypatch):
    settings = types.SimpleNamespace(fee_account="FEE", vat_account="")
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(get_value=lambda *args, **kwargs:
        types.SimpleNamespace(company="Co", is_group=0, disabled=0)), raising=False)
    with pytest.raises(ValueError, match="fee and VAT accounts"):
        api._validate_fee_accounts(settings, [{"family": "FEE_VAT", "amount": -.15}])


def test_posting_own_transfer_updates_both_legs(api, monkeypatch):
    first = Doc(name="M1", direction="DEBIT", amount=-100, currency="SAR", erp_doctype="Journal Entry",
                erp_document="JV-1", engine_state="DRAFT_READY", decision_type="", link_method="OWN_TRANSFER",
                signals_json='{"paired_transfer":{"name":"M2"}}')
    other = Doc(name="M2", direction="CREDIT", amount=100, currency="SAR", erp_doctype="Journal Entry", erp_document="JV-1")
    for row in (first, other):
        row.append = lambda *args: None
    entry = Doc(doctype="Journal Entry", name="JV-1", docstatus=0, company="Co", accounts=[
        Doc(account="BANK1", debit_in_account_currency=0, credit_in_account_currency=100),
        Doc(account="BANK2", debit_in_account_currency=100, credit_in_account_currency=0),
    ])
    posted = []
    entry.submit = lambda: posted.append("JV-1")
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api, "_lock", lambda *args: first)
    monkeypatch.setattr(api.frappe, "get_doc", lambda doctype, name: entry if doctype == "Journal Entry" else other, raising=False)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None, savepoint=lambda *args: None,
                         release_savepoint=lambda *args: None, rollback=lambda **kwargs: None), raising=False)
    monkeypatch.setattr(api, "_bank_gl", lambda row: "BANK1" if row.name == "M1" else "BANK2")
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_fees_for", lambda names: {})
    api.post_reviewed_draft("M1", "t")
    assert posted == ["JV-1"]
    assert first.engine_state == other.engine_state == "POSTED"


def test_posting_payment_and_fee_failure_rolls_back_both(api, monkeypatch):
    movement = Doc(name="M1", direction="DEBIT", amount=-100, currency="SAR", erp_doctype="Payment Entry",
                   erp_document="PE-1", engine_state="DRAFT_READY", decision_type="", link_method="AUTO_DRAFT",
                   source_json='{"statement_key":"KEY"}', counterparty="")
    movement.append = lambda *args: None
    payment = Doc(doctype="Payment Entry", name="PE-1", docstatus=0, company="Co", paid_from="BANK", paid_to="SUP", paid_amount=100, received_amount=100)
    fee = Doc(doctype="Journal Entry", name="FEE-1", docstatus=0, company="Co", custom_pc_statement_key="KEY#FEE",
              accounts=[Doc(account="BANK", debit_in_account_currency=0, credit_in_account_currency=1)])
    fee_movement = Doc(name="FM1", parent_movement="M1", erp_document="", erp_doctype="")
    payment.submit = lambda: None
    fee.submit = lambda: (_ for _ in ()).throw(ValueError("Fee failed"))
    rollbacks = []
    db = types.SimpleNamespace(sql=lambda *args: None, savepoint=lambda *args: None,
        release_savepoint=lambda *args: None, rollback=lambda **kwargs: rollbacks.append(kwargs), get_value=lambda *args, **kwargs: "FEE-1")
    monkeypatch.setattr(api.frappe, "db", db, raising=False)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda doctype, name: payment if doctype == "Payment Entry" else fee if doctype == "Journal Entry" else fee_movement, raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_bank_gl", lambda *args: "BANK")
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_fees_for", lambda names: {"M1": [{"name": "FM1", "amount": -1}]})
    monkeypatch.setattr(api.runtime.documents, "FEE_MARKER_SUFFIX", "#FEE", raising=False)
    with pytest.raises(ValueError, match="Fee failed"):
        api.post_reviewed_draft("M1", "t")
    assert rollbacks == [{"save_point": "bank_router_post_reviewed"}]
    assert movement.engine_state == "DRAFT_READY"


def test_decide_keeps_draft_when_posting_fails(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api, "route_movement", lambda *args: {"movement": {"name": "M1", "modified": "1", "decision_type": "CREATE_DRAFT"}})
    monkeypatch.setattr(api, "create_reviewed_draft", lambda *args: {"name": "M1", "modified": "2", "erp_doctype": "Journal Entry", "erp_document": "JV-1", "doc_status": 0, "engine_state": "DRAFT_READY", "decision_type": ""})
    def fail_post(*args):
        raise ValueError("Fee journal missing")
    monkeypatch.setattr(api, "post_reviewed_draft", fail_post)
    result = api.decide_business_route("M1", "0", {"business_route": "other_out", "treatment": "JOURNAL_ENTRY"}, "post")
    assert result["status"] == "draft"
    assert result["movement"]["erp_document"] == "JV-1"
    assert "Fee journal missing" in result["post_error"]


def test_decide_never_posts_a_draft_with_an_unresolved_mismatch(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api, "route_movement", lambda *args: {"movement": {"erp_document": "PE-1", "erp_doctype": "Payment Entry", "doc_status": 0, "engine_state": "NEEDS_YOU", "decision_type": "TREATMENT_MISMATCH"}})
    posted = []
    monkeypatch.setattr(api, "post_reviewed_draft", lambda *args: posted.append(True))
    with pytest.raises(ValueError, match="remaining review"):
        api.decide_business_route("M1", "0", {"business_route": "other_out", "treatment": "JOURNAL_ENTRY"}, "post")
    assert posted == []


def test_decide_post_requires_submit_permission_before_any_write(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda doctype, permission, *args: permission != "submit")
    writes = []
    monkeypatch.setattr(api, "route_movement", lambda *args: writes.append(True))
    with pytest.raises(PermissionError, match="permission to submit"):
        api.decide_business_route("M1", "0", {"business_route": "other_out", "treatment": "JOURNAL_ENTRY"}, "post")
    assert writes == []


def test_business_decision_routes_remembers_and_creates_a_draft(api, monkeypatch):
    movement = Doc(name="M1", modified="v1", direction="DEBIT", kind="UNKNOWN", engine_state="NEEDS_YOU",
                   decision_type="CHOOSE_TREATMENT", accounting_treatment="", accounting_account="", counterparty="",
                   route_source="", erp_document="", erp_doctype="", link_method="", signals_json="{}", recognition_json="{}",
                   payment_reference="", source_json='{"statement_key":"KEY"}')
    movement.append = lambda *args: None
    cp = Doc(name="CP1", status="ACTIVE", employee="", is_company=0, confirmed_routes=[], purpose_defaults_json="", expense_account="")
    cp.save = lambda **kwargs: None
    def append(field, values):
        row = Doc(**values)
        row.update = lambda updates: row.__dict__.update(updates)
        cp.confirmed_routes.append(row)
        return row
    cp.append = append
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None,
        get_value=lambda *args, **kwargs: {"company": "Co", "is_group": 0, "disabled": 0, "account_type": ""}), raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *args: None)
    monkeypatch.setattr(api, "_retarget_draft", lambda *args: None)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_bank_gl", lambda *args: "BANK")
    monkeypatch.setattr(api, "_fees_for", lambda names: {})
    def run(*args, **kwargs):
        if kwargs.get("manual_draft"):
            movement.erp_doctype, movement.erp_document = "Journal Entry", "JV-1"
            movement.engine_state, movement.decision_type = "DRAFT_READY", ""
        else:
            movement.decision_type = "CREATE_DRAFT"
        return {"errors": 0}
    api.runtime.run = run
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name, "modified": movement.modified,
        "erp_doctype": movement.erp_doctype, "erp_document": movement.erp_document,
        "engine_state": movement.engine_state, "decision_type": movement.decision_type,
        "doc_status": 0 if movement.erp_document else None})
    target = {"business_route": "other_out", "business_purpose": "OTHER_OUT", "type": "EXPENSE",
              "treatment": "JOURNAL_ENTRY", "account": "EXPENSE", "remember_default": "1"}
    result = api.decide_business_route("M1", "v1", target, "draft")
    assert result["status"] == "draft" and result["movement"]["erp_document"] == "JV-1"
    assert movement.business_route == "other_out" and movement.business_purpose == "OTHER_OUT"
    assert cp.confirmed_routes[0].route == "other_out" and cp.confirmed_routes[0].account == "EXPENSE"


def test_employee_advance_confirms_employee_without_marking_petty_cash(api, monkeypatch):
    movement = Doc(name="M1", modified="v1", direction="DEBIT", kind="UNKNOWN", accounting_treatment="",
                   accounting_account="", counterparty="", route_source="", erp_document="", erp_doctype="",
                   link_method="", signals_json="{}", recognition_json="{}", payment_reference="")
    movement.append = lambda *args: None
    cp = Doc(name="CP1", status="ACTIVE", employee="", is_company=0, confirmed_routes=[], purpose_defaults_json="", expense_account="")
    cp.save = lambda **kwargs: None
    def append(field, values):
        row = Doc(**values)
        row.update = lambda updates: row.__dict__.update(updates)
        cp.confirmed_routes.append(row)
        return row
    cp.append = append
    def get_value(doctype, *args, **kwargs):
        if doctype == "Employee":
            return types.SimpleNamespace(status="Active", company="Co")
        return {"company": "Co", "is_group": 0, "disabled": 0, "account_type": ""}
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None, get_value=get_value), raising=False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_bank_gl", lambda *args: "BANK")
    monkeypatch.setattr(api, "_learn_identifiers", lambda *args: None)
    monkeypatch.setattr(api, "_retarget_draft", lambda *args: None)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name})
    api.runtime.run = lambda *args, **kwargs: {"errors": 0}
    target = {"business_route": "employee_advance", "business_purpose": "XXHR", "type": "EXPENSE", "employee": "EMP-1",
              "treatment": "JOURNAL_ENTRY", "account": "1321", "remember_default": "1"}
    api.route_movement("M1", "v1", target)
    assert cp.employee == "EMP-1" and cp.confirmed_routes[0].route == "employee_advance"
    assert cp.confirmed_routes[0].petty_cash == 0
    assert "finance_petty_cash" not in json.loads(movement.recognition_json)


def test_confirmation_candidate_needs_a_mapped_biller(api, monkeypatch):
    doc = Doc(name="M1", erp_document="", parent_movement="", kind="EXPENSE_PAYMENT", direction="DEBIT", account_scope_hash="scope",
              source_json='{"parser_family":"SADAD"}', signals_json='{"biller_code":"050"}')
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    settings = types.SimpleNamespace(scopes={"scope": "BANK"}, billers={"050": "IQAMA"})
    candidate = api._confirmation_candidate(doc, settings)
    assert candidate["debit"] == "IQAMA"
    assert candidate["credit"] == "BANK"
    settings.billers.clear()
    assert api._confirmation_candidate(doc, settings) is None


@pytest.mark.parametrize("route", ["own_ledger", "bank_service"])
def test_confirmation_requires_unambiguous_confirmed_memory(api, monkeypatch, route):
    doc = Doc(name="M1", erp_document="", parent_movement="", kind="UNKNOWN", direction="DEBIT",
              account_scope_hash="scope", source_json="{}", signals_json="{}", counterparty="CP1",
              recognition_json="{}", decision_type="CHOOSE_TREATMENT")
    row = Doc(confirmed_by="finance", purpose=route.upper(), route=route, direction="DEBIT", account="LEDGER",
              party="", party_type="", petty_cash=0)
    cp = Doc(status="ACTIVE", confirmed_routes=[row])
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: cp, raising=False)
    settings = types.SimpleNamespace(scopes={"scope": "BANK"}, billers={})
    assert api._confirmation_candidate(doc, settings)["debit"] == "LEDGER"
    row.confirmed_by = ""
    assert api._confirmation_candidate(doc, settings) is None
    row.confirmed_by = "finance"
    doc.decision_type = "PICK_DOCUMENT"
    assert api._confirmation_candidate(doc, settings) is None


def test_bulk_confirmation_holds_changed_fee_account(api, monkeypatch):
    doc = Doc(name="M1", modified="v1")
    db = types.SimpleNamespace(savepoint=lambda *args: None, rollback=lambda **kwargs: None, release_savepoint=lambda *args: None)
    monkeypatch.setattr(api.frappe, "db", db, raising=False)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: doc, raising=False)
    monkeypatch.setattr(api.runtime, "Settings", lambda: object(), raising=False)
    monkeypatch.setattr(api, "_confirmation_candidate", lambda *args: {"kind": "bill", "debit": "EXP", "credit": "BANK"})
    monkeypatch.setattr(api, "_confirmation_fees", lambda *args: [{"account": "NEW"}])
    result = api.bulk_confirm_routes([{"name": "M1", "modified": "v1", "reviewed_accounts": ["EXP", "BANK"],
                                       "reviewed_fees": [{"account": "OLD"}]}], "post")
    assert result["items"][0]["status"] == "held"
    assert "fees changed" in result["items"][0]["error"]


def test_confirmation_pair_is_excluded_from_regular_queues(api, monkeypatch):
    primary = Doc(name="M1", signals_json='{"paired_transfer":{"name":"M2"}}')
    monkeypatch.setattr(api, "_confirmation_candidates", lambda *args: [(primary, {"kind": "own_transfer"})])
    calls = []
    def get_list(doctype, **kwargs):
        calls.append(kwargs)
        return []
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    monkeypatch.setattr(api, "_fees_for", lambda names: {})
    monkeypatch.setattr(api, "_doc_status", lambda rows: {})
    result = api.list_inbox()
    assert calls[0]["filters"]["name"] == ["not in", ["M1", "M2"]]
    assert result["counts"]["confirm"] == 1


def test_bulk_confirmation_rejects_duplicate_rows(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    with pytest.raises(ValueError, match="once"):
        api.bulk_confirm_routes([{"name": "M1"}, {"name": "M1"}], "draft")


def test_bulk_confirmation_holds_one_failure_and_continues(api, monkeypatch):
    docs = {name: Doc(name=name, modified="v1", signals_json="{}") for name in ("M1", "M2")}
    rollbacks = []
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda doctype, name: docs[name], raising=False)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(savepoint=lambda *args: None,
                         rollback=lambda **kwargs: rollbacks.append(kwargs), release_savepoint=lambda *args: None), raising=False)
    monkeypatch.setattr(api.runtime, "Settings", lambda: object(), raising=False)
    monkeypatch.setattr(api, "_confirmation_candidate", lambda *args: {"kind": "bill", "account": "EXPENSE"})
    def decide(name, *args):
        if name == "M1":
            raise ValueError("changed")
        return {"status": "draft", "movement": {"erp_document": "JV-2"}}
    monkeypatch.setattr(api, "decide_business_route", decide)
    result = api.bulk_confirm_routes([{"name": "M1", "modified": "v1"}, {"name": "M2", "modified": "v1"}], "draft")
    assert [row["status"] for row in result["items"]] == ["held", "draft"]
    assert rollbacks == [{"save_point": "bank_router_bulk_0"}]


def test_bulk_sadad_reuses_verified_biller_counterparty(api, monkeypatch):
    doc = Doc(name="M1", modified="v1", signals_json='{"biller_code":"050"}')
    db = types.SimpleNamespace(savepoint=lambda *args: None, rollback=lambda **kwargs: None,
                               release_savepoint=lambda *args: None,
                               get_value=lambda *args, **kwargs: types.SimpleNamespace(counterparty="CP-050", status="ACTIVE"))
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: doc, raising=False)
    monkeypatch.setattr(api.frappe, "db", db, raising=False)
    monkeypatch.setattr(api.runtime, "Settings", lambda: object(), raising=False)
    monkeypatch.setattr(api, "_confirmation_candidate", lambda *args: {"kind": "bill", "account": "EXPENSE"})
    selected = []
    def decide(name, modified, target, mode):
        selected.append(target["counterparty"])
        return {"status": "draft", "movement": {"erp_document": "JV-1"}}
    monkeypatch.setattr(api, "decide_business_route", decide)
    result = api.bulk_confirm_routes([{"name": "M1", "modified": "v1"}], "draft")
    assert selected == ["CP-050"]
    assert result["items"][0]["status"] == "draft"


def test_legacy_snapshot_is_stable_and_detects_changed_choices(api):
    cp = Doc(status="ACTIVE", purpose_defaults_json='{"XXMR":{"treatment":"PAYMENT_ENTRY"}}',
             employee="", custody_account="", supplier="SUP-1", confirmed_routes=[])
    first = api._legacy_route_snapshot(cp)
    assert first["proposals"][0]["party"] == "SUP-1"
    assert first["digest"] == api._legacy_route_snapshot(cp)["digest"]
    cp.supplier = "SUP-2"
    assert first["digest"] != api._legacy_route_snapshot(cp)["digest"]


def test_legacy_migration_requires_unchanged_preview_and_is_not_replayed(api, monkeypatch):
    cp = Doc(name="CP1", status="ACTIVE", purpose_defaults_json='{"XXMR":{"treatment":"PAYMENT_ENTRY"}}',
             employee="", custody_account="", supplier="SUP-1", confirmed_routes=[])
    def append(field, values):
        row = Doc(**values)
        cp.confirmed_routes.append(row)
        return row
    cp.append = append
    cp.save = lambda **kwargs: None
    monkeypatch.setattr(api, "_integration_only", lambda: None)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True)
    monkeypatch.setattr(api.frappe, "get_doc", lambda *args: cp, raising=False)
    monkeypatch.setattr(api.frappe, "db", types.SimpleNamespace(sql=lambda *args: None, get_value=lambda *args, **kwargs: False), raising=False)
    digest = api._legacy_route_snapshot(cp)["digest"]
    result = api.apply_legacy_route_migration([{"counterparty": "CP1", "digest": digest}])
    assert result["counterparties"][0]["created"] == 1
    assert cp.confirmed_routes[0].source == "MIGRATED"
    with pytest.raises(ValueError, match="changed since preview"):
        api.apply_legacy_route_migration([{"counterparty": "CP1", "digest": digest}])
    assert len(cp.confirmed_routes) == 1


def test_pc_suggestion_requires_exact_mapping_and_permissions(api, monkeypatch):
    doc = Doc(kind="PETTY_CASH")
    cp = {"am_key": "beneficiary-1"}
    mapping = {"source": "Sheet Am matched beneficiary", "beneficiary_key": "beneficiary-1", "erp_party": "Employee: Abid Saeed | 13221"}
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    def get_list(doctype, **kwargs):
        return [{"name": "13221 - Custody - Co"}] if doctype == "Account" else [{"name": "EMP-1", "employee_name": "Abid Saeed"}]
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    assert api._suggest_pc_employee(doc, mapping, cp) == {"employee": "EMP-1", "name": "Abid Saeed", "account": "13221 - Custody - Co"}
    assert api._suggest_pc_employee(doc, {**mapping, "beneficiary_key": "other"}, cp) is None
    assert api._suggest_pc_employee(doc, {**mapping, "erp_party": "Employee: Different Name | 13221"}, cp) is None
    arabic = {**mapping, "erp_party": "Employee: محمد عثمان | 13221"}
    assert api._suggest_pc_employee(doc, arabic, cp)["employee"] == "EMP-1"
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: False)
    assert api._suggest_pc_employee(doc, mapping, cp) is None


def test_pc_suggestion_rejects_ambiguous_custody(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    monkeypatch.setattr(api.frappe, "get_list", lambda *args, **kwargs: [{"name": "a"}, {"name": "b"}], raising=False)
    assert api._suggest_pc_employee(Doc(kind="PETTY_CASH"), {"source": "Sheet Am matched beneficiary", "beneficiary_key": "a", "erp_party": "Employee: Abid | 13221"}, {"am_key": "a"}) is None


def test_only_the_integration_owner_may_run_the_engine_or_read_links(api):
    api.frappe.session.user = "someone@example.com"
    for call in (lambda: api.run_engine("main"), lambda: api.list_links(), lambda: api.sync_counterparties([])):
        with pytest.raises(PermissionError):
            call()


def test_list_links_returns_posted_status_and_exact_rejected_hints(api):
    rows = [
        types.SimpleNamespace(name="A", source_key="SNB-A", erp_doctype="Payment Entry", erp_document="ACC-PAY-1",
                              link_method="AUTO_DRAFT", signals_json="{}", candidates_json='{"rejected":[]}'),
        types.SimpleNamespace(name="B", source_key="SNB-B", erp_doctype="", erp_document="", link_method="",
                              signals_json="{}", candidates_json='{"rejected":["ACC-JV-OLD"]}'),
    ]
    api.frappe.get_all = lambda doctype, **kwargs: (
        rows if doctype == api.DOCTYPE else [types.SimpleNamespace(name="ACC-PAY-1", docstatus=1)]
    )
    result = api.list_links()
    assert result["rows"] == [
        {"source_key": "SNB-A", "erp_doctype": "Payment Entry", "erp_document": "ACC-PAY-1", "link_method": "AUTO_DRAFT",
         "doc_status": 1, "am_link_rejected": False, "rejected_documents": []},
        {"source_key": "SNB-B", "erp_doctype": "", "erp_document": "", "link_method": "",
         "doc_status": None, "am_link_rejected": False, "rejected_documents": ["ACC-JV-OLD"]},
    ]
    assert result["has_more"] is False and result["next_start"] == 2


def test_engine_rejects_an_unknown_phase(api):
    with pytest.raises(ValueError):
        api.run_engine("everything")


def test_ingest_is_idempotent_and_keeps_derived_evidence_refreshable(api):
    source = {"event_date": "2026-11-09", "direction": "DEBIT", "signed_amount": -5}
    name = hashlib.sha256(b"SNB-row").hexdigest()
    doc = Doc(source_key="SNB-row", source_json=api._json(source), recognition_json="{}", erp_hint_json="{}", account_scope_hash="")
    api.frappe.db = types.SimpleNamespace(exists=lambda *a: True, sql=lambda *a: None)
    api.frappe.get_doc = lambda *a: doc
    item = {"id": "SNB-row", "source": source, "recognition": {"related_main_id": "SNB-main", "category": "XXPC"}}
    assert api.ingest([item]) == [{"id": "SNB-row", "status": "DERIVED_UPDATED", "name": name}]
    assert json.loads(doc.recognition_json) == {"category": "XXPC", "related_main_id": "SNB-main"}
    assert api.ingest([item])[0]["status"] == "EXISTS"
    assert api.ingest([{**item, "source": {**source, "direction": "CREDIT"}}])[0]["status"] == "SOURCE_CONFLICT"
    assert doc.source_json == api._json(source), "source evidence never changes"


def test_ingest_allows_only_the_legacy_parser_family_enrichment(api):
    legacy = {"event_date": "2026-11-09", "direction": "DEBIT", "signed_amount": -5}
    source = {**legacy, "parser_family": "BANK_FEE"}
    name = hashlib.sha256(b"SNB-row").hexdigest()
    doc = Doc(source_key="SNB-row", source_json=api._json(legacy), recognition_json="{}", erp_hint_json="{}", account_scope_hash="")
    api.frappe.db = types.SimpleNamespace(exists=lambda *a: True, sql=lambda *a: None)
    api.frappe.get_doc = lambda *a: doc
    item = {"id": "SNB-row", "source": source, "account_scope_hash": "a" * 64,
            "recognition": {"related_fee_rows": [], "category": "XXPC"}}
    result = api.ingest([item])
    assert result == [{"id": "SNB-row", "status": "DERIVED_UPDATED", "name": name}]
    assert json.loads(doc.source_json) == source
    assert doc.account_scope_hash == "a" * 64
    assert api.ingest([item])[0]["status"] == "EXISTS"
    changed = {**source, "signed_amount": -6}
    assert api.ingest([{**item, "source": changed}])[0]["status"] == "SOURCE_CONFLICT"


def test_ingest_hint_conflict_and_scope_rules(api):
    source = {"event_date": "2026-11-09", "direction": "CREDIT"}
    scope = "a" * 64
    doc = Doc(source_key="SNB-row", source_json=api._json(source), recognition_json="{}", erp_hint_json=api._json({"linked_doc": "ACC-JV-1"}), account_scope_hash=scope)
    api.frappe.db = types.SimpleNamespace(exists=lambda *a: True, sql=lambda *a: None)
    api.frappe.get_doc = lambda *a: doc
    item = {"id": "SNB-row", "source": source}
    assert api.ingest([{**item, "erp": {"linked_doc": "ACC-JV-2"}}])[0]["status"] == "HINT_CONFLICT"
    assert api.ingest([{**item, "account_scope_hash": "b" * 64}])[0]["status"] == "ACCOUNT_SCOPE_CONFLICT"
    with pytest.raises(ValueError):
        api.ingest([{**item, "account_scope_hash": "nothex"}])


def test_new_party_refuses_an_existing_exact_name_and_applies_defaults(api):
    row = types.SimpleNamespace(name="CUST-1", customer_name="Khutut Co")
    row.get = lambda key: row.customer_name
    api.frappe.get_list = lambda *a, **k: [row]
    with pytest.raises(ValueError, match="already exists: CUST-1"):
        api._new_party("Customer", "  khutut  co ")
    created = {}
    class Inserted(Doc):
        name = "CUST-2"
        def insert(self):
            created.update(self.__dict__)
    api.frappe.get_list = lambda *a, **k: []
    api.frappe.get_doc = lambda values: Inserted(**values)
    assert api._new_party("Supplier", "New Supplier Ltd", "300123") == "CUST-2"
    assert created["supplier_group"] == "Local" and created["supplier_type"] == "Company" and created["tax_id"] == "300123"
    api.frappe.db = types.SimpleNamespace(exists=lambda doctype, name: doctype == "Country" and name == "Saudi Arabia")
    api._check_link = lambda *args: None
    with pytest.raises(ValueError, match="valid country"):
        api._new_party("Customer", "New Customer Ltd")
    assert api._new_party("Customer", "New Customer Ltd", country="Saudi Arabia") == "CUST-2"
    assert created["custom_country"] == "Saudi Arabia"
    with pytest.raises(ValueError):
        api._new_party("Supplier", "ab")


def test_routing_requires_a_treatment_and_checks_party_type(api):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None)
    doc = Doc(modified="t", kind="OWN_TRANSFER", signals_json="{}", counterparty="", accounting_treatment="")
    api.frappe.get_doc = lambda *a: doc
    with pytest.raises(ValueError, match="Choose Payment Entry"):
        api.route_movement("n", "t", {"type": "PARTY"})
    doc.kind = "CUSTOMER_RECEIPT"
    doc.direction = "CREDIT"
    api.frappe.db.exists = lambda *a: False
    api._ensure_counterparty = lambda *args: Doc(name="CP")
    with pytest.raises(ValueError, match="take a Customer"):
        api.route_movement("n", "t", {"type": "PARTY", "treatment": "PAYMENT_ENTRY", "party_type": "Supplier", "party": "S"})
    with pytest.raises(ValueError, match="changed since"):
        api.route_movement("n", "stale", {"type": "PARTY"})


def test_sadad_route_can_reuse_an_existing_active_counterparty(api):
    selected = Doc(name="YANAL-CP", status="ACTIVE")
    seen = []
    selected.check_permission = lambda permission: seen.append(permission)
    api.frappe.db = types.SimpleNamespace(exists=lambda doctype, name: False)
    api.frappe.get_doc = lambda doctype, name: selected

    result = api._ensure_counterparty(Doc(counterparty=""), "SaudiOrix", "YANAL-CP")

    assert result is selected
    assert seen == ["read"]


def test_counterparty_route_does_not_silently_switch_an_existing_link(api):
    api.frappe.db = types.SimpleNamespace(exists=lambda doctype, name: True)
    doc = Doc(counterparty="OLD-CP")
    with pytest.raises(ValueError, match="already has a linked counterparty"):
        api._ensure_counterparty(doc, "Yanal", "OTHER-CP")


def test_unlink_remembers_the_wrong_document(api):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None)
    doc = Doc(name="n", modified="t", erp_document="JV-1", erp_doctype="Journal Entry", link_method="LEDGER", candidates_json="{}", engine_state="DRAFT_READY")
    doc.append = lambda *a, **k: None
    api.frappe.get_doc = lambda *a: doc
    api.get_movement = lambda name: {"ok": True}
    assert api.unlink_movement("n", "t") == {"ok": True}
    assert json.loads(doc.candidates_json)["rejected"] == ["JV-1"]
    assert (doc.erp_document, doc.engine_state) == ("", "PENDING")


def test_pick_only_accepts_an_offered_candidate(api):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None)
    doc = Doc(name="n", modified="t", candidates_json=json.dumps({"documents": [{"doctype": "Journal Entry", "name": "JV-1"}]}))
    doc.append = lambda *a, **k: None
    api.frappe.get_doc = lambda *a: doc
    api.get_movement = lambda name: {"ok": True}
    with pytest.raises(ValueError, match="not offered"):
        api.pick_document("n", "t", "Journal Entry", "JV-9")
    api.pick_document("n", "t", "Journal Entry", "JV-1")
    assert (doc.erp_document, doc.link_method) == ("JV-1", "MANUAL")


def test_accounts_user_cannot_create_a_supplier_and_is_told_so(api):
    api.frappe.get_list = lambda *a, **k: []
    api.frappe.has_permission = lambda doctype, permission: not (doctype == "Supplier" and permission == "create")
    with pytest.raises(PermissionError, match="cannot create a new Supplier"):
        api._new_party("Supplier", "Brand New Supplier Co")
    assert api.frappe.has_permission("Customer", "create") is True


def test_retarget_saves_router_draft_with_normal_write_permission(api, monkeypatch):
    permissions = []
    class Payment(Doc):
        def check_permission(self, permission):
            permissions.append(permission)
        def save(self):
            assert not getattr(self.flags, "ignore_permissions", False)
            self.saved = True
    payment = Payment(custom_snb_idempotency_key="K1", company="Co", payment_type="Pay", accounts=[])
    api.frappe.db = types.SimpleNamespace(get_value=lambda doctype, name, *args, **kwargs:
        types.SimpleNamespace(docstatus=0) if doctype == "Payment Entry" and name == "PE-1" else "Supplier Ltd")
    api.frappe.get_doc = lambda *args: payment
    erp_party = types.ModuleType("erpnext.accounts.party")
    erp_party.get_party_account = lambda *args: "Payables - Co"
    monkeypatch.setitem(sys.modules, "erpnext", types.ModuleType("erpnext"))
    monkeypatch.setitem(sys.modules, "erpnext.accounts", types.ModuleType("erpnext.accounts"))
    monkeypatch.setitem(sys.modules, "erpnext.accounts.party", erp_party)
    review = Doc(erp_document="PE-1", erp_doctype="Payment Entry", link_method="AUTO_DRAFT",
                 source_json=json.dumps({"statement_key": "K1"}))
    api._retarget_draft(review, api.SUPPLIER_PAYMENT, {"party_type": "Supplier", "party": "SUP-1"}, Doc())
    assert permissions == ["write"]
    assert payment.saved and payment.party == "SUP-1"


def test_retarget_replaces_only_a_marked_unallocated_router_draft(api):
    calls = []
    old = Doc(custom_snb_idempotency_key="K1", references=[], doctype="Payment Entry")
    permissions = []
    old.check_permission = lambda permission: permissions.append(permission)
    api.frappe.db = types.SimpleNamespace(get_value=lambda doctype, name, *args, **kwargs:
        types.SimpleNamespace(docstatus=0) if args and args[0] == ["docstatus"] else None)
    api.frappe.get_doc = lambda *args: old
    api.frappe.has_permission = lambda doctype, permission: doctype == "Journal Entry" and permission == "create"
    api.frappe.delete_doc = lambda *args, **kwargs: calls.append((args, kwargs))
    review = Doc(erp_document="PE-1", erp_doctype="Payment Entry", link_method="AUTO_DRAFT",
                 source_json=json.dumps({"statement_key": "K1"}))
    replaced = api._retarget_draft(review, "EXPENSE_PAYMENT", {"account": "Expense - Co"}, Doc(), "JOURNAL_ENTRY")
    assert calls == [(("Payment Entry", "PE-1"), {})]
    assert permissions == ["write", "delete"]
    assert replaced == {"doctype": "Payment Entry", "name": "PE-1"}
    assert review.erp_document == "" and review.erp_doctype == ""


def test_retarget_keeps_allocated_payment_entry_when_type_would_change(api):
    old = Doc(custom_snb_idempotency_key="K1", references=[{"reference_name": "PINV-1"}], doctype="Payment Entry")
    api.frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: types.SimpleNamespace(docstatus=0))
    api.frappe.get_doc = lambda *args: old
    review = Doc(erp_document="PE-1", erp_doctype="Payment Entry", link_method="AUTO_DRAFT",
                 source_json=json.dumps({"statement_key": "K1"}))
    with pytest.raises(ValueError, match="allocations"):
        api._retarget_draft(review, "EXPENSE_PAYMENT", {"account": "Expense - Co"}, Doc(), "JOURNAL_ENTRY")
    assert review.erp_document == "PE-1"


def test_related_document_status_uses_permission_filtered_list(api):
    api.frappe.get_all = lambda *a, **k: (_ for _ in ()).throw(AssertionError("get_all bypassed read filters"))
    api.frappe.get_list = lambda *a, **k: [types.SimpleNamespace(name="PE-1", docstatus=0)]
    result = api._doc_status([{"erp_doctype": "Payment Entry", "erp_document": "PE-1"}])
    assert result == {("Payment Entry", "PE-1"): 0}


def test_party_duplicate_check_requires_read_permission(api):
    api.frappe.get_list = lambda *a, **k: []
    api.frappe.has_permission = lambda doctype, permission: not (doctype == "Supplier" and permission == "read")
    with pytest.raises(PermissionError, match="need read access"):
        api._new_party("Supplier", "New Supplier Ltd")


def test_manual_route_reprocesses_only_the_reviewed_movement(api, monkeypatch):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None, exists=lambda *a: False,
                                          get_value=lambda *a, **k: False)
    movement = Doc(name="ROW-1", modified="now", kind=api.SUPPLIER_PAYMENT, signals_json="{}",
                   direction="DEBIT", counterparty="", erp_document="", erp_doctype="", link_method="", accounting_treatment="")
    movement.append = lambda *a, **k: None
    counterparty = Doc(name="CP-1", supplier="", customer="", expense_account="")
    counterparty.save = lambda **kwargs: None
    def get_doc(doctype, name=None):
        if doctype == api.DOCTYPE:
            return movement
        return Doc(name=name, check_permission=lambda permission: None)
    api.frappe.get_doc = get_doc
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *a: counterparty)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *a: None)
    monkeypatch.setattr(api, "_retarget_draft", lambda *a: None)
    reruns = []
    api.runtime.run = lambda *args, **kwargs: reruns.append((args, kwargs))
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name})
    result = api.route_movement("ROW-1", "now", {"type": "PARTY", "treatment": "PAYMENT_ENTRY", "party_type": "Supplier", "party": "SUP-1"})
    assert result == {"movement": {"name": "ROW-1"}, "rerouted": 0}
    assert reruns == [(('main', 0, 1), {"names": ["ROW-1"], "manual_draft": False})]


def test_clear_missing_document_preserves_rejection_and_does_not_run_engine(api, monkeypatch):
    movement = Doc(name="row", erp_doctype="Journal Entry", erp_document="ACC-JV-OLD", link_method="AM_LINK",
                   candidates_json='{"rejected":[]}', erp_hint_json='{"linked_doc":"ACC-JV-OLD"}',
                   engine_state="DRAFT_READY", decision_type="")
    audit = []
    movement.append = lambda field, row: audit.append((field, row))
    api.frappe.db = types.SimpleNamespace(exists=lambda *args: False)
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name})
    api.runtime.run = lambda *args, **kwargs: pytest.fail("must not run routing or create a draft")
    assert api.clear_missing_document("row", "modified") == {"name": "row"}
    assert movement.erp_document == "" and movement.engine_state == "PENDING"
    assert json.loads(movement.candidates_json)["rejected"] == ["ACC-JV-OLD"]
    assert json.loads(movement.erp_hint_json)["linked_doc"] == ""
    assert movement.saved and audit


def test_clear_missing_document_refuses_an_existing_document(api, monkeypatch):
    movement = Doc(erp_doctype="Payment Entry", erp_document="ACC-PAY-1")
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    api.frappe.db = types.SimpleNamespace(exists=lambda *args: True)
    with pytest.raises(ValueError, match="still exists"):
        api.clear_missing_document("row", "modified")
    assert movement.erp_document == "ACC-PAY-1"


def test_bulk_clear_missing_requires_unique_fresh_rows(api, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "clear_missing_document", lambda name, modified: calls.append((name, modified)))
    assert api.bulk_clear_missing_documents([{"name": "A", "modified": "t1"}, {"name": "B", "modified": "t2"}]) == {"cleared": 2}
    assert calls == [("A", "t1"), ("B", "t2")]
    with pytest.raises(ValueError):
        api.bulk_clear_missing_documents([{"name": "A", "modified": "t1"}, {"name": "A", "modified": "t2"}])
    with pytest.raises(ValueError):
        api.bulk_clear_missing_documents([{"name": "A"}])


def test_receipt_route_records_valid_invoice_and_clamps_allocation(api, monkeypatch):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None, exists=lambda *a: False,
                                          get_value=lambda *a, **k: False)
    movement = Doc(name="R1", modified="t", kind=api.CUSTOMER_RECEIPT, signals_json="{}", direction="CREDIT",
                   counterparty="", erp_document="", erp_doctype="", link_method="", accounting_treatment="", amount=500)
    movement.append = lambda *a, **k: None
    cp = Doc(name="CP", customer="", supplier="", display_name="Customer name")
    cp.save = lambda **kwargs: None
    invoice = Doc(docstatus=1, company=api.runtime.documents.COMPANY, currency="SAR", customer="CUST", outstanding_amount=300)
    api.frappe.get_doc = lambda doctype, name=None: movement if doctype == api.DOCTYPE else invoice
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *a: cp)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *a: None)
    monkeypatch.setattr(api, "_retarget_draft", lambda *a: None)
    monkeypatch.setattr(api, "_check_link", lambda *a: None)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name})
    api.route_movement("R1", "t", {"type": "PARTY", "treatment": "PAYMENT_ENTRY", "party_type": "Customer", "party": "CUST", "sales_invoice": "INV-1"})
    assert movement.payment_reference == "INV-1" and movement.payment_reference_amount == 300
    invoice.customer = "OTHER"
    with pytest.raises(ValueError, match="reference"):
        api.route_movement("R1", "t", {"type": "PARTY", "treatment": "PAYMENT_ENTRY", "party_type": "Customer", "party": "CUST", "sales_invoice": "INV-1"})


def test_payload_hides_parties_the_user_cannot_read(api):
    row = Doc(name="R", modified="t", event_date="2026-11-10", amount=10, currency="SAR", source_account_tail="1234",
              direction="CREDIT", engine_state="NEEDS_YOU", decision_type="ROUTE_PARTY", kind="CUSTOMER_RECEIPT",
              accounting_treatment="", accounting_account="", counterparty="CP", route_source="", erp_doctype="", erp_document="",
              link_method="", source_json="{}", recognition_json="{}", signals_json="{}", candidates_json='{"counterparties":["CP2"]}',
              notes="", parent_movement="")
    def get_value(doctype, name, fields, **kwargs):
        return {"display_name":"Known", "customer":"SECRET", "supplier":""} if isinstance(fields, list) else "SECRET"
    api.frappe.db = types.SimpleNamespace(get_value=get_value)
    api.frappe.has_permission = lambda doctype, permission, *args: False
    payload = api._payload(row)
    assert payload["linked_party"] == "" and payload["suggested_parties"] == []


def test_confirming_old_snb_row_learns_newly_parsed_receipt_hint(api):
    created = []
    api.runtime.Settings = lambda: types.SimpleNamespace(company_scopes=frozenset())
    api.frappe.db = types.SimpleNamespace(exists=lambda *args: False)
    def make_doc(value):
        doc = Doc(**value)
        doc.insert = lambda **kwargs: created.append(value)
        return doc
    api.frappe.get_doc = make_doc
    api.frappe.utils.nowdate = lambda: "2026-11-10"
    source = {"bank": "SNB", "direction": "CREDIT", "parser_family": "INCOMING_LOCAL",
              "transaction_description": "Incoming Local transfer", "detail_description": "BNPASARI ENOVA FOR FACILITIES AND ENERG EXTN980263063RK6"}
    movement = Doc(signals_json='{"identifiers":[]}', source_json=json.dumps(source))
    api._learn_identifiers(movement, Doc(name="CP-1"))
    assert len(created) == 1 and created[0]["kind"] == "NAME_LARGE_LOCAL"
    assert created[0]["value"] == "ENOVA FOR FACILITIES AND ENERG"


def test_request_supplier_requires_unique_match_and_readable_supplier(api):
    doc = Doc(direction="DEBIT")
    recognition = {"am_category_status": "MATCHED", "transfer_request": {"erp_party": "Supplier: ALMASAR YELLOW .CO"}}
    seen = []
    api.frappe.get_list = lambda doctype, **kw: seen.append((doctype, kw)) or [{"name": "SUP-ALMASAR"}]
    assert api._request_supplier(doc, recognition) == "SUP-ALMASAR"
    assert seen[0][1]["filters"] == {"disabled": 0}
    assert seen[0][1]["or_filters"]["supplier_name"] == ["=", "ALMASAR YELLOW .CO"]
    recognition["am_category_status"] = "NO_CATEGORY"
    assert api._request_supplier(doc, recognition) == "SUP-ALMASAR"
    recognition["am_category_status"] = "AMBIGUOUS"
    assert api._request_supplier(doc, recognition) == ""
    recognition["am_category_status"] = "MATCHED"
    api.frappe.get_list = lambda *a, **k: [{"name": "SUP-1"}, {"name": "SUP-2"}]
    assert api._request_supplier(doc, recognition) == ""
    api.frappe.has_permission = lambda *args: False
    assert api._request_supplier(doc, recognition) == ""
    doc.direction = "CREDIT"
    assert api._request_supplier(doc, recognition) == ""


def test_petty_cash_confirmation_rejects_conflicting_custody_and_never_drafts(api, monkeypatch):
    import sys
    movement = Doc(name="R", direction="DEBIT", kind="PETTY_CASH", erp_document="", recognition_json='{"category":"XXPC","am_category_status":"MATCHED"}',
                   signals_json='{}', source_json='{}', counterparty="", route_source="", accounting_treatment="")
    movement.append = lambda *args: None
    cp = Doc(name="CP", employee="OTHER", custody_account="OTHER-ACCOUNT")
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._active_employee = lambda employee, company: "CUSTODY"
    funding._require_finance = lambda: None
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    api.runtime.run = lambda *args, **kwargs: pytest.fail("must not route a conflicting identity")
    with pytest.raises(ValueError, match="different Employee"):
        api.confirm_petty_cash_employee("R", "t", "EMP-1")
    assert movement.counterparty == "" and not getattr(movement, "saved", False)


def test_petty_cash_confirmation_records_explicit_review_without_drafting(api, monkeypatch):
    import sys
    movement = Doc(name="R", direction="DEBIT", kind="PETTY_CASH", erp_document="", recognition_json='{"category":"XXPC","am_category_status":"MATCHED"}',
                   signals_json='{}', source_json='{}', counterparty="", route_source="", accounting_treatment="")
    movement.append = lambda *args: None
    cp = Doc(name="CP", employee="", custody_account="")
    cp.save = lambda **kwargs: None
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *args: None)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name, "kind": "PETTY_CASH"})
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._active_employee = lambda employee, company: "CUSTODY"
    funding._require_finance = lambda: None
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    calls = []
    api.runtime.run = lambda *args, **kwargs: calls.append(kwargs) or {"errors": 0}
    assert api.confirm_petty_cash_employee("R", "t", "EMP-1")["name"] == "R"
    assert (cp.employee, cp.custody_account, movement.accounting_treatment) == ("EMP-1", "CUSTODY", "JOURNAL_ENTRY")
    assert calls == [{"names": ["R"], "review_only": True}]


def test_untagged_employee_can_be_designated_petty_cash(api, monkeypatch):
    movement = Doc(name="R", direction="DEBIT", kind="UNKNOWN", erp_document="", recognition_json='{}',
                   signals_json='{}', source_json='{}', counterparty="", route_source="", accounting_treatment="")
    movement.append = lambda *args: None
    cp = Doc(name="CP", employee="", custody_account="")
    cp.save = lambda **kwargs: None
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *args: None)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name": name, "kind": "PETTY_CASH"})
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._active_employee = lambda employee, company: "CUSTODY"
    funding._require_finance = lambda: None
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    api.runtime.run = lambda *args, **kwargs: {"errors": 0}
    api.confirm_petty_cash_employee("R", "t", "EMP-1")
    assert json.loads(movement.recognition_json) == {"finance_petty_cash": True}
    assert cp.employee == "EMP-1"


def test_own_transfer_refuses_when_either_leg_already_linked(api):
    first = Doc(name="A", modified="t", kind="OWN_TRANSFER", signals_json='{"paired_transfer":{"name":"B"}}', erp_document="")
    second = Doc(name="B", erp_document="JV-EXISTING")
    api.frappe.get_doc = lambda doctype, name: first if name == "A" else second
    api.frappe.db = types.SimpleNamespace(sql=lambda *args: None)
    with pytest.raises(ValueError, match="already has a linked"):
        api.create_own_transfer_draft("A", "t")


def test_own_transfer_refuses_ambiguous_pair_after_lock(api, monkeypatch):
    first = Doc(name="A", modified="t", kind="OWN_TRANSFER", signals_json='{"paired_transfer":{"name":"B"}}', erp_document="")
    second = Doc(name="B", erp_document="")
    api.frappe.get_doc = lambda doctype, name: first if name == "A" else second
    api.frappe.db = types.SimpleNamespace(sql=lambda *args: None)
    api.runtime.Settings = lambda: object()
    api.runtime.load_index = lambda: ({}, {})
    api.runtime.pair_own_transfers = lambda *args: {}
    with pytest.raises(ValueError, match="unique opposite"):
        api.create_own_transfer_draft("A", "t")


def test_hint_export_requires_integration_identity_and_preserves_scope(api):
    api.frappe.session.user = "someone@example.com"
    with pytest.raises(PermissionError):
        api.list_confirmed_party_hints()
    api.frappe.session.user = "9eskot9@gmail.com"
    ident = types.SimpleNamespace(name="a" * 64, counterparty="CP-1", kind="NAME_IPS_LOCAL", value="ACME", normalized="acme", status="ACTIVE", modified="2026-11-10")
    api.frappe.get_all = lambda *args, **kwargs: [ident]
    api.frappe.db = types.SimpleNamespace(get_value=lambda *args, **kwargs: types.SimpleNamespace(customer="C-1", supplier="", status="ACTIVE"))
    result = api.list_confirmed_party_hints()
    assert result["rows"][0]["customer"] == "C-1" and result["rows"][0]["kind"] == "NAME_IPS_LOCAL"
    assert result["has_more"] is False and result["next_start"] == 1


def test_manual_custody_is_explicit_and_does_not_assign_employee(api, monkeypatch):
    movement = Doc(name="R", direction="DEBIT", kind="PETTY_CASH", erp_document="", recognition_json='{"category":"XXPC","am_category_status":"MATCHED"}',
                   signals_json='{}', source_json='{}', counterparty="", route_source="", accounting_treatment="", accounting_account="")
    movement.append = lambda *args: None
    cp = Doc(name="CP", employee="", custody_account="")
    cp.save = lambda **kwargs: None
    monkeypatch.setattr(api, "_lock", lambda *args: movement)
    monkeypatch.setattr(api, "_ensure_counterparty", lambda *args: cp)
    monkeypatch.setattr(api, "_verified_custody_account", lambda account: account)
    monkeypatch.setattr(api, "_learn_identifiers", lambda *args: None)
    monkeypatch.setattr(api, "get_movement", lambda name: {"name":name})
    funding = types.ModuleType("sig_warehouse.sig_warehouse.pc_funding")
    funding._require_finance = lambda: None
    monkeypatch.setitem(sys.modules, funding.__name__, funding)
    calls = []
    api.runtime.run = lambda *args, **kwargs: calls.append(kwargs) or {"errors":0}
    api.confirm_petty_cash_custody("R", "t", "1322 - Rajhi")
    assert cp.employee == "" and cp.custody_account == "1322 - Rajhi"
    assert movement.accounting_account == "1322 - Rajhi" and movement.route_source == "MANUAL"
    assert calls == [{"names":["R"], "review_only":True}]
    with pytest.raises(ValueError, match="different custody"):
        api.confirm_petty_cash_custody("R", "t", "1322 - SAB")


def test_own_transfer_creates_one_draft_and_links_both_legs(api, monkeypatch):
    import datetime
    first = Doc(name="A", modified="t", kind="OWN_TRANSFER", signals_json='{"paired_transfer":{"name":"B"}}', erp_document="",
                direction="DEBIT", amount=-500, currency="SAR", account_scope_hash="S1", event_date=datetime.date(2026,11,10),
                source_json='{"statement_key":"KEY","reference":"REF"}', source_key="SNB-A")
    second = Doc(name="B", modified="u", kind="OWN_TRANSFER", signals_json='{"paired_transfer":{"name":"A"}}', erp_document="",
                 direction="CREDIT", amount=500, currency="SAR", account_scope_hash="S2", event_date=datetime.date(2026,11,10),
                 source_json='{}', source_key="SNB-B")
    for row in (first, second): row.append = lambda *args: None
    inserted = []
    journal = Doc(name="JV-1")
    journal.insert = lambda: inserted.append(True)
    api.frappe.get_doc = lambda doctype, name=None: (first if name == "A" else second) if doctype == api.DOCTYPE else journal
    bank = types.SimpleNamespace(company=api.runtime.documents.COMPANY, account_type="Bank", disabled=0, is_group=0, account_currency="SAR")
    api.frappe.db = types.SimpleNamespace(sql=lambda *args: None, get_value=lambda *args, **kwargs: bank, exists=lambda *args: False)
    api.runtime.Settings = lambda: types.SimpleNamespace(scopes={"S1":"BANK-1", "S2":"BANK-2"}, fee_account="FEE", vat_account="VAT")
    api.runtime.load_index = lambda: ({}, {})
    api.runtime.pair_own_transfers = lambda *args: {"A":{"name":"B"}, "B":{"name":"A"}}
    api.runtime.getdate = lambda x: x
    api.runtime.dt = datetime
    api.runtime.Ledger = lambda *args: types.SimpleNamespace(candidates=lambda *args: [])
    api.runtime.documents.own_transfer_journal = lambda *args: {"doctype":"Journal Entry"}
    monkeypatch.setattr(api, "_fees_for", lambda names: {})
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    result = api.create_own_transfer_draft("A", "t")
    assert inserted == [True] and result == {"journal":"JV-1", "movements":["A","B"]}
    assert first.erp_document == second.erp_document == "JV-1"
    assert first.link_method == second.link_method == "OWN_TRANSFER"


def test_nonemployee_custody_selection_requires_approved_1322_ancestor(api, monkeypatch):
    monkeypatch.setattr(api, "_check_link", lambda *args: None)
    row = types.SimpleNamespace(company=api.runtime.documents.COMPANY, root_type="Asset", account_currency="SAR", disabled=0, is_group=0, parent_account="PARENT")
    api.frappe.db = types.SimpleNamespace(get_value=lambda doctype, name, fields, **kwargs: row if name == "CUSTODY" else ("1322", "ROOT"))
    assert api._verified_custody_account("CUSTODY") == "CUSTODY"
    api.frappe.db.get_value = lambda doctype, name, fields, **kwargs: row if name == "CUSTODY" else ("1321", "")
    with pytest.raises(ValueError, match="1322"):
        api._verified_custody_account("CUSTODY")


def test_supply_type_follows_the_purpose_then_the_payee_usual_type(api):
    types_ = [{"code": "MATERIAL_SUPPLY"}, {"code": "MAINTENANCE"}, {"code": "CONTRACTING"}]
    assert api._suggest_supply(types_, "XXMT", {"category": "MATERIAL_SUPPLY"}) == "MAINTENANCE"
    assert api._suggest_supply(types_, "", {"category": "material_supply"}) == "MATERIAL_SUPPLY"
    assert api._suggest_supply(types_, "XXLG", {"category": "NOT_A_TYPE"}) == ""
    assert api._suggest_supply(types_, "XXSC", None) == "CONTRACTING"


def test_fee_rows_are_never_counted_as_lines_of_their_own(api):
    assert api._shown_in_tab("deferred", "BANK_CHARGE", "") is False
    assert api._shown_in_tab("posted", "BANK_CHARGE", "PARENT") is False
    assert api._shown_in_tab("posted", "BANK_CHARGE", "") is True
    assert api._shown_in_tab("needs", "UNKNOWN", "") is True
    assert set(api.KIND_GROUPS["OTHER"]) >= {"BANK_CHARGE", "SPECIALIST"}


def test_supplier_open_documents_mark_exact_amounts_and_keep_receipts_as_hints(api):
    calls = {}

    def getter(doctype, **kwargs):
        calls[doctype] = kwargs["filters"]
        return {
            "Purchase Invoice": [{"name": "PI-1", "bill_no": "B1", "posting_date": "2026-10-01", "grand_total": 500, "outstanding_amount": 366.09},
                                 {"name": "PI-2", "bill_no": "", "posting_date": "2026-09-01", "grand_total": 900, "outstanding_amount": 900}],
            "Purchase Order": [{"name": "PO-1", "transaction_date": "2026-10-02", "grand_total": 1000, "advance_paid": 100}],
            "Purchase Receipt": [{"name": "PR-1", "posting_date": "2026-10-21", "grand_total": 366.09}],
        }[doctype]
    out = api._open_supplier_documents("SUP", -366.09, getter)
    assert [(d["name"], d["exact"]) for d in out["invoices"]] == [("PI-1", True), ("PI-2", False)]
    assert out["orders"][0]["open"] == 900 and out["orders"][0]["exact"] is False
    assert out["receipts"][0]["exact"] is True and out["receipts"][0]["doctype"] == "Purchase Receipt"
    assert calls["Purchase Receipt"]["status"] == "To Bill" and calls["Purchase Invoice"]["outstanding_amount"] == [">", 0]


def test_supplier_open_documents_report_a_document_type_the_role_cannot_read(api):
    def getter(doctype, **kwargs):
        if doctype == "Purchase Receipt":
            raise PermissionError("no")
        return []
    out = api._open_supplier_documents("SUP", 100, getter)
    assert out["receipts"] == [] and out["restricted"] == ["Purchase Receipt"]


def test_a_sadad_bill_account_names_the_employee_only_when_erp_holds_it(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    monkeypatch.setattr(api.frappe, "get_list", lambda *a, **k: [{"name": "HR-EMP-9", "employee_name": "Imran"}], raising=False)
    assert api._bill_owner({"bill_account": "2286958091"}) == {"employee": "HR-EMP-9", "name": "Imran"}
    monkeypatch.setattr(api.frappe, "get_list", lambda *a, **k: [], raising=False)
    assert api._bill_owner({"bill_account": "2286958091"}) is None
    assert api._bill_owner({}) is None
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: False, raising=False)
    assert api._bill_owner({"bill_account": "2286958091"}) is None


def test_government_fee_billers_list_accounts_in_the_owners_order_without_choosing(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    seen = {}
    def get_list(doctype, **kwargs):
        seen.update(kwargs["filters"])
        return [{"name": "530 - Admin", "account_number": "530"}, {"name": "5155 - Projects", "account_number": "5155"}]
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    assert api._account_choices("090") == ["5155 - Projects", "530 - Admin"]
    assert seen["root_type"] == "Expense" and seen["is_group"] == 0
    assert api._account_choices("002") == [] and api._account_choices("") == []


def test_a_journal_entry_may_use_any_suitable_account_of_the_company(api):
    """Owner decision 11 Nov: do not limit Finance to expense accounts; custody, advances, other banks and liabilities are allowed."""
    base = {"root_type": "Expense", "account_type": "", "is_group": 0, "disabled": 0, "company": "Co"}
    for root, account in (("Expense", "5155 - X"), ("Asset", "132247 - Company use - SIG"), ("Asset", "1321 - Advances - SIG"),
                          ("Liability", "243 - Yanal"), ("Asset", "13122 - Alinma - SIG")):
        assert api._expense_account_allowed({**base, "root_type": root}, account, bank_gl="13121 - SNB 109 - SIG") is True
    assert api._expense_account_allowed(base, "13121 - SNB 109 - SIG", bank_gl="13121 - SNB 109 - SIG") is False   # its own bank
    assert api._expense_account_allowed({**base, "account_type": "Payable"}, "221", bank_gl="") is False            # needs a party
    assert api._expense_account_allowed({**base, "account_type": "Receivable"}, "1201", bank_gl="") is False
    assert api._expense_account_allowed({**base, "is_group": 1}, "5 - Group") is False
    assert api._expense_account_allowed({**base, "company": "Other"}, "5155 - X") is False
    assert api._is_sadad('{"parser_family":"SADAD"}') and not api._is_sadad('{"parser_family":"LOCAL"}')


def test_a_company_use_ledger_is_offered_when_no_employee_owns_it(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    def get_list(doctype, **kw):
        return [{"name": "132247 - Algain Al Rajhi - SIG"}] if doctype == "Account" else []
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    monkeypatch.setattr(api, "_verified_custody_account", lambda account: account, raising=False)
    found = api._company_use_ledger("Employee: Mohammed Salah Algain - Al Rajhi | 132247")
    assert found == {"employee": "", "name": "Mohammed Salah Algain - Al Rajhi", "account": "132247 - Algain Al Rajhi - SIG", "company_use": True}
    assert api._company_use_ledger("Supplier: X") is None


def test_the_payee_label_comes_from_the_matched_line_or_the_payee_record(api):
    cp = {"am_key": "K1", "am_party": "Employee: Obed | 132244"}
    matched = {"source": "Sheet Am matched beneficiary", "beneficiary_key": "K1", "erp_party": "Employee: Obed Sharrif | 132244"}
    assert api._payee_label(matched, cp) == "Employee: Obed Sharrif | 132244"
    assert api._payee_label({"source": "Sheet Am beneficiary/transfer evidence"}, cp) == "Employee: Obed | 132244"
    assert api._payee_label({**matched, "beneficiary_key": "K2"}, cp) == "Employee: Obed | 132244"
    assert api._payee_label({}, None) == ""


def test_sadad_group_filters_and_counts_statement_family(api, monkeypatch):
    monkeypatch.setattr(api, "_confirmation_candidates", lambda *args: [])
    rows = [types.SimpleNamespace(engine_state="NEEDS_YOU", kind="UNKNOWN", parent_movement="", source_json='{"parser_family":"SADAD"}'),
            types.SimpleNamespace(engine_state="NEEDS_YOU", kind="EXPENSE_PAYMENT", parent_movement="", source_json='{"parser_family":"SADAD"}'),
            types.SimpleNamespace(engine_state="NEEDS_YOU", kind="UNKNOWN", parent_movement="", source_json='{"parser_family":"LOCAL"}')]
    calls = []
    def get_list(doctype, **kwargs):
        calls.append(kwargs)
        return rows if kwargs.get("limit_page_length") == 0 else []
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    monkeypatch.setattr(api, "_fees_for", lambda names: {})
    monkeypatch.setattr(api, "_doc_status", lambda docs: {})
    result = api.list_inbox(kind_group="SADAD")
    assert calls[0]["filters"]["source_json"] == ["like", '%"parser_family":"SADAD"%']
    assert result["kind_counts"]["SADAD"] == 2
    assert result["kind_counts"]["ALL"] == 3


def test_mapped_custody_needs_one_enabled_account_and_one_active_employee(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    def get_list(doctype, **kwargs):
        return [{"name": "132214 - Imran - SIG"}] if doctype == "Account" else [{"name": "HR-EMP-9", "employee_name": "Mohammed Imran Ansary"}]
    monkeypatch.setattr(api.frappe, "get_list", get_list, raising=False)
    found = api._mapped_custody({"erp_party": "Employee: Mohammed Imran Ansary | 132214"})
    assert (found["employee"], found["account"]) == ("HR-EMP-9", "132214 - Imran - SIG")
    assert api._mapped_custody({"erp_party": "Supplier: X"}) is None and api._mapped_custody({}) is None


def test_verified_payee_custody_needs_the_exact_beneficiary_and_the_name(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    monkeypatch.setattr(api.frappe, "get_list", lambda doctype, **kw: [{"name": "132214 - Imran - SIG"}] if doctype == "Account"
                        else [{"name": "HR-EMP-9", "employee_name": "Mohammed Imran Ansary"}], raising=False)
    good = {"source": "Sheet Am matched beneficiary", "beneficiary_key": "K1", "erp_party": "Employee: Mohammed Imran Ansary | 132214"}
    assert api._verified_payee_custody(good, "K1")["employee"] == "HR-EMP-9"
    assert api._verified_payee_custody({**good, "source": "typed"}, "K1") is None
    assert api._verified_payee_custody(good, "K2") is None
    assert api._verified_payee_custody({**good, "erp_party": "Employee: Someone Else | 132214"}, "K1") is None
    arabic = {**good, "erp_party": "Employee: محمد عمران | 132214"}
    assert api._verified_payee_custody(arabic, "K1")["account"] == "132214 - Imran - SIG"


def test_verified_employee_proposals_skip_payees_that_are_already_tied_or_not_people(api, monkeypatch):
    monkeypatch.setattr(api.frappe, "has_permission", lambda *args: True, raising=False)
    monkeypatch.setattr(api.frappe, "get_list", lambda doctype, **kw: [{"name": "132214 - Imran - SIG"}] if doctype == "Account"
                        else [{"name": "HR-EMP-9", "employee_name": "Mohammed Imran Ansary"}], raising=False)
    mapping = {"source": "Sheet Am matched beneficiary", "beneficiary_key": "K1", "erp_party": "Employee: Mohammed Imran Ansary | 132214"}
    rows = [{"name": "m1", "counterparty": "CP1", "recognition_json": json.dumps({"am_beneficiary_mapping": mapping})},
            {"name": "m2", "counterparty": "CP1", "recognition_json": json.dumps({"am_beneficiary_mapping": mapping})},
            {"name": "m3", "counterparty": "CP2", "recognition_json": json.dumps({"am_beneficiary_mapping": mapping})},
            {"name": "m4", "counterparty": "CP3", "recognition_json": json.dumps({"am_beneficiary_mapping": mapping})}]
    cps = {"CP1": {"am_key": "K1", "display_name": "Imran"},
           "CP2": {"am_key": "K1", "employee": "HR-EMP-9", "custody_account": "x"},      # already tied
           "CP3": {"am_key": "K1", "supplier": "SUP-1"}}                                  # a supplier, not a person
    found = api._verified_employee_proposals(rows, cps.get)
    assert list(found) == ["CP1"] and found["CP1"]["movements"] == ["m1", "m2"] and found["CP1"]["employee"] == "HR-EMP-9"
