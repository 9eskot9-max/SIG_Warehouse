"""Seed Bank Counterparty records from the Sheet Am beneficiary registry. Idempotent; never overwrites a filled field.

`plan()` is pure. `apply()` writes through Frappe. The registry is mined, not trusted: a Supplier link counts only
when that Supplier exists and is enabled in ERP, and corrupted values (the '????' encoding damage) are ignored.
"""
import hashlib
import re

from .adapters.snb import TAWAL_PATTERN
from .text import DEFAULT_COMPANY_SCOPES, hint_key, is_company_number, normalize_text

PREFIX_LENGTH = 30
MIN_NAME = 4


def _clean(value):
    value = str(value or "").strip()
    return "" if (not value or "???" in value) else value


def plan(b, suppliers, supplier_names, own_names, scopes=DEFAULT_COMPANY_SCOPES, categories=None):
    """What one beneficiary contributes. `suppliers` is the set of enabled Supplier ids, `supplier_names` {name: id}."""
    categories = categories or {}
    names = [n for n in (_clean(b.get("beneficiary_name")), _clean(b.get("nickname"))) if n]
    display = names[0] if names else _clean(b.get("erp_party")) or "Unnamed beneficiary"
    identifiers = []
    account = re.sub(r"\D", "", str(b.get("account_number") or ""))
    iban = re.sub(r"\s", "", str(b.get("iban") or "")).upper()
    own = False
    if len(account) >= 8:
        if is_company_number(account, scopes):
            own = True
        else:
            identifiers.append(("ACCOUNT", account))
    if re.fullmatch(r"SA\d{22}", iban):
        if is_company_number(iban, scopes):
            own = True
        else:
            identifiers.append(("IBAN", iban))
    for name in names:
        key = normalize_text(name)
        if len(key) >= MIN_NAME:
            identifiers.append(("NAME", name))
            if len(key) > PREFIX_LENGTH:
                identifiers.append(("NAME", key[:PREFIX_LENGTH].strip()))
    erp_party = str(b.get("erp_party") or "")
    record = _clean(b.get("erp_record_id"))
    supplier = ""
    if record in suppliers:
        supplier = record
    else:
        match = re.match(r"^Supplier:\s*(.+)$", erp_party, re.I)
        if match:
            wanted = _clean(match.group(1))
            supplier = wanted if wanted in suppliers else supplier_names.get(wanted, "")
    employee = re.match(r"^Employee:\s*([^|]+)\|\s*(\d+)", erp_party)
    route = str(b.get("proposed_route") or "")
    category = route.split("|")[1] if "|" in route and route.split("|")[0] in ("JE_PERSON", "PAY_SUPPLIER") else ""
    own = own or any(normalize_text(n) in own_names or any(normalize_text(n).startswith(o) for o in own_names) for n in names)
    return {"am_key": str(b.get("source_key") or ""), "display_name": display, "identifiers": identifiers, "supplier": supplier,
            "is_employee": bool(employee), "custody_gl": employee.group(2) if employee else "", "category": category,
            "expense_account": categories.get(category, "") if route.startswith("JE_PERSON") else "",
            "is_company": own, "handler": "TAWAL" if any(TAWAL_PATTERN.search(n) for n in names) else ""}


def apply(rows):
    """Create or complete counterparties and identifiers. Returns counts plus duplicate identifiers that were left alone."""
    import frappe
    from frappe.utils import getdate, nowdate

    from .runtime import IDENTIFIER, COUNTERPARTY, Settings, identity_key
    from .documents import COMPANY

    s = Settings()
    suppliers = {r.name: r.supplier_name for r in frappe.get_all("Supplier", fields=["name", "supplier_name"], filters={"disabled": 0}, limit_page_length=0)}
    supplier_names = {n: i for i, n in suppliers.items()}
    existing_cp = {r.am_key: r for r in frappe.get_all(COUNTERPARTY, fields=["name", "am_key", "supplier", "custody_account", "employee",
                   "expense_account", "category", "is_company", "handler", "is_employee"], filters={"am_key": ["!=", ""]}, limit_page_length=0)}
    existing_ids = {r.name: r.counterparty for r in frappe.get_all(IDENTIFIER, fields=["name", "counterparty"], limit_page_length=0)}
    employees = {}
    for e in frappe.get_all("Employee", fields=["name", "custom_custody_account"], filters={"status": "Active", "custom_custody_account": ["!=", ""]}, limit_page_length=0):
        employees.setdefault(e.custom_custody_account, []).append(e.name)
    counts = {"counterparties_created": 0, "counterparties_updated": 0, "identifiers_created": 0, "duplicates": [], "skipped": 0}
    for b in rows:
        p = plan(b, set(suppliers), supplier_names, s.own_names, s.company_scopes, s.categories)
        if not p["am_key"]:
            counts["skipped"] += 1
            continue
        custody = ""
        if p["custody_gl"]:
            custody = frappe.db.get_value("Account", {"account_number": p["custody_gl"], "company": COMPANY}, "name") or ""
        employee = employees.get(custody, [None])[0] if len(employees.get(custody, [])) == 1 else ""
        cp = existing_cp.get(p["am_key"])
        if cp is None:
            doc = frappe.get_doc({"doctype": COUNTERPARTY, "display_name": p["display_name"][:140], "status": "ACTIVE", "am_key": p["am_key"],
                                  "is_company": cint_(p["is_company"]), "handler": p["handler"], "is_employee": cint_(p["is_employee"]),
                                  "custody_account": custody or None, "employee": employee or None,
                                  "supplier": p["supplier"] or None if not p["is_company"] else None,
                                  "expense_account": p["expense_account"] or None, "category": p["category"]})
            doc.flags.bank_router_write = True
            doc.insert()
            cp_name = doc.name
            counts["counterparties_created"] += 1
        else:
            cp_name = cp.name
            fills = {}
            for field, value in (("supplier", p["supplier"]), ("custody_account", custody), ("employee", employee),
                                 ("expense_account", p["expense_account"]), ("category", p["category"])):
                if value and not cp.get(field) and not (field == "supplier" and (p["is_company"] or cp.is_company)):
                    fills[field] = value
            for field, value in (("is_company", cint_(p["is_company"])), ("is_employee", cint_(p["is_employee"]))):
                if value and not cp.get(field):
                    fills[field] = value
            if p["handler"] and not cp.handler:
                fills["handler"] = p["handler"]
            if fills:
                doc = frappe.get_doc(COUNTERPARTY, cp_name)
                doc.update(fills)
                doc.flags.bank_router_write = True
                doc.save()
                counts["counterparties_updated"] += 1
        for kind, value in p["identifiers"]:
            key = identity_key(kind, value)
            owner = existing_ids.get(key)
            if owner is None:
                ident = frappe.get_doc({"doctype": IDENTIFIER, "identity_key": key, "counterparty": cp_name, "kind": kind, "value": str(value)[:140],
                                        "normalized": hint_key(kind, value), "status": "ACTIVE", "source": "SEED_AM", "first_seen": nowdate()})
                ident.flags.bank_router_write = True
                ident.insert()
                existing_ids[key] = cp_name
                counts["identifiers_created"] += 1
            elif owner != cp_name:
                counts["duplicates"].append({"kind": kind, "value": str(value)[:60], "kept": owner, "other": cp_name})
    counts["duplicates"] = counts["duplicates"][:50]
    return counts


def cint_(value):
    return 1 if value else 0
