"""Cancelled draft history must not block legitimate later assignments."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def assignment(monkeypatch):
    frappe = types.ModuleType("frappe")
    frappe.__path__ = []
    model = types.ModuleType("frappe.model")
    model.__path__ = []
    document = types.ModuleType("frappe.model.document")
    document.Document = type("Document", (), {})
    frappe.get_all = lambda *args, **kwargs: frappe.rows
    frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
    for name, module in (("frappe", frappe), ("frappe.model", model),
                         ("frappe.model.document", document)):
        monkeypatch.setitem(sys.modules, name, module)
    path = Path(__file__).resolve().parents[1] / "sig_hr/doctype/sig_employee_project_assignment/sig_employee_project_assignment.py"
    spec = importlib.util.spec_from_file_location("assignment_overlap_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    doc = module.SIGEmployeeProjectAssignment()
    doc.name, doc.employee, doc.project, doc.project_role = "new", "E1", "P1", "Team Member"
    doc.start_date, doc.end_date, doc.status = "2026-11-05", None, "Draft"
    return frappe, doc


def test_cancelled_draft_does_not_block_new_assignment(assignment):
    frappe, doc = assignment
    frappe.rows = [types.SimpleNamespace(name="old", project_role="Team Member", start_date="2026-11-05", end_date=None, status="Cancelled")]
    doc._validate_overlap()


@pytest.mark.parametrize("status", ["Draft", "Active", "Ended"])
def test_actual_overlaps_still_block(assignment, status):
    frappe, doc = assignment
    frappe.rows = [types.SimpleNamespace(name="old", project_role="Team Member", start_date="2026-11-05", end_date="2026-12-01", status=status)]
    with pytest.raises(ValueError, match="overlapping"):
        doc._validate_overlap()


def test_cancelling_a_draft_does_not_create_an_overlap_error(assignment):
    frappe, doc = assignment
    doc.status = "Cancelled"
    frappe.rows = [types.SimpleNamespace(name="old", project_role="Team Member", start_date="2026-11-05", end_date=None, status="Active")]
    doc._validate_overlap()
