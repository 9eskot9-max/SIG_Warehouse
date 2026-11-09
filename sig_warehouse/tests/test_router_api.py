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


def test_only_the_integration_owner_may_run_the_engine_or_read_links(api):
    api.frappe.session.user = "someone@example.com"
    for call in (lambda: api.run_engine("main"), lambda: api.list_links(), lambda: api.sync_counterparties([])):
        with pytest.raises(PermissionError):
            call()


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
    api.frappe.get_all = lambda *a, **k: [row]
    with pytest.raises(ValueError, match="already exists: CUST-1"):
        api._new_party("Customer", "  khutut  co ")
    created = {}
    class Inserted(Doc):
        name = "CUST-2"
        def insert(self):
            created.update(self.__dict__)
    api.frappe.get_all = lambda *a, **k: []
    api.frappe.get_doc = lambda values: Inserted(**values)
    assert api._new_party("Supplier", "New Supplier Ltd", "300123") == "CUST-2"
    assert created["supplier_group"] == "Local" and created["supplier_type"] == "Company" and created["tax_id"] == "300123"
    with pytest.raises(ValueError):
        api._new_party("Supplier", "ab")


def test_routing_is_only_for_party_kinds_and_checks_the_party_type(api):
    api.frappe.db = types.SimpleNamespace(sql=lambda *a: None)
    doc = Doc(modified="t", kind="OWN_TRANSFER", signals_json="{}", counterparty="")
    api.frappe.get_doc = lambda *a: doc
    with pytest.raises(ValueError, match="not routed to a party"):
        api.route_movement("n", "t", {"type": "PARTY"})
    doc.kind = "CUSTOMER_RECEIPT"
    api.frappe.db.exists = lambda *a: False
    api._ensure_counterparty = lambda d, label: Doc(name="CP")
    with pytest.raises(ValueError, match="take a Customer"):
        api.route_movement("n", "t", {"type": "PARTY", "party_type": "Supplier", "party": "S"})
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
    api.frappe.get_all = lambda *a, **k: []
    api.frappe.has_permission = lambda doctype, permission: not (doctype == "Supplier" and permission == "create")
    with pytest.raises(PermissionError, match="cannot create a new Supplier"):
        api._new_party("Supplier", "Brand New Supplier Co")
    assert api.frappe.has_permission("Customer", "create") is True
