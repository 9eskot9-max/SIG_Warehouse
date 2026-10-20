"""Offline accounting boundaries; native Frappe/DB/UAT are separate release checks."""

import datetime as dt
import importlib
import json
from pathlib import Path
import sys
import types

import pytest

from sig_warehouse.sig_warehouse import pc_clearance_rules as rules


ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-10-19 13:00:00"


class Denied(Exception):
    pass


class Record(dict):
    __getattr__ = dict.get

    def set(self, key, value):
        self[key] = value

    def check_permission(self, ptype):
        self.trace.append(("permission", self.doctype, ptype))

    def insert(self, **kwargs):
        assert kwargs == {}, "Accounting insertion must use native permissions"
        assert getattr(self.fake.flags, "sig_pc_journal_create_receipt", None) == self.custom_pc_receipt
        if self.fake.deny_insert:
            raise Denied("Native Journal Entry create denied")
        self["name"], self["docstatus"] = "JE-PC-1", 0
        self.fake.journals[self.name] = self
        self.trace.append(("insert", self.doctype))
        return self

    def save(self, **kwargs):
        assert kwargs == {"ignore_permissions": True}
        self.trace.append(("save", self.doctype))
        self["modified"] = "2026-10-19 13:05:00"
        return self


@pytest.fixture
def app(monkeypatch):
    fake = types.ModuleType("frappe")
    fake.whitelist = lambda **kwargs: lambda fn: fn
    fake.PermissionError = Denied
    fake.session = types.SimpleNamespace(user="reviewer@example.com")
    fake.flags = types.SimpleNamespace()
    fake.deny_insert, fake.journals, fake.trace, fake.legacy = False, {}, [], []

    def throw(message, exc=None):
        raise (exc or RuntimeError)(message)

    fake.throw = throw
    utils = types.ModuleType("frappe.utils")
    utils.get_datetime = lambda value: dt.datetime.fromisoformat(str(value))
    utils.now_datetime = lambda: dt.datetime(2026, 10, 19, 13, 5)
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    module = importlib.import_module("sig_warehouse.sig_warehouse.pc_journal")
    monkeypatch.setattr(module, "frappe", fake)

    def record(**values):
        out = Record(values)
        out.fake, out.trace = fake, fake.trace
        return out

    employee = record(name="HR-EMP-00019", employee_name="Asif Nawaz Muhammad Nawaz",
                      status="Active", cell_number="+966598366060", user_id="asif@example.com")
    actor = record(name="HR-EMP-00007", employee_name="Waleed", status="Active")
    scopes = json.loads((ROOT / "sig_warehouse/pc_review_scopes.json").read_text())
    context = {"user": fake.session.user, "roles": {"SIG PC Clearance"}, "actor": actor,
               "employees": [employee, actor], "phones": {"966598366060": {employee.name: employee}},
               "scopes": scopes}
    receipt = record(doctype="SIG PC Transaction", name="RECEIPT-1", source_id="SOURCE-1",
                     employee_name="966598366060", transaction_date="2026-10-19", amount=250,
                     transaction_category="Hotel Rent", has_vat=1, merchant="Hotel",
                     supplier_vat_number="123456789012345", invoice_number="INV-1", details="Room",
                     closure_status="Needs Review", modified=STAMP,
                     source_media_url="https://cdnydm.com/original.jpeg")
    fake.receipt, fake.context = receipt, context

    def get_doc(spec, name=None):
        if isinstance(spec, dict):
            assert spec["doctype"] == "Journal Entry", "No supplier, invoice or payment creation"
            return record(**spec)
        if spec == "SIG PC Transaction":
            return receipt
        if spec == "Journal Entry":
            return fake.journals[name]
        raise AssertionError("Unexpected document lookup: " + spec)

    def sql(query, args):
        fake.trace.append(("sql", query, args))
        if "from `tabSIG PC Transaction` where" in query:
            return [(receipt.name,)]
        if "je.user_remark" in query:
            return fake.legacy
        return []

    fake.get_doc = get_doc
    fake.db = types.SimpleNamespace(sql=sql, exists=lambda *args: False,
                                    escape=lambda value: "'" + value.replace("'", "''") + "'")
    monkeypatch.setattr(module, "_context", lambda user=None: context)
    monkeypatch.setattr(module, "_accounts", lambda *args: ("SIG", "EXPENSE", "CUSTODY", "Main"))
    return module, fake, receipt, context


def confirm(app, **kwargs):
    module, fake, receipt, _ = app
    return module.confirm_receipt(receipt.name, expected_modified=STAMP, **kwargs)


def test_confirm_creates_one_unsubmitted_native_journal_and_links_original(app):
    result = confirm(app)
    _, fake, receipt, _ = app
    journal = fake.journals[result["journal_entry"]]
    assert journal.docstatus == 0
    assert journal.custom_pc_receipt == receipt.name
    assert journal.custom_pc_source_key == rules.source_key(receipt.source_id)
    assert len(journal.accounts) == 2
    assert journal.accounts[0]["debit_in_account_currency"] == 250
    assert journal.accounts[1]["credit_in_account_currency"] == 250
    assert "Gross expense" in journal.user_remark
    assert receipt.source_media_url.endswith("original.jpeg")
    assert receipt.journal_status == "Draft" and receipt.closure_status == "Closed"
    assert not receipt.purchase_invoice and not receipt.payment_entry and not receipt.supplier
    assert receipt.reviewed_by == "reviewer@example.com"
    assert [(t[0], t[1]) for t in fake.trace if t[0] in ("insert", "save")] == [
        ("insert", "Journal Entry"), ("save", "SIG PC Transaction")]


def test_native_journal_permission_denial_does_not_confirm_receipt(app):
    _, fake, receipt, _ = app
    fake.deny_insert = True
    with pytest.raises(Denied, match="Native Journal Entry"):
        confirm(app)
    assert receipt.closure_status == "Needs Review" and not receipt.journal_entry
    assert not fake.journals
    assert not any(t[0] == "save" for t in fake.trace)
    assert not hasattr(fake.flags, "sig_pc_journal_create_receipt")


def test_exact_retry_returns_same_journal(app):
    first = confirm(app)
    again = confirm(app)
    assert again["existing"] and again["journal_entry"] == first["journal_entry"]
    assert len(app[1].journals) == 1


def test_retry_with_changed_amount_does_not_create_another_journal(app):
    confirm(app)
    with pytest.raises(RuntimeError, match="already has a journal"):
        confirm(app, amount="251.00")
    assert len(app[1].journals) == 1


@pytest.mark.parametrize("field", ["purchase_invoice", "payment_entry", "journal_entry"])
def test_existing_accounting_link_is_never_replaced(app, field):
    module, fake, receipt, _ = app
    receipt[field] = "EXISTING"
    if field == "journal_entry":
        fake.journals["EXISTING"] = Record(docstatus=0)
    with pytest.raises(RuntimeError, match="already has"):
        confirm(app)
    assert receipt[field] == "EXISTING"
    assert "JE-PC-1" not in fake.journals


def test_stale_receipt_is_rejected_before_accounting(app):
    app[2].modified = "2026-10-19 13:01:00"
    with pytest.raises(RuntimeError, match="changed after"):
        confirm(app)
    assert not app[1].journals


def test_pending_review_queue_excludes_pre_october_transactions(app, monkeypatch):
    module, fake, _, _ = app
    seen = []
    monkeypatch.setattr(fake, "get_list", lambda doctype, **kwargs: (seen.append((doctype, kwargs)) or []), raising=False)
    assert module.pending_receipts() == []
    assert seen[0][1]["filters"] == {
        "closure_status": ["in", ["Draft", "Needs Review"]],
        "transaction_date": [">=", "2026-10-01"],
    }


def test_status_report_reads_only_docstatus_of_the_matching_linked_journal(app, monkeypatch):
    module, fake, _, _ = app
    tx = Record(name="RECEIPT-1", employee_name="966598366060", transaction_date="2026-10-19",
                amount=250, transaction_category="Hotel Rent", closure_status="Closed",
                reviewed_by="manager@example.com", reviewed_at="2026-10-19 13:05:00",
                journal_entry="JE-1")
    seen = []
    monkeypatch.setattr(fake, "get_list", lambda doctype, **kwargs: (seen.append((doctype, kwargs)) or [tx]), raising=False)
    monkeypatch.setattr(module, "load_matrix", lambda: {
        "employees": [{"employee": "HR-EMP-00019", "pc_review_group": "colocation"}],
        "review_groups": {"colocation": {"label": "Colocation", "lead": "PM lead"}},
    })
    fake.db.get_value = lambda doctype, filters, fields, **kwargs: (
        Record(docstatus=1) if doctype == "Journal Entry" and filters == {
            "name": "JE-1", "custom_pc_receipt": "RECEIPT-1"} else "Manager Name"
    )
    result = module.transaction_status_report(employee="HR-EMP-00019", from_date="2026-10-01", to_date="2026-10-31")
    assert result[0]["journal_status"] == "Submitted"
    assert result[0]["finance_status"] == "Posted"
    assert result[0]["reviewed_by"] == "Manager Name"
    assert result[0]["employee_name"] == "Asif Nawaz Muhammad Nawaz"
    assert result[0]["review_group"] == "Colocation"
    assert result[0]["review_group_lead"] == "PM lead"
    assert seen[0][0] == "SIG PC Transaction"
    assert seen[0][1]["filters"] == {
        "transaction_date": ["between", ["2026-10-01", "2026-10-31"]]}


def test_status_report_clamps_requested_range_to_october(app, monkeypatch):
    module, fake, _, _ = app
    seen = []
    monkeypatch.setattr(fake, "get_list", lambda doctype, **kwargs: (seen.append(kwargs) or []), raising=False)
    result = module.transaction_status_report(from_date="2026-09-01", to_date="2026-10-31")
    assert result == []
    assert seen[0]["filters"] == {
        "transaction_date": ["between", ["2026-10-01", "2026-10-31"]]}


def test_status_report_returns_empty_for_range_before_october(app, monkeypatch):
    module, fake, _, _ = app
    seen = []
    monkeypatch.setattr(fake, "get_list", lambda doctype, **kwargs: (seen.append(kwargs) or []), raising=False)
    assert module.transaction_status_report(from_date="2026-09-01", to_date="2026-09-30") == []
    assert seen == []


def test_status_report_does_not_trust_a_mismatched_journal_link(app, monkeypatch):
    module, fake, _, _ = app
    tx = Record(name="RECEIPT-1", employee_name="Asif", transaction_date="2026-10-19",
                amount=250, transaction_category="Hotel Rent", closure_status="Closed",
                reviewed_by=None, reviewed_at=None, journal_entry="JE-OTHER")
    monkeypatch.setattr(fake, "get_list", lambda doctype, **kwargs: [tx], raising=False)
    fake.db.get_value = lambda doctype, filters, fields, **kwargs: None
    result = module.transaction_status_report()
    assert result[0]["journal_status"] == "Link mismatch"
    assert result[0]["journal_entry"] is None
    assert result[0]["finance_status"] == "Journal link mismatch"


def test_confirm_requires_original_evidence(app):
    app[2].source_media_url = ""
    with pytest.raises(RuntimeError, match="original receipt"):
        confirm(app)
    assert not app[1].journals


@pytest.mark.parametrize("case", ["unmatched", "ambiguous", "inactive", "unassigned", "self", "no_role"])
def test_sender_and_reviewer_boundaries(app, case):
    _, fake, receipt, context = app
    employee = context["employees"][0]
    if case == "unmatched":
        receipt.employee_name = "966500000000"
    elif case == "ambiguous":
        context["phones"]["966598366060"]["OTHER"] = Record(name="OTHER", status="Active")
    elif case == "inactive":
        employee.status = "Left"
    elif case == "unassigned":
        context["actor"].name = "HR-EMP-00013"
    elif case == "self":
        context["actor"] = employee
    elif case == "no_role":
        context["roles"] = {"Employee"}
    with pytest.raises((RuntimeError, Denied)):
        confirm(app)
    assert not fake.journals


def test_legacy_cycle_overlap_is_held_but_different_period_is_allowed(app):
    app[1].legacy = [("OLD", "[SIGPC clearance] Asif | SIG-PC-ASIF-2026-10-01-2026-10-31-hash")]
    with pytest.raises(RuntimeError, match="covers this receipt date"):
        confirm(app)
    app[1].legacy = [("OLD", "[SIGPC clearance] Asif | SIG-PC-ASIF-2026-09-01-2026-09-30-hash")]
    assert confirm(app)["ok"]


def test_rejection_cannot_bypass_existing_draft(app):
    module, fake, receipt, _ = app
    receipt.purchase_invoice = "OLD-PI"
    with pytest.raises(RuntimeError, match="without accounting"):
        module.reject_receipt(receipt.name, expected_modified=STAMP, notes="Duplicate")
    assert receipt.closure_status == "Needs Review" and not fake.journals


def test_stored_employee_scopes_match_approved_roster():
    folder = ROOT / "sig_warehouse"
    source = json.loads((folder / "pc_review_assignments.json").read_text(encoding="utf-8-sig"))
    stored = json.loads((folder / "pc_review_scopes.json").read_text())
    assert stored == rules.compile_scopes(source)
    assert len(stored["employees"]) == 58
    assert "HR-EMP-00007" in stored["employees"]["HR-EMP-00019"]
    assert all(employee not in reviewers for employee, reviewers in stored["employees"].items())


@pytest.mark.parametrize("value", [None, True, "NaN", "Infinity", "-1", "0", "0.001", "1000000000", "bad"])
def test_invalid_amounts_never_form_journal_lines(value):
    with pytest.raises(ValueError):
        rules.journal_lines(value, "EXPENSE", "CUSTODY", "Main")


def test_cycle_dates_fail_closed_on_unknown_format():
    with pytest.raises(ValueError):
        rules.legacy_cycle_period("[SIGPC clearance] unknown interval")


def test_native_query_scopes_before_pagination_and_direct_read_agrees(app):
    module, fake, receipt, context = app
    fake.get_all = lambda *args, **kwargs: [Record(employee_name=receipt.employee_name),
                                           Record(employee_name="966500000000")]
    condition = module.transaction_query_conditions()
    assert "966598366060" in condition and "966500000000" not in condition
    assert module.transaction_permission(receipt) is None  # native read still required
    assert module.transaction_permission(Record(employee_name="966500000000")) is False
    context["actor"].name = "HR-EMP-00013"
    assert module.transaction_query_conditions() == "1=0"
    assert module.transaction_permission(receipt) is False


def test_native_finance_access_is_preserved(app):
    module, _, receipt, context = app
    context["roles"] = {"Accounts User"}
    assert module.transaction_query_conditions() == ""
    assert module.transaction_permission(receipt) is None


def test_pc_clearance_journal_access_is_receipt_scoped_and_create_is_endpoint_only(app):
    module, fake, receipt, context = app
    fake.get_all = lambda *args, **kwargs: [Record(employee_name=receipt.employee_name),
                                            Record(employee_name="966500000000")]
    condition = module.journal_entry_query_conditions()
    assert "custom_pc_receipt" in condition and "966598366060" in condition
    assert "966500000000" not in condition
    fake.db.get_value = lambda doctype, name, field: (
        receipt.employee_name if doctype == "SIG PC Transaction" and name == receipt.name else None)
    linked = Record(custom_pc_receipt=receipt.name)
    assert module.journal_entry_permission(linked, permission_type="read") is None
    assert module.journal_entry_permission(Record(custom_pc_receipt="OTHER"), permission_type="read") is False
    assert module.journal_entry_permission(Record(custom_pc_receipt=receipt.name), permission_type="create") is False
    fake.flags.sig_pc_journal_create_receipt = receipt.name
    assert module.journal_entry_permission(linked, permission_type="create") is None
    assert module.journal_entry_permission(Record(custom_pc_receipt=receipt.name), permission_type="write") is None
    context["actor"].name = "HR-EMP-00013"
    assert module.journal_entry_permission(linked, permission_type="read") is False


def test_pc_clearance_create_without_document_is_denied(app):
    module, _, _, _ = app
    assert module.journal_entry_permission(None, permission_type="create") is False


def test_legacy_cycle_writer_detects_receipt_path_overlap(app):
    module, fake, _, _ = app
    original_sql = fake.db.sql

    def sql(query, args):
        if "inner join `tabSIG PC Transaction`" in query:
            assert args == ("CUSTODY", "2026-10-01", "2026-10-31")
            return [("JE-PC-1",)]
        return original_sql(query, args)

    fake.db.sql = sql
    cycle = Record(user_remark="[SIGPC clearance] Asif | SIG-PC-ASIF-2026-10-01-2026-10-31-hash",
                   accounts=[Record(account="CUSTODY", credit_in_account_currency=250)])
    with pytest.raises(RuntimeError, match="old cycle export"):
        module.guard_legacy_cycle(cycle)


@pytest.fixture
def migration(monkeypatch, app):
    fake = app[1]
    custom = types.ModuleType("frappe.custom.doctype.custom_field.custom_field")
    records, writes = {}, []

    def add_fields(definitions, update):
        assert update is True and set(definitions) == {"Journal Entry"}
        writes.append("fields")
        for field in definitions["Journal Entry"]:
            records[("Custom Field", "Journal Entry-" + field["fieldname"])] = Record(field)

    custom.create_custom_fields = add_fields
    monkeypatch.setitem(sys.modules, "frappe.custom.doctype.custom_field.custom_field", custom)
    module = importlib.import_module("sig_warehouse.sig_warehouse.patches.v1_0.stage_pc_journal_clearance")
    monkeypatch.setattr(module, "frappe", fake)

    class Script(Record):
        def save(self, **kwargs):
            assert kwargs == {"ignore_permissions": True}
            writes.append(self.name)

    for name in module.OLD_ENDPOINTS:
        records[("Server Script", name)] = Script(name=name, script_type="API", api_method=name, disabled=0)
    records[("Client Script", "SIG PC Transaction Review")] = Script(
        name="SIG PC Transaction Review", dt="SIG PC Transaction", enabled=1)
    fake.db.exists = lambda doctype, name: (doctype == "DocType" and name == "SIG PC Transaction") or (doctype, name) in records
    fake.get_doc = lambda doctype, name: records[(doctype, name)]
    fake.clear_cache = lambda **kwargs: None
    fake.cache = lambda: types.SimpleNamespace(delete_value=lambda key: None)
    return module, records, writes


def test_migration_is_repeatable_and_never_changes_permission_rows(migration):
    module, records, writes = migration
    module.execute()
    assert len(records) == 7
    assert set(key[0] for key in records) == {"Server Script", "Client Script", "Custom Field"}
    assert records[("Custom Field", "Journal Entry-custom_pc_receipt")]["unique"] == 1
    assert records[("Custom Field", "Journal Entry-custom_pc_source_key")]["unique"] == 1
    assert len(writes) == 5
    module.execute()
    assert writes.count("fields") == 2
    assert len(writes) == 6  # no repeated Server/Client Script writes


def test_migration_discovers_conflicting_endpoint_before_any_schema_write(migration):
    module, records, writes = migration
    records[("Server Script", "sig_pc_close_transaction")].api_method = "unexpected"
    with pytest.raises(RuntimeError, match="Unexpected legacy"):
        module.execute()
    assert writes == []


def test_migration_refuses_conflicting_unique_origin_contract(migration):
    module, records, writes = migration
    records[("Custom Field", "Journal Entry-custom_pc_receipt")] = Record(
        fieldtype="Data", unique=0, read_only=0)
    with pytest.raises(RuntimeError, match="contract differs"):
        module.execute()
    assert writes == []


def test_pc_je_permission_patch_updates_only_clearance_row_and_is_repeatable(monkeypatch, app):
    module = importlib.import_module(
        "sig_warehouse.sig_warehouse.patches.v1_0.scope_pc_clearance_journal_entry_permissions")
    rows = [Record(name="perm-" + role, role=role,
                   **dict(zip(module.PERM_FIELDS, values)))
            for role, values in module.CUSTOM_BASELINE.items()]
    by_name = {row.name: row for row in rows}
    writes, clears = [], []

    fake = app[1]
    def get_permissions(*args, **kwargs):
        assert kwargs["filters"] == {"parent": "Journal Entry"}
        assert "parenttype" not in kwargs["filters"]
        return rows
    fake.get_all = get_permissions
    fake.get_doc = lambda doctype, name: by_name[name]
    fake.clear_cache = lambda **kwargs: clears.append(kwargs)
    for row in rows:
        row.save = lambda **kwargs: (writes.append(row.role)
                                     if kwargs == {"ignore_permissions": True}
                                     else (_ for _ in ()).throw(AssertionError(kwargs)))
    monkeypatch.setattr(module, "frappe", fake)
    module.execute()
    assert writes == ["SIG PC Clearance"]
    assert by_name["perm-SIG PC Clearance"].write == 0
    assert by_name["perm-SIG PC Clearance"].export == 0
    assert by_name["perm-Accounts User"].write == 1
    module.execute()
    assert writes == ["SIG PC Clearance"]


def test_pc_je_permission_patch_fails_closed_on_matrix_drift(monkeypatch, app):
    module = importlib.import_module(
        "sig_warehouse.sig_warehouse.patches.v1_0.scope_pc_clearance_journal_entry_permissions")
    rows = [Record(name="perm-" + role, role=role,
                   **dict(zip(module.PERM_FIELDS, values)))
            for role, values in module.CUSTOM_BASELINE.items()]
    rows[0]["submit"] = 0
    writes = []
    fake = app[1]
    fake.get_all = lambda *args, **kwargs: rows
    fake.get_doc = lambda *args: writes.append("get_doc")
    monkeypatch.setattr(module, "frappe", fake)
    with pytest.raises(RuntimeError, match="matrix changed"):
        module.execute()
    assert writes == []
