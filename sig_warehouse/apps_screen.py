"""Frappe v16 desktop (apps screen) tiles for the SIG workspaces.

v16 shows one tile per app. The SIG workspaces (Accounting, HR, Operations, ...) are defined in the
site database, so without these tiles they are reachable only from the small switcher at the top left.
Each tile appears only for users whose roles can open that workspace (no roles on the workspace = everyone).
"""
import frappe


def _allowed(workspace):
    if not frappe.db.exists("Workspace", workspace):
        return False
    roles = frappe.get_all("Has Role", filters={"parent": workspace, "parenttype": "Workspace"}, pluck="role")
    return not roles or bool(set(roles) & set(frappe.get_roles()))


def my_work():
    return _allowed("SIG - My Work")


def accounting():
    return _allowed("SIG Accounting")


def hr():
    return _allowed("SIG HR")


def operations():
    return _allowed("SIG Operations")


def petty_cash():
    return _allowed("SIG Petty Cash")


def projects():
    return _allowed("SIG Projects")


def assets():
    return _allowed("SIG Assets")
