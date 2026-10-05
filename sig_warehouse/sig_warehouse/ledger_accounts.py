"""Ledger accounts that SIG Warehouse documents post to (single source of truth).

Material consumption (Material Issue) and its returns must hit the materials expense account, never the
Company stock-adjustment default (5129), which is reserved for count / valuation differences.
Owner and accountant decision 2026-10-04. The live Server Scripts ``sig_se_expense_5121_before_save`` and
``sig_se_expense_5121_before_submit`` enforce the same rule as a safety net for every other creation path;
setting it here as well makes the document correct at creation, independent of those scripts.
"""

MATERIALS_EXPENSE_ACCOUNT = "5121 - مواد - SIG"
