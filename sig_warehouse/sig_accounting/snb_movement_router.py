"""ERP persistence for the local SNB recognition queue. No ledger posting occurs here."""
import hashlib
import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

DOCTYPE = "SNB Movement Review"
LANES = {"RECEIPTS", "PAYMENTS", "OWN_ACCOUNTS", "OTHER", "DEFERRED"}
ROUTES = {"CUSTOMER_RECEIPT", "OWN_ACCOUNT_TRANSFER", "PETTY_CASH_FUNDING", "SUPPLIER_PAYMENT", "MATERIAL_SUPPLIER_PAYMENT", "SUBCONTRACTOR_PAYMENT", "MAINTENANCE_PAYMENT", "LOGISTICS_PAYMENT", "HR_EMPLOYEE_PAYMENT", "SALARY_PAYMENT", "SADAD_PAYMENT", "EMPLOYEE_PAYMENT", "OTHER", "DEFERRED_TAWAL", "DEFERRED_XXCL"}
STATUSES = {"PENDING", "REVIEWED", "NEEDS_CLARIFICATION", "DEFERRED"}
FIELDS = ("lane", "route", "category", "party_type", "party", "company", "bank_account", "counter_account", "material_treatment", "notes", "review_status")


def _data(value):
    return frappe.parse_json(value) if isinstance(value, str) else value


def _require(permission):
    if frappe.session.user == "Guest" or not frappe.has_permission(DOCTYPE, permission):
        frappe.throw(_("You do not have permission for SNB movement review."), frappe.PermissionError)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _check_link(doctype, name):
    if name:
        doc = frappe.get_doc(doctype, name)
        doc.check_permission("read")


@frappe.whitelist(methods=["POST"])
def ingest(items):
    """Import local recognition items, preserving previously reviewed decisions.

    This method is deliberately limited to the configured integration owner or System Manager.
    Exact repeats are idempotent; conflicting source evidence is reported, never overwritten.
    """
    _require("create")
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the SNB integration owner may ingest movements."), frappe.PermissionError)
    rows = _data(items)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        frappe.throw(_("Send between 1 and 100 movements per request."))
    results = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("source"), dict):
            frappe.throw(_("Invalid movement item."))
        source = item["source"]
        key = str(item.get("id") or "").strip()
        if not key or len(key) > 140 or source.get("direction") not in ("CREDIT", "DEBIT") or not source.get("event_date"):
            frappe.throw(_("Movement identity, date, and direction are required."))
        source_json = _json(source)
        if len(source_json) > 50000:
            frappe.throw(_("Movement evidence exceeds the size limit."))
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        if frappe.db.exists(DOCTYPE, name):
            doc = frappe.get_doc(DOCTYPE, name)
            doc.check_permission("read")
            if doc.source_key != key or doc.source_json != source_json:
                results.append({"id": key, "status": "SOURCE_CONFLICT", "name": name})
            else:
                results.append({"id": key, "status": "EXISTS", "name": name})
            continue
        doc = frappe.new_doc(DOCTYPE)
        doc.update({"source_hash": name, "source_key": key, "event_date": source["event_date"], "source_account_tail": str(source.get("account_tail") or "")[-4:], "direction": source["direction"], "amount": flt(source.get("signed_amount")), "currency": source.get("currency") or "SAR", "source_json": source_json, "recognition_json": _json(item.get("recognition") or {}), "erp_hint_json": _json(item.get("erp") or {}), "review_status": "PENDING"})
        doc.flags.snb_router_write = True
        doc.insert()
        results.append({"id": key, "status": "CREATED", "name": name})
    return results


@frappe.whitelist()
def list_movements(start=0, limit=100):
    _require("read")
    start = max(0, int(start)); limit = min(200, max(1, int(limit)))
    rows = frappe.get_list(DOCTYPE, fields=["name"], order_by="event_date desc, name asc", start=start, page_length=limit)
    return [get_movement(row.name) for row in rows]


@frappe.whitelist()
def get_movement(name):
    _require("read")
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("read")
    return {"name": doc.name, "modified": doc.modified, "id": doc.source_key, "source": _data(doc.source_json) or {}, "recognition": _data(doc.recognition_json) or {}, "erp": _data(doc.erp_hint_json) or {}, "review": {field: doc.get(field) for field in FIELDS}}


@frappe.whitelist(methods=["POST"])
def save_review(name, modified, decision):
    _require("write")
    # Serialize updates so two accountants cannot both pass the version check.
    frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (name,))
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw(_("This movement changed since you opened it. Refresh and review again."))
    data = _data(decision)
    if not isinstance(data, dict):
        frappe.throw(_("Invalid review decision."))
    clean = {field: str(data.get(field) or "").strip()[:2000 if field == "notes" else 140] for field in FIELDS}
    if clean["lane"] not in LANES or clean["route"] not in ROUTES or clean["review_status"] not in STATUSES:
        frappe.throw(_("Choose a valid lane, route, and review state."))
    if clean["party_type"] not in ("", "Customer", "Supplier", "Employee", "Other") or clean["material_treatment"] not in ("", "STOCK", "OPERATIONAL_NON_STOCK"):
        frappe.throw(_("Invalid party or material treatment."))
    if clean["party"] and clean["party_type"] in ("Customer", "Supplier", "Employee"):
        _check_link(clean["party_type"], clean["party"])
    for field, doctype in (("company", "Company"), ("bank_account", "Account"), ("counter_account", "Account")):
        _check_link(doctype, clean[field])
    previous = {field: doc.get(field) for field in FIELDS}
    doc.update(clean)
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json(previous), "decision_json": _json(clean)})
    doc.flags.snb_router_write = True
    doc.save()
    return get_movement(doc.name)
