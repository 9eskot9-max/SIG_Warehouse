"""Regression for reviewer Employee defaults entering the Finance funding hook."""

import importlib.util
from pathlib import Path
import sys
import types

import pytest


class Denied(Exception):
    pass


class Doc(dict):
    doctype = "Journal Entry"

    def get_doc_before_save(self):
        return getattr(self, "before", None)


@pytest.fixture
def funding(monkeypatch):
    fake = types.ModuleType("frappe")
    fake.PermissionError = Denied
    fake.get_roles = lambda: ["Employee", "SIG PC Clearance"]
    fake.whitelist = lambda **kwargs: lambda fn: fn
    fake.new_doc = lambda doctype, as_dict: {
        "custom_pc_employee": "HR-EMP-00028", "custom_pc_top_up": 0,
    }
    def throw(message, exc=None):
        raise (exc or ValueError)(message)
    fake.throw = throw
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda value: int(value or 0)
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    path = Path(__file__).parents[1] / "sig_warehouse/pc_funding.py"
    spec = importlib.util.spec_from_file_location("pc_funding_regression", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("unchecked", [None, 0, "0"])
def test_reviewer_can_validate_clearance_with_own_employee_default(funding, unchecked):
    doc = Doc(custom_pc_receipt="RECEIPT-1", custom_pc_employee="HR-EMP-00028",
              custom_pc_top_up=unchecked)
    funding.validate_journal_entry(doc)


@pytest.mark.parametrize("field", [
    "custom_pc_top_up", "custom_pc_employee", "custom_pc_funding_date",
    "custom_pc_funding_source", "custom_pc_bank_txn_id",
    "custom_pc_bank_journal_number", "custom_pc_statement_key",
    "custom_pc_funding_source_key", "custom_pc_transfer_category",
])
def test_reviewer_cannot_set_funding_fields(funding, field):
    doc = Doc(custom_pc_employee="HR-EMP-00028", custom_pc_top_up=0)
    doc[field] = 1 if field == "custom_pc_top_up" else "explicit funding change"
    with pytest.raises(Denied, match="Only Finance"):
        funding.validate_journal_entry(doc)


def test_existing_funding_field_edits_remain_finance_only(funding):
    doc = Doc(custom_pc_top_up=0, custom_pc_employee="HR-EMP-00025")
    doc.before = Doc(custom_pc_top_up=0, custom_pc_employee="HR-EMP-00028")
    with pytest.raises(Denied, match="Only Finance"):
        funding.validate_journal_entry(doc)


def test_blank_and_checkbox_serialization_do_not_count_as_edits(funding):
    doc = Doc(custom_pc_top_up="0", custom_pc_employee="HR-EMP-00028",
              custom_pc_funding_source="")
    doc.before = Doc(custom_pc_top_up=0, custom_pc_employee="HR-EMP-00028",
                     custom_pc_funding_source=None)
    funding.validate_journal_entry(doc)


def test_existing_top_up_still_requires_finance(funding):
    doc = Doc(custom_pc_top_up=1, custom_pc_employee="HR-EMP-00028")
    doc.before = Doc(doc)
    with pytest.raises(Denied, match="Only Finance"):
        funding.validate_journal_entry(doc)


def test_finance_can_designate_valid_top_up(funding, monkeypatch):
    funding.frappe.get_roles = lambda: ["Accounts User"]
    funding.frappe.get_all = lambda *args, **kwargs: ["BANK"]
    funding.frappe.db = types.SimpleNamespace(get_value=lambda *args: None)
    monkeypatch.setattr(funding, "_active_employee", lambda *args: "CUSTODY")
    doc = Doc(custom_pc_top_up=1, custom_pc_employee="HR-EMP-00025",
              custom_pc_funding_date="2026-10-26", custom_pc_funding_source="Manual Finance",
              accounts=[types.SimpleNamespace(account="CUSTODY", debit=100, credit=0),
                        types.SimpleNamespace(account="BANK", debit=0, credit=100)])
    doc.docstatus, doc.company, doc.name = 0, "SIG", "JE-FUND"
    funding.validate_journal_entry(doc)
    assert doc.custom_pc_funding_source_key == "MANUAL:JE-FUND"
    doc["accounts"][1].debit = 1
    with pytest.raises(ValueError, match="must debit the Employee custody"):
        funding.validate_journal_entry(doc)
