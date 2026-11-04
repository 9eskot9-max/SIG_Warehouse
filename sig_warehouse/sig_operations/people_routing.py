"""Restricted, revision-controlled employee operational and PC routing setup."""

import frappe
from frappe import _

from sig_warehouse.sig_warehouse.pc_review_routing import load_matrix

DOCTYPE = "SIG People Routing Setup"


def _require():
    if frappe.session.user == "Guest" or "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only System Manager can manage employee routing."), frappe.PermissionError)


@frappe.whitelist()
def get_state():
    _require()
    doc = frappe.get_single(DOCTYPE)
    matrix = load_matrix()
    return {"revision": int(doc.revision or 0), "matrix": matrix}


@frappe.whitelist(methods=["POST"])
def publish(rows, base_revision, reviewer_groups):
    """Prevent routing changes while clearance uses a separate fixed scope."""
    _require()
    frappe.throw(_("People routing is temporarily read-only: petty-cash clearance "
                   "permissions must be aligned with the published routing before changes can be saved."),
                 frappe.PermissionError)
