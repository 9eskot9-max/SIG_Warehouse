"""Deterministic SNB payer hints are format- and account-tail scoped."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest


@pytest.fixture
def api(monkeypatch):
    fake = types.ModuleType("frappe")
    fake._ = lambda value: value
    fake.parse_json = json.loads
    fake.whitelist = lambda **kwargs: lambda fn: fn
    fake.session = types.SimpleNamespace(user="finance@example.com")
    fake.PermissionError = PermissionError
    fake.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or ValueError)(message))
    fake.has_permission = lambda doctype, permission: True
    utils = types.ModuleType("frappe.utils")
    utils.flt = float
    utils.now_datetime = lambda: "2026-11-09 10:00:00"
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    path = Path(__file__).parents[1] / "sig_accounting/snb_movement_router.py"
    spec = importlib.util.spec_from_file_location("router_party_hint_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_three_narrative_families_are_not_amount_derived(api):
    ips = {"parser_family": "IPS_LOCAL", "signed_amount": 1000,
           "detail_description": "SAUDI ARABIA ACME CO"}
    internal = {"parser_family": "INTERNAL_BEN_ID", "signed_amount": 90000,
                "detail_description": "12345678901234 BEN ID: 7654321"}
    large = {"parser_family": "LOCAL_OTBANK", "signed_amount": 100,
             "detail_description": "OTBANK:SABB ACME COMPANY"}
    assert [api._family(x) for x in (ips, internal, large)] == ["IPS_LOCAL", "INTERNAL_SNB", "LARGE_LOCAL"]
    assert api._hint_candidates(internal) == [("BEN_ID", "7654321"), ("ACCOUNT", "12345678901234")]
    assert api._family({"parser_family":"INCOMING_LOCAL", "transaction_description":"Incoming internal transfer"}) == "INTERNAL_SNB"
    assert api._family({"parser_family":"INCOMING_LOCAL", "detail_description":"Incoming internal transfer — DEP ID:1010354384"}) == "INTERNAL_SNB"
    for amount in (19999, 20000, 20001):
        assert api._family({**ips, "signed_amount":amount}) == "IPS_LOCAL"


def test_active_rule_match_requires_exact_bank_format_and_account_tail(api):
    fingerprint=hashlib.sha256(b"00000000000001").hexdigest()
    rule = types.SimpleNamespace(name="rule-1", source_bank="SNB", account_scope_hash=fingerprint, account_tail="0001",
        direction="CREDIT", narrative_family="IPS_LOCAL", hint_kind="NAME", normalized_hint="acme", display_hint="Acme",
        party_type="Customer", party="CUST-001", party_label="Acme Co")
    source = {"bank": "SNB", "account_tail": "0001", "direction":"CREDIT", "parser_family": "IPS_LOCAL",
              "detail_description": "SAUDI ARABIA ACME"}
    result = api._suggestion_for(source, [rule], fingerprint)
    assert result["party"] == "CUST-001"
    assert api._suggestion_for(source, [rule], hashlib.sha256(b"10000000000001").hexdigest()) is None
    source["account_tail"] = "0002"
    assert api._suggestion_for(source, [rule], fingerprint) is None
    source["account_tail"] = "0001"
    source["direction"] = "DEBIT"
    assert api._suggestion_for(source, [rule], fingerprint) is None


def test_party_search_allows_only_enabled_visible_customer_supplier(api, monkeypatch):
    calls = []
    def get_list(doctype, **kwargs):
        calls.append((doctype,kwargs))
        if doctype==api.PARTY_APPROVAL:
            return [types.SimpleNamespace(party='CUST-001')]
        return [types.SimpleNamespace(name="CUST-001", customer_name="Acme Trading", get=lambda key: "Acme Trading")]
    api.frappe.get_list = get_list
    assert api.search_parties("Customer", "acme")[0]["name"] == "CUST-001"
    assert calls[0][1]["filters"] == {"party_type":"Customer","status":"APPROVED"}
    assert calls[1][1]["filters"] == {"disabled":0,"name":["in",['CUST-001']]}
    assert calls[1][1]["page_length"] == 30
    assert api.search_parties("Supplier", "a") == []
    with pytest.raises(ValueError, match="Unsupported"):
        api.search_parties("Employee", "acme")


def test_non_manager_cannot_manage_approvals(api):
    api.frappe.get_roles=lambda: ['Accounts User']
    with pytest.raises(PermissionError):
        api.search_active_parties_for_approval('Customer','acme')


def test_hint_normalization_handles_arabic_and_spacing(api):
    assert api._normalize_hint("  أَكْمَة   Co.  ") == "اكمة co"


def test_manual_stable_phrase_supports_local_narrative_and_detects_conflict(api):
    source = {"bank": "SNB", "account_tail": "1001", "direction":"CREDIT", "parser_family": "INCOMING_LOCAL",
              "transaction_description": "Incoming Local transfer",
              "detail_description": "Transfer from Example Building Company reference 123"}
    fingerprint=hashlib.sha256(b"00000000001001").hexdigest()
    common = dict(source_bank="SNB", account_scope_hash=fingerprint, account_tail="1001", direction="CREDIT", narrative_family="LARGE_LOCAL",
        hint_kind="NAME", normalized_hint="example building company", display_hint="Example Building Company")
    a = types.SimpleNamespace(name="rule-a", party_type="Customer", party="CUST-A", party_label="Example Co", **common)
    b = types.SimpleNamespace(name="rule-b", party_type="Customer", party="CUST-B", party_label="Example Co (2)", **common)
    assert api._suggestion_for(source, [a], fingerprint)["party"] == "CUST-A"
    assert api._suggestion_for(source, [a, b], fingerprint)["status"] == "AMBIGUOUS_RULE"
    assert api._suggestion_for({**source, "detail_description":"TAWAL Example Building Company"}, [a], fingerprint) is None


def test_confirmed_rules_work_before_the_am_copy_is_made(api, monkeypatch):
    calls=[]
    api.frappe.get_list=lambda doctype, **kwargs: calls.append((doctype,kwargs)) or []
    assert api._active_hint_rules() == []
    assert calls[0][1]["filters"] == {"status":"ACTIVE"}


COMPANY_IBAN = "SA0380000001400010326605"   # ends in our own 14-digit account
OTHER_IBAN = "SA1234567890123456789012"


def test_incoming_internal_transfer_uses_dep_id_and_never_our_own_account(api):
    credit = {"direction": "CREDIT", "parser_family": "INCOMING_LOCAL", "transaction_description": "Incoming Internal Transfer",
              "detail_description": "01400010326605 DEP ID:2323429130 CHNL:SNB Payment Systems"}
    # The long number in an incoming narrative is the receiving (company) account, so only the DEP ID is a payer hint.
    assert api._hint_candidates(credit) == [("DEP_ID", "2323429130")]
    payer = {**credit, "detail_description": "38759875000102 DEP ID:2323429130 CHNL:SNB Payment Systems"}
    assert api._hint_candidates(payer) == [("DEP_ID", "2323429130"), ("ACCOUNT", "38759875000102")]


def test_incoming_larger_local_transfer_uses_the_payer_iban_not_ours(api):
    credit = {"direction": "CREDIT", "parser_family": "INCOMING_LOCAL", "transaction_description": "Incoming Local transfer",
              "detail_description": f"SA CHNL: SAEED BIN ZYED ST {OTHER_IBAN} payment for invoices"}
    assert api._family(credit) == "LARGE_LOCAL"
    assert api._hint_candidates(credit) == [("ACCOUNT", OTHER_IBAN)]
    own = {**credit, "detail_description": f"CITY:Jeddah {COMPANY_IBAN} CHNL:SNB Payment Systems"}
    assert api._hint_candidates(own) == []


def test_digit_hints_ignore_leading_zeros_that_sheets_may_drop(api):
    assert api._hint_key("ACCOUNT", "0038759875000102") == api._hint_key("ACCOUNT", "38759875000102")
    assert api._hint_key("DEP_ID", " 2323429130 ") == "2323429130"
    assert api._hint_key("NAME", "  Khutut   Buildings ") == "khutut buildings"
    assert api._hint_key("ACCOUNT", OTHER_IBAN) == OTHER_IBAN.lower()


def test_movement_payload_hands_the_page_its_hint_options(api):
    class Doc:
        name="m1"; modified="t"; source_key="k"; account_scope_hash=""; erp_hint_json="{}"; recognition_json="{}"
        source_json=json.dumps({"direction":"CREDIT","parser_family":"IPS_LOCAL","detail_description":"SAUDI ARABIA ACME CO"})
        def check_permission(self, permission): pass
        def get(self, key): return getattr(self, key, "")
    payload = api._movement_payload(Doc(), [])
    assert payload["family"] == "IPS_LOCAL"
    assert payload["hint_options"] == [{"kind": "NAME", "value": "ACME CO"}]


def test_child_table_controllers_exist_for_every_router_doctype():
    base = Path(__file__).parents[1] / "sig_accounting/doctype"
    for folder in ("snb_party_hint_rule_event", "snb_party_hint_rule", "snb_router_party_approval", "snb_movement_review_event"):
        assert (base / folder / f"{folder}.py").is_file(), folder
        assert json.loads((base / folder / f"{folder}.json").read_text(encoding="utf-8"))["name"]


SCOPE = hashlib.sha256(b"01400010326605").hexdigest()
SHEET_ROW = {"row": 2, "account_tail": "6605", "account_scope_hash": SCOPE, "transfer_type": "IPS_LOCAL", "hint_kind": "NAME",
             "hint_text": "Khutut Buildings", "party_type": "Customer", "erp_record_id": "CUST-1", "status": "ACTIVE", "updated_by": "owner"}


class FakeDoc:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.flags = types.SimpleNamespace(); self.events = []; self.saved = False; self.inserted = False
    def get(self, key): return getattr(self, key, None)
    def check_permission(self, permission): pass
    def append(self, field, value): self.events.append(value)
    def save(self): self.saved = True
    def insert(self): self.inserted = True; self.name = self.rule_key


@pytest.fixture
def importer(api, monkeypatch):
    owner = types.ModuleType("sig_warehouse.sig_operations.app_connections")
    owner.TODOIST_OWNER = "finance@example.com"
    monkeypatch.setitem(sys.modules, owner.__name__, owner)
    api.frappe.get_roles = lambda: ["Accounts Manager"]
    state = types.SimpleNamespace(approved={("Customer", "CUST-1"), ("Customer", "CUST-2")}, rule=None, created=[], parties={
        ("Customer", "CUST-1"): FakeDoc(disabled=0, customer_name="Khutut Co"),
        ("Customer", "CUST-2"): FakeDoc(disabled=0, customer_name="Other Co")})
    key = api._sheet_rule(SHEET_ROW)[0]["rule_key"]
    def exists(doctype, name):
        if doctype == "SNB Party Hint Rule": return key if state.rule else None
        return any(hashlib.sha256((t + "|" + n).encode()).hexdigest() == name for t, n in state.approved)
    api.frappe.db = types.SimpleNamespace(exists=exists, sql=lambda *args: None, get_value=lambda *args: "APPROVED")
    def get_doc(*args):
        if isinstance(args[0], dict):
            doc = FakeDoc(**args[0]); state.created.append(doc); return doc
        if args[0] == "SNB Party Hint Rule": return state.rule
        return state.parties[(args[0], args[1])]
    api.frappe.get_doc = get_doc
    state.key = key
    return state


def test_sheet_edit_creates_an_active_rule_that_is_already_in_sync(api, importer):
    result = api.import_sheet_hint_rules([SHEET_ROW])
    assert result == [{"row": 2, "status": "CREATED", "name": importer.key, "party_label": "Khutut Co"}]
    rule = importer.created[0]
    assert rule.inserted and rule.sync_status == "SYNCED" and rule.status == "ACTIVE" and rule.direction == "CREDIT"
    assert "Edited in Sheet Am by owner" in rule.events[0]["note"]


def test_sheet_edit_changing_the_party_updates_with_audit_instead_of_deadlocking(api, importer):
    importer.rule = FakeDoc(name=importer.key, party_type="Customer", party="CUST-1", status="ACTIVE", sync_status="SYNCED", party_label="Khutut Co")
    changed = api.import_sheet_hint_rules([{**SHEET_ROW, "erp_record_id": "CUST-2"}])[0]
    assert changed["status"] == "UPDATED"
    assert importer.rule.party == "CUST-2" and importer.rule.party_label == "Other Co" and importer.rule.saved
    assert importer.rule.events[-1]["note"].startswith("Edited in Sheet Am")
    importer.rule.saved = False
    assert api.import_sheet_hint_rules([{**SHEET_ROW, "erp_record_id": "CUST-2"}])[0]["status"] == "UNCHANGED"
    assert not importer.rule.saved


def test_sheet_rows_are_rejected_individually_with_a_reason(api, importer):
    importer.approved.discard(("Customer", "CUST-2"))
    rows = [
        {**SHEET_ROW, "row": 3, "account_scope_hash": ""},
        {**SHEET_ROW, "row": 4, "hint_text": "ab"},
        {**SHEET_ROW, "row": 5, "hint_kind": "ACCOUNT", "hint_text": "01400010326605"},
        {**SHEET_ROW, "row": 6, "erp_record_id": "CUST-2", "hint_text": "Another Payer"},
        {**SHEET_ROW, "row": 7, "party_type": "Employee"},
        {**SHEET_ROW, "row": 8, "hint_text": "Good Payer Name"},
    ]
    reasons = {r["row"]: r.get("reason") or r["status"] for r in api.import_sheet_hint_rules(rows)}
    assert reasons == {3: "unknown_account", 4: "hint_too_short", 5: "own_account_number",
                       6: "party_not_approved", 7: "invalid_party", 8: "CREATED"}


def test_one_hint_given_to_two_parties_in_the_sheet_imports_neither(api, importer):
    rows = [SHEET_ROW, {**SHEET_ROW, "row": 3, "erp_record_id": "CUST-2"}]
    results = api.import_sheet_hint_rules(rows)
    assert [r.get("reason") for r in results] == ["same_hint_two_parties"] * 2
    assert not importer.created


def test_only_the_integration_owner_may_import_sheet_rules(api, importer):
    api.frappe.session.user = "someone@example.com"
    api.frappe.get_roles = lambda: ["Accounts Manager"]
    with pytest.raises(PermissionError):
        api.import_sheet_hint_rules([SHEET_ROW])


def test_acknowledgement_does_not_mark_an_edited_rule_synced(api, monkeypatch):
    owner=types.ModuleType('sig_warehouse.sig_operations.app_connections')
    owner.TODOIST_OWNER='finance@example.com'
    monkeypatch.setitem(sys.modules,owner.__name__,owner)
    class Rule:
        name='rule-1'
        modified='2026-11-09 12:00:01'
        sync_status='PENDING'
        flags=types.SimpleNamespace()
        def check_permission(self, permission): pass
        def save(self): self.saved=True
    rule=Rule()
    api.frappe.db=types.SimpleNamespace(sql=lambda *args: None, exists=lambda *args: True)
    api.frappe.get_doc=lambda *args: rule
    result=api.acknowledge_hint_rules([{'name':'rule-1','modified':'2026-11-09 12:00:00'}])
    assert result == {'updated':0,'missing':0,'stale':['rule-1']}
    assert rule.sync_status=='PENDING'


def test_sync_lists_pending_rules_with_required_payload_fields(api, monkeypatch):
    owner=types.ModuleType('sig_warehouse.sig_operations.app_connections')
    owner.TODOIST_OWNER='finance@example.com'
    monkeypatch.setitem(sys.modules,owner.__name__,owner)
    calls=[]
    api.frappe.get_list=lambda doctype,**kwargs: calls.append((doctype,kwargs)) or []
    result=api.list_hint_rules_for_sync()
    assert result['rows']==[] and not result['has_more']
    assert calls[0][1]['filters']['sync_status'][1]==['PENDING','ERP_ONLY','FAILED']
    assert {'rule_key','normalized_hint','direction','party_label','modified'} <= set(calls[0][1]['fields'])


def test_revoking_party_approval_revokes_and_queues_its_active_rules(api):
    api.frappe.get_roles=lambda: ['Accounts Manager']
    class Document:
        def __init__(self,**values):
            self.__dict__.update(values); self.flags=types.SimpleNamespace(); self.events=[]
        def check_permission(self,permission): pass
        def append(self,field,value): self.events.append(value)
        def is_new(self): return False
        def save(self): self.saved=True
    party=Document(disabled=0)
    approval=Document(status='APPROVED')
    rule=Document(status='ACTIVE',sync_status='SYNCED')
    api.frappe.db=types.SimpleNamespace(sql=lambda *args:None,exists=lambda *args:True,count=lambda *args,**kwargs:1)
    api.frappe.get_list=lambda *args,**kwargs:[types.SimpleNamespace(name='rule-1')]
    api.frappe.get_doc=lambda doctype,name: {'Customer':party,api.PARTY_APPROVAL:approval,'SNB Party Hint Rule':rule}[doctype]
    result=api.set_party_approval('Customer','CUST-1','REVOKED')
    assert result['status']=='REVOKED' and approval.status=='REVOKED'
    assert rule.status=='REVOKED' and rule.sync_status=='PENDING'
    assert rule.events[-1]['reviewer']=='finance@example.com'

