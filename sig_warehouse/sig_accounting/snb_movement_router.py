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
FIELDS = ("lane", "route", "category", "party_type", "party", "company", "bank_account", "counter_account", "material_treatment", "payment_reference_doctype", "payment_reference", "payment_reference_amount", "notes", "review_status")


def _data(value):
    return frappe.parse_json(value) if isinstance(value, str) else value


def _require(permission):
    if frappe.session.user == "Guest" or not frappe.has_permission(DOCTYPE, permission):
        frappe.throw(_("You do not have permission for bank movement review."), frappe.PermissionError)


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
        frappe.throw(_("Only the configured movement integration owner may ingest movements."), frappe.PermissionError)
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
            frappe.db.sql("SELECT name FROM `tabSNB Movement Review` WHERE name=%s FOR UPDATE", (name,))
            doc = frappe.get_doc(DOCTYPE, name)
            doc.check_permission("read")
            if doc.source_key != key or doc.source_json != source_json:
                results.append({"id": key, "status": "SOURCE_CONFLICT", "name": name})
            else:
                # A staging link is a hint, not proof of a readable ERP document.
                # Never change source evidence or the accountant's saved decision.
                old = _data(doc.erp_hint_json) or {}
                incoming = item.get("erp") or {}
                old_link = str(old.get("linked_doc") or "").strip()
                new_link = str(incoming.get("linked_doc") or "").strip()
                if old_link and new_link and old_link != new_link:
                    results.append({"id": key, "status": "HINT_CONFLICT", "name": name})
                elif new_link and not old_link:
                    old.update({"linked_doc": new_link, "readback_status": "NEEDS_LIVE_READBACK"})
                    doc.erp_hint_json = _json(old)
                    doc.flags.snb_router_write = True
                    doc.save()
                    results.append({"id": key, "status": "HINT_UPDATED", "name": name})
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


@frappe.whitelist()
def list_marked_documents(doctype, start=0, limit=100):
    """List visible bank-marked accounting documents without creating review records.

    The Journal Entry field denotes statement evidence, not necessarily SNB;
    don't infer a bank from it. User Permissions still apply via get_list.
    """
    _require("read")
    marker = {"Payment Entry": "custom_snb_idempotency_key",
              "Journal Entry": "custom_pc_statement_key"}.get(doctype)
    if not marker:
        frappe.throw(_("Unsupported accounting document type."))
    if not frappe.has_permission(doctype, "read"):
        return {"available": False, "rows": []}
    start = max(0, int(start))
    limit = min(200, max(1, int(limit)))
    rows = frappe.get_list(doctype, filters={marker: ["is", "set"]},
                           fields=["name", "docstatus", "posting_date", marker],
                           order_by="posting_date desc, name asc", start=start, page_length=limit)
    return {"available": True, "rows": [{"doctype": doctype, "name": row.name,
            "docstatus": row.docstatus, "posting_date": str(row.posting_date or ""),
            "statement_key": row.get(marker),
            "bank": "SNB" if doctype == "Payment Entry" else "UNCONFIRMED"} for row in rows]}


@frappe.whitelist()
def get_supplier_payment_references(name, supplier, company):
    """Return permission-filtered submitted SAR PO/PI references for one debit."""
    _require("read")
    movement = frappe.get_doc(DOCTYPE, name)
    movement.check_permission("read")
    if movement.direction != "DEBIT":
        frappe.throw(_("Payment references are available only for outgoing bank movements."))
    supplier = str(supplier or "").strip()
    company = str(company or "").strip()
    if not supplier or not company:
        return {"purchase_orders": [], "purchase_invoices": []}
    _check_link("Supplier", supplier)
    _check_link("Company", company)
    common = {"supplier": supplier, "company": company, "currency": movement.currency, "docstatus": 1}
    orders = frappe.get_list(
        "Purchase Order", filters=common,
        fields=["name", "transaction_date", "currency", "grand_total", "advance_paid", "status"],
        order_by="transaction_date desc", page_length=100,
    )
    invoice_filters = {**common, "outstanding_amount": [">", 0]}
    invoices = frappe.get_list(
        "Purchase Invoice", filters=invoice_filters,
        fields=["name", "posting_date", "currency", "grand_total", "outstanding_amount", "status"],
        order_by="posting_date desc", page_length=100,
    )
    return {"purchase_orders": orders, "purchase_invoices": invoices}


def _validate_payment_reference(movement, clean):
    doctype = clean["payment_reference_doctype"]
    name = clean["payment_reference"]
    amount = flt(clean["payment_reference_amount"])
    has_type_or_name = bool(doctype or name)
    if not has_type_or_name:
        if amount:
            frappe.throw(_("Clear the payment reference amount when no document is selected."))
        return
    if doctype not in ("Purchase Order", "Purchase Invoice") or not name:
        frappe.throw(_("Select a Purchase Order or Purchase Invoice."))
    supplier_routes = {"SUPPLIER_PAYMENT", "MATERIAL_SUPPLIER_PAYMENT", "SUBCONTRACTOR_PAYMENT", "MAINTENANCE_PAYMENT", "LOGISTICS_PAYMENT"}
    if (clean["party_type"] != "Supplier" or not clean["party"] or movement.direction != "DEBIT"
            or clean["lane"] != "PAYMENTS" or clean["route"] not in supplier_routes):
        frappe.throw(_("A payment reference needs an outgoing movement linked to its Supplier."))
    if not clean["company"]:
        frappe.throw(_("Choose a Company before linking a supplier document."))
    bank_amount = abs(flt(movement.amount))
    if amount <= 0 or amount - bank_amount > 0.005:
        frappe.throw(_("The reference amount must be positive and cannot exceed the bank movement."))
    reference = frappe.get_doc(doctype, name)
    reference.check_permission("read")
    if (reference.docstatus != 1 or reference.supplier != clean["party"]
            or reference.company != clean["company"] or reference.currency != movement.currency):
        frappe.throw(_("The selected document must be submitted and match the Supplier, Company, and bank currency."))
    if doctype == "Purchase Invoice" and amount - flt(reference.outstanding_amount) > 0.005:
        frappe.throw(_("The Purchase Invoice has less outstanding than the selected allocation."))


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
    clean = {field: str(data.get(field) or "").strip()[:2000 if field == "notes" else 140] for field in FIELDS if field != "payment_reference_amount"}
    clean["payment_reference_amount"] = flt(data.get("payment_reference_amount"))
    if clean["lane"] not in LANES or clean["route"] not in ROUTES or clean["review_status"] not in STATUSES:
        frappe.throw(_("Choose a valid lane, route, and review state."))
    if clean["party_type"] not in ("", "Customer", "Supplier", "Employee", "Other") or clean["material_treatment"] not in ("", "STOCK", "OPERATIONAL_NON_STOCK"):
        frappe.throw(_("Invalid party or material treatment."))
    if clean["party"] and clean["party_type"] in ("Customer", "Supplier", "Employee"):
        _check_link(clean["party_type"], clean["party"])
    for field, doctype in (("company", "Company"), ("bank_account", "Account"), ("counter_account", "Account")):
        _check_link(doctype, clean[field])
    _validate_payment_reference(doc, clean)
    previous = {field: doc.get(field) for field in FIELDS}
    doc.update(clean)
    doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "previous_json": _json(previous), "decision_json": _json(clean)})
    doc.flags.snb_router_write = True
    doc.save()
    return get_movement(doc.name)
