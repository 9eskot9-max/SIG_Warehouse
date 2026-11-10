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
    api._ensure_counterparty = lambda d, label: Doc(name="CP")
    with pytest.raises(ValueError, match="take a Customer"):
        api.route_movement("n", "t", {"type": "PARTY", "treatment": "PAYMENT_ENTRY", "party_type": "Supplier", "party": "S"})
    with pytest.raises(ValueError, match="changed since"):
        api.route_movement("n", "stale", {"type": "PARTY"})


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
