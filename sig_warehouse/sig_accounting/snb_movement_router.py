"""ERP persistence for the local SNB recognition queue. No ledger posting occurs here."""
import hashlib
import json
import re
import unicodedata

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

DOCTYPE = "SNB Movement Review"
LANES = {"RECEIPTS", "PAYMENTS", "OWN_ACCOUNTS", "OTHER", "DEFERRED"}
ROUTES = {"CUSTOMER_RECEIPT", "OWN_ACCOUNT_TRANSFER", "PETTY_CASH_FUNDING", "SUPPLIER_PAYMENT", "MATERIAL_SUPPLIER_PAYMENT", "SUBCONTRACTOR_PAYMENT", "MAINTENANCE_PAYMENT", "LOGISTICS_PAYMENT", "HR_EMPLOYEE_PAYMENT", "SALARY_PAYMENT", "SADAD_PAYMENT", "EMPLOYEE_PAYMENT", "OTHER", "DEFERRED_TAWAL", "DEFERRED_XXCL"}
STATUSES = {"PENDING", "REVIEWED", "NEEDS_CLARIFICATION", "DEFERRED"}
FIELDS = ("lane", "route", "category", "party_type", "party", "company", "bank_account", "counter_account", "material_treatment", "payment_reference_doctype", "payment_reference", "payment_reference_amount", "notes", "review_status")
PARTY_DOCTYPES = {"Customer", "Supplier"}
HINT_KINDS = {"NAME", "ACCOUNT", "BEN_ID", "DEP_ID"}
MIN_HINT_LENGTH = {"NAME": 4, "ACCOUNT": 8, "BEN_ID": 3, "DEP_ID": 5}
PARTY_APPROVAL = "SNB Router Party Approval"
# Fingerprints and GL numbers mirror the two SNB mappings in the existing local importer.
SNB_BANK_GL_BY_SCOPE = {
    "f98451763299c21a58d649ad9118abe9fca723cfd0a2ca00fe65238d98bbe3fb": "13121",
    "370b2d40789076a4688a328253800d1574bcb2ebbab14add0c1acb0d7dfe1b9e": "13123",
}


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


def _normalize_hint(value):
    value = unicodedata.normalize("NFKD", str(value or "")).strip().casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[\u0640]", "", value)
    value = re.sub(r"[أإآ]", "ا", value)
    return " ".join(re.findall(r"[\w]+", value, flags=re.UNICODE))


def _hint_key(kind, value):
    """Stable comparison form. Digit-only identifiers ignore leading zeros, which Sheets may drop."""
    text = _normalize_hint(value)
    if kind == "NAME":
        return text
    compact = text.replace(" ", "")
    return compact.lstrip("0") if compact.isdigit() else compact


def _is_company_number(value):
    """True when a long number is one of our own SNB accounts (compared by fingerprint, never stored).

    Incoming narratives usually carry the receiving account, so it must never become a payer hint.
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 10:
        return False
    return hashlib.sha256(digits[-14:].zfill(14).encode("utf-8")).hexdigest() in SNB_BANK_GL_BY_SCOPE


def _family(source):
    """Use parser/narrative evidence, never amount, to separate SNB formats."""
    parser = str(source.get("parser_family") or "").upper()
    description = str(source.get("transaction_description") or "").upper()
    detail = " ".join(str(source.get(k) or "") for k in ("detail_description", "extra_description", "remarks")).upper()
    if re.search(r"\b(?:INCOMING\s+)?(?:INTERNAL|SNB|WITHIN\s+BANK)\s+TRANSFER\b", description + " " + detail):
        return "INTERNAL_SNB"
    if parser == "IPS_LOCAL" or "SAUDI ARABIA" in detail:
        return "IPS_LOCAL"
    if parser == "INTERNAL_BEN_ID" or "BEN ID:" in detail:
        return "INTERNAL_SNB"
    if parser in ("LOCAL_OTBANK", "INCOMING_LOCAL") or "INCOMING LOCAL" in description:
        return "LARGE_LOCAL"
    return ""


def _hint_candidates(source):
    family = _family(source)
    if not family:
        return []
    detail = " ".join(str(source.get(k) or "") for k in ("detail_description", "extra_description", "remarks"))
    values = []
    # Outgoing narratives say BEN ID, incoming ones say DEP ID; both name the other party.
    party_id = re.search(r"(?P<label>BEN|DEP)\s*ID\s*:\s*(?P<value>\d+)", detail, re.I)
    account = re.search(r"(\d{10,24})\s+(?:BEN|DEP)\s*ID\s*:", detail, re.I)
    otbank = re.search(r"OTBANK\s*:\s*[A-Z]{4}(.+)$", detail, re.I)
    ips = re.search(r"SAUDI\s+ARABIA\s+(.+)$", detail, re.I)
    iban = re.search(r"(?<![A-Z0-9])(SA\d{22})(?!\d)", detail, re.I)
    if family == "INTERNAL_SNB" and party_id:
        # The account in an internal-transfer narrative is the other side. When that is one of ours (as DEP ID/BEN ID then
        # carry our own company ID), it is an own-account transfer: there is no payer or payee to remember.
        if account and _is_company_number(account.group(1)):
            return []
        values.append(("BEN_ID" if party_id.group("label").upper() == "BEN" else "DEP_ID", party_id.group("value")))
        if account and not _is_company_number(account.group(1)):
            values.append(("ACCOUNT", account.group(1)))
    elif family == "IPS_LOCAL" and ips:
        values.append(("NAME", ips.group(1)))
    elif family == "LARGE_LOCAL":
        if otbank:
            values.append(("NAME", otbank.group(1)))
        # The transfer's own IBAN is the stable payer identifier when the bank gives no name.
        if iban and not _is_company_number(iban.group(1)):
            values.append(("ACCOUNT", iban.group(1).upper()))
    return [(kind, value.strip()) for kind, value in values if value and _hint_key(kind, value)]


def _active_hint_rules():
    # ERP is authoritative: a confirmed rule works at once. Am receives a copy on the next sync.
    rules = frappe.get_list("SNB Party Hint Rule", filters={"status": "ACTIVE"},
        fields=["name", "source_bank", "account_scope_hash", "account_tail", "direction", "narrative_family", "hint_kind",
                "normalized_hint", "display_hint", "party_type", "party", "party_label"],
        order_by="modified desc", page_length=5000)
    visible = _visible_party_rules(rules, enabled_only=True)
    approvals = frappe.get_list(PARTY_APPROVAL, filters={"status": "APPROVED"}, fields=["party_type", "party"], page_length=5000)
    allowed = {(row.party_type, row.party) for row in approvals}
    return [rule for rule in visible if (rule.party_type, rule.party) in allowed]


def _visible_party_rules(rules, enabled_only=False):
    visible = {}
    for doctype in PARTY_DOCTYPES:
        names = list({rule.party for rule in rules if rule.party_type == doctype and rule.party})
        if not names or not frappe.has_permission(doctype, "read"):
            visible[doctype] = set()
            continue
        filters = {"name": ["in", names]}
        if enabled_only:
            filters["disabled"] = 0
        visible[doctype] = {row.name for row in frappe.get_list(doctype,
            filters=filters, fields=["name"], page_length=5000)}
    return [rule for rule in rules if rule.party in visible.get(rule.party_type, set())]


def _suggestion_for(source, rules, account_scope_hash):
    """Return an exact, account-tail and format scoped hint suggestion only."""
    candidates = _hint_candidates(source)
    matches = []
    # A reviewer may define a stable name fragment when the bank's local-transfer
    # narrative is not parsed into a dedicated field. Match that exact phrase only.
    narrative = _normalize_hint(" ".join(str(source.get(k) or "") for k in
        ("transaction_description", "detail_description", "extra_description", "remarks")))
    if re.search(r"\bTAWAL\b|TELECOMMUNICATIONS?\s+TOWERS", narrative, re.I):
        return None
    bank = str(source.get("bank") or "SNB").upper()
    account_tail = str(source.get("account_tail") or "")[-4:]
    family = _family(source)
    if not re.fullmatch(r"[0-9a-f]{64}", str(account_scope_hash or "")):
        return None
    exact = {(kind, _hint_key(kind, value)) for kind, value in candidates}
    for row in rules:
        if (str(row.source_bank).upper() != bank or str(row.account_tail)[-4:] != account_tail or
                str(row.account_scope_hash or "") != account_scope_hash or row.direction != source.get("direction") or
                row.narrative_family != family):
            continue
        if (row.hint_kind, row.normalized_hint) in exact or (row.hint_kind == "NAME" and row.normalized_hint and
                f" {row.normalized_hint} " in f" {narrative} "):
            matches.append(row)
    matches = list({row.name: row for row in matches}.values())
    parties = {(row.party_type, row.party) for row in matches}
    if len(parties) > 1:
        return {"status": "AMBIGUOUS_RULE", "candidates": [{"party_type": row.party_type, "party": row.party,
                "party_label": row.party_label, "hint": row.display_hint} for row in matches],
                "narrative_family": _family(source)}
    if matches:
        row = matches[0]
        return {"status": "RULE_SUGGESTION", "source": "ERP confirmed rule", "rule": row.name,
                "party_type": row.party_type, "party": row.party, "party_label": row.party_label,
                "hint_kind": row.hint_kind, "hint_value": row.display_hint, "narrative_family": _family(source)}
    return None


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
        account_scope_hash = str(item.get("account_scope_hash") or "").lower()
        if account_scope_hash and not re.fullmatch(r"[0-9a-f]{64}", account_scope_hash):
            frappe.throw(_("Invalid account scope fingerprint."))
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
                derived_changed = False
                scope_changed = False
                if account_scope_hash:
                    stored_scope = str(doc.account_scope_hash or "")
                    if stored_scope and stored_scope != account_scope_hash:
                        results.append({"id": key, "status": "ACCOUNT_SCOPE_CONFLICT", "name": name})
                        continue
                    if not stored_scope:
                        doc.account_scope_hash = account_scope_hash
                        scope_changed = True
                old_recognition = _data(doc.recognition_json) or {}
                incoming_recognition = item.get("recognition") or {}
                for derived_field in ("related_fee_rows", "related_main_key", "category", "am_category_status",
                                      "transfer_request", "am_beneficiary_mapping"):
                    if derived_field in incoming_recognition and old_recognition.get(derived_field) != incoming_recognition[derived_field]:
                        old_recognition[derived_field] = incoming_recognition[derived_field]
                        derived_changed = True
                if derived_changed:
                    doc.recognition_json = _json(old_recognition)
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
                elif derived_changed or scope_changed:
                    doc.flags.snb_router_write = True
                    doc.save()
                    results.append({"id": key, "status": "DERIVED_UPDATED" if derived_changed else "ACCOUNT_SCOPE_UPDATED", "name": name})
                else:
                    results.append({"id": key, "status": "EXISTS", "name": name})
            continue
        doc = frappe.new_doc(DOCTYPE)
        doc.update({"source_hash": name, "source_key": key, "event_date": source["event_date"], "source_account_tail": str(source.get("account_tail") or "")[-4:], "account_scope_hash": account_scope_hash, "direction": source["direction"], "amount": flt(source.get("signed_amount")), "currency": source.get("currency") or "SAR", "source_json": source_json, "recognition_json": _json(item.get("recognition") or {}), "erp_hint_json": _json(item.get("erp") or {}), "review_status": "PENDING"})
        doc.flags.snb_router_write = True
        doc.insert()
        results.append({"id": key, "status": "CREATED", "name": name})
    return results


@frappe.whitelist()
def list_movements(start=0, limit=100):
    _require("read")
    start = max(0, int(start)); limit = min(200, max(1, int(limit)))
    rows = frappe.get_list(DOCTYPE, fields=["name"], order_by="event_date desc, name asc", start=start, page_length=limit)
    rules = _active_hint_rules()
    return [_movement_payload(frappe.get_doc(DOCTYPE, row.name), rules) for row in rows]


@frappe.whitelist()
def get_movement(name):
    _require("read")
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("read")
    return _movement_payload(doc, _active_hint_rules())


def _movement_payload(doc, rules):
    doc.check_permission("read")
    source = _data(doc.source_json) or {}
    recognition = _data(doc.recognition_json) or {}
    review = {field: doc.get(field) for field in FIELDS}
    tawal_route = "DEFERRED_TAWAL" in (review.get("route"), recognition.get("route"))
    suggestion = _suggestion_for(source, rules, doc.account_scope_hash) if not tawal_route and not review.get("party") and review.get("review_status") in ("", "PENDING") else None
    if suggestion:
        recognition = {**recognition, "party_suggestion": suggestion}
    # The page shows exactly what the server would accept, so format logic lives in one place.
    return {"name": doc.name, "modified": doc.modified, "id": doc.source_key,
            "account_scope_hash": doc.account_scope_hash or "", "source": source,
            "family": _family(source),
            "hint_options": [{"kind": kind, "value": value} for kind, value in _hint_candidates(source)],
            "recognition": recognition, "erp": _data(doc.erp_hint_json) or {}, "review": review}


def _search_active_parties(doctype, query, approved_names=None):
    _require("read")
    if doctype not in PARTY_DOCTYPES or not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You do not have permission to search this party type."), frappe.PermissionError)
    term = str(query or "").strip()
    if len(term) < 2:
        return []
    label_field = "customer_name" if doctype == "Customer" else "supplier_name"
    filters = {"disabled": 0}
    if approved_names is not None:
        if not approved_names:
            return []
        filters["name"] = ["in", approved_names]
    rows = frappe.get_list(doctype, filters=filters,
                           or_filters={"name": ["like", f"%{term}%"], label_field: ["like", f"%{term}%"]},
                           fields=["name", label_field], order_by=f"{label_field} asc", page_length=30)
    return [{"name": row.name, "label": f"{row.get(label_field) or row.name} · {row.name}"} for row in rows]


@frappe.whitelist()
def search_parties(doctype, query=""):
    _require("read")
    if doctype not in PARTY_DOCTYPES:
        frappe.throw(_("Unsupported party type."))
    approvals = frappe.get_list(PARTY_APPROVAL, filters={"party_type": doctype, "status": "APPROVED"},
                                fields=["party"], page_length=5000)
    return _search_active_parties(doctype, query, [row.party for row in approvals])


@frappe.whitelist()
def search_active_parties_for_approval(doctype, query=""):
    _require("read")
    if not {"Accounts Manager", "System Manager"}.intersection(frappe.get_roles()):
        frappe.throw(_("Only an Accounts Manager may manage router party approvals."), frappe.PermissionError)
    return _search_active_parties(doctype, query)


def _require_approved_party(doctype, name):
    _check_link(doctype, name)
    key = hashlib.sha256((doctype + "|" + name).encode("utf-8")).hexdigest()
    if not frappe.db.exists(PARTY_APPROVAL, key):
        frappe.throw(_("This party is not approved for the bank router."))
    frappe.db.sql("SELECT name FROM `tabSNB Router Party Approval` WHERE name=%s FOR UPDATE", (key,))
    approval = frappe.get_doc(PARTY_APPROVAL, key)
    approval.check_permission("read")
    if approval.status != "APPROVED":
        frappe.throw(_("This party is not approved for the bank router."))


@frappe.whitelist(methods=["POST"])
def set_party_approval(party_type, party, status):
    _require("write")
    if not {"Accounts Manager", "System Manager"}.intersection(frappe.get_roles()):
        frappe.throw(_("Only an Accounts Manager may manage router party approvals."), frappe.PermissionError)
    if party_type not in PARTY_DOCTYPES or status not in ("APPROVED", "REVOKED"):
        frappe.throw(_("Invalid party or approval status."))
    _check_link(party_type, party)
    party_doc = frappe.get_doc(party_type, party)
    if status == "APPROVED" and party_doc.disabled:
        frappe.throw(_("A disabled party cannot be approved."))
    key = hashlib.sha256((party_type + "|" + party).encode("utf-8")).hexdigest()
    frappe.db.sql("SELECT name FROM `tabSNB Router Party Approval` WHERE name=%s FOR UPDATE", (key,))
    if frappe.db.exists(PARTY_APPROVAL, key):
        approval = frappe.get_doc(PARTY_APPROVAL, key)
        approval.check_permission("write")
    else:
        if status != "APPROVED":
            frappe.throw(_("This party has no router approval to revoke."))
        approval = frappe.get_doc({"doctype": PARTY_APPROVAL, "approval_key": key, "party_type": party_type, "party": party})
    approval.status = status
    approval.flags.snb_router_write = True
    approval.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": status, "note": "Bank router party approval"})
    if approval.is_new(): approval.insert()
    else: approval.save()
    if status == "REVOKED":
        filters = {"party_type": party_type, "party": party, "status": "ACTIVE"}
        total = frappe.db.count("SNB Party Hint Rule", filters=filters)
        rules = frappe.get_list("SNB Party Hint Rule", filters=filters, fields=["name"], page_length=5000)
        if total != len(rules):
            frappe.throw(_("Not all active hint rules are accessible; approval revocation stopped."), frappe.PermissionError)
        for row in rules:
            frappe.db.sql("SELECT name FROM `tabSNB Party Hint Rule` WHERE name=%s FOR UPDATE", (row.name,))
            rule = frappe.get_doc("SNB Party Hint Rule", row.name)
            rule.check_permission("write")
            rule.status, rule.sync_status = "REVOKED", "PENDING"
            rule.flags.snb_router_write = True
            rule.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": "REVOKED", "note": "Party approval revoked"})
            rule.save()
    return {"party_type": party_type, "party": party, "status": status}


@frappe.whitelist(methods=["POST"])
def confirm_party_hint(name, modified, hint_kind, hint_value, party_type, party):
    """Save a reusable exact hint rule in ERP. It suggests matches; it never posts or allocates."""
    _require("write")
    movement = frappe.get_doc(DOCTYPE, name)
    movement.check_permission("write")
    if str(movement.modified) != str(modified):
        frappe.throw(_("This movement changed since you opened it. Refresh and review again."))
    source = _data(movement.source_json) or {}
    recognition = _data(movement.recognition_json) or {}
    if "DEFERRED_TAWAL" in (movement.route, recognition.get("route")):
        frappe.throw(_("TAWAL movements must use the existing TAWAL workflow."))
    if re.search(r"\bTAWAL\b|TELECOMMUNICATIONS?\s+TOWERS", " ".join(str(source.get(k) or "") for k in
            ("transaction_description", "detail_description", "extra_description", "remarks")), re.I):
        frappe.throw(_("TAWAL movements must use the existing TAWAL workflow."))
    direction = str(source.get("direction") or movement.direction)
    if not ((direction == "CREDIT" and party_type == "Customer") or
            (direction == "DEBIT" and party_type == "Supplier")):
        frappe.throw(_("Incoming receipts require a Customer; outgoing supplier payments require a Supplier."))
    account_scope_hash = str(movement.account_scope_hash or "")
    if not re.fullmatch(r"[0-9a-f]{64}", account_scope_hash):
        frappe.throw(_("Refresh the SNB sync to establish this movement's account scope before saving a reusable hint."))
    if hint_kind not in HINT_KINDS:
        frappe.throw(_("Choose a supported hint type."))
    hint_value = str(hint_value or "").strip()[:180]
    normalized = _hint_key(hint_kind, hint_value)
    if not normalized or len(normalized) < MIN_HINT_LENGTH[hint_kind]:
        frappe.throw(_("Enter a more specific hint; this type needs at least {0} characters.").format(MIN_HINT_LENGTH[hint_kind]))
    family = _family(source)
    allowed = _hint_candidates(source)
    narrative = _normalize_hint(" ".join(str(source.get(k) or "") for k in
        ("transaction_description", "detail_description", "extra_description", "remarks")))
    parsed_match = (hint_kind, normalized) in [(kind, _hint_key(kind, value)) for kind, value in allowed]
    narrative_match = hint_kind == "NAME" and f" {normalized} " in f" {narrative} "
    if hint_kind != "NAME" and _is_company_number(hint_value):
        frappe.throw(_("That number is one of our own accounts, not the payer's."))
    if not family or not (parsed_match or narrative_match):
        frappe.throw(_("The selected hint does not match a parsed value for this statement format."))
    _require_approved_party(party_type, party)
    party_doc = frappe.get_doc(party_type, party)
    if party_doc.disabled:
        frappe.throw(_("Select an enabled ERP party."))
    party_label = str(party_doc.get("customer_name" if party_type == "Customer" else "supplier_name") or party).strip()
    bank = str(source.get("bank") or "SNB").upper()
    if bank != "SNB":
        frappe.throw(_("Reusable hint rules are currently limited to SNB."))
    account_tail = str(source.get("account_tail") or "")[-4:]
    filters = {"source_bank": bank, "account_tail": account_tail, "account_scope_hash": account_scope_hash, "direction": direction, "narrative_family": family,
               "hint_kind": hint_kind, "normalized_hint": normalized, "status": "ACTIVE"}
    existing = frappe.get_list("SNB Party Hint Rule", filters=filters, fields=["name", "party_type", "party"], page_length=3)
    if existing:
        if len(existing) == 1 and existing[0].party_type == party_type and existing[0].party == party:
            return {"status": "EXISTS", "rule": existing[0].name, "movement": get_movement(name)}
        frappe.throw(_("This exact account and statement hint already has a different active party. Resolve the existing rule before changing it."))
    key = hashlib.sha256("|".join((bank, account_scope_hash, direction, family, hint_kind, normalized)).encode("utf-8")).hexdigest()
    rule_name = frappe.db.exists("SNB Party Hint Rule", key)
    if rule_name:
        rule = frappe.get_doc("SNB Party Hint Rule", rule_name)
        if rule.status == "ACTIVE":
            frappe.throw(_("An active rule already exists for this hint; refresh and review its suggestion."))
        rule.party_type, rule.party, rule.party_label = party_type, party, party_label
        rule.display_hint, rule.status, rule.sync_status = hint_value, "ACTIVE", "PENDING"
        rule.flags.snb_router_write = True
        rule.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": "ACTIVE", "note": "Reactivated and confirmed from movement " + movement.name})
        rule.save()
    else:
        rule = frappe.get_doc({"doctype": "SNB Party Hint Rule", "rule_key": key, "source_bank": bank,
            "account_scope_hash": account_scope_hash, "direction": direction,
            "account_tail": account_tail, "narrative_family": family, "hint_kind": hint_kind,
            "display_hint": hint_value, "normalized_hint": normalized, "party_type": party_type,
            "party": party, "party_label": party_label, "status": "ACTIVE", "sync_status": "PENDING"})
        rule.flags.snb_router_write = True
        rule.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": "ACTIVE", "note": "Confirmed from movement " + movement.name})
        rule.insert()
    return {"status": "CREATED", "rule": rule.name, "movement": get_movement(name),
            "sync_status": "PENDING"}


@frappe.whitelist(methods=["POST"])
def set_hint_rule_status(name, modified, status, note=""):
    """Revoke an exact rule with optimistic locking and an audit entry."""
    _require("write")
    if status not in ("ACTIVE", "REVOKED"):
        frappe.throw(_("Invalid rule status."))
    preliminary = frappe.get_doc("SNB Party Hint Rule", name)
    preliminary.check_permission("write")
    if status == "ACTIVE":
        _require_approved_party(preliminary.party_type, preliminary.party)
    frappe.db.sql("SELECT name FROM `tabSNB Party Hint Rule` WHERE name=%s FOR UPDATE", (name,))
    rule = frappe.get_doc("SNB Party Hint Rule", name)
    rule.check_permission("write")
    if str(rule.modified) != str(modified):
        frappe.throw(_("This hint rule changed. Refresh before editing it."))
    previous = rule.status
    rule.status = status
    rule.sync_status = "PENDING"
    rule.flags.snb_router_write = True
    rule.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": status,
                           "note": str(note or "").strip()[:500] or ("Changed from " + previous)})
    rule.save()
    return {"name": rule.name, "status": rule.status, "sync_status": rule.sync_status,
            "modified": rule.modified}


@frappe.whitelist()
def list_hint_rules(start=0, limit=100):
    _require("read")
    start = max(0, int(start)); limit = min(200, max(1, int(limit)))
    rows = frappe.get_list("SNB Party Hint Rule", fields=["name", "owner", "modified", "rule_key", "source_bank", "account_scope_hash", "account_tail", "direction",
        "narrative_family", "hint_kind", "display_hint", "normalized_hint", "party_type", "party", "party_label", "status", "sync_status"],
        order_by="modified desc", page_length=5000)
    return _visible_party_rules(rows)[start:start + limit]


@frappe.whitelist()
def list_hint_rules_for_sync(start=0, limit=100):
    _require("read")
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the movement integration owner may synchronize rules."), frappe.PermissionError)
    start = max(0, int(start)); limit = min(200, max(1, int(limit)))
    rows = frappe.get_list("SNB Party Hint Rule", filters={"sync_status": ["in", ["PENDING", "ERP_ONLY", "FAILED"]]}, fields=["name", "owner", "modified_by", "modified", "rule_key", "source_bank", "account_scope_hash", "account_tail", "direction", "narrative_family", "hint_kind", "display_hint", "normalized_hint", "party_type", "party", "party_label", "status", "sync_status"], order_by="name asc", start=start, page_length=limit)
    visible = _visible_party_rules(rows)
    if len(visible) != len(rows):
        frappe.throw(_("The integration user cannot read every linked party; rule sync stopped."), frappe.PermissionError)
    active = [row for row in rows if row.status == "ACTIVE"]
    if len(_visible_party_rules(active, enabled_only=True)) != len(active):
        frappe.throw(_("An active rule has a disabled or inaccessible party; rule sync stopped."))
    approvals = frappe.get_list(PARTY_APPROVAL, filters={"status": "APPROVED"}, fields=["party_type", "party"], page_length=5000)
    allowed = {(row.party_type, row.party) for row in approvals}
    if any(row.status == "ACTIVE" and (row.party_type, row.party) not in allowed for row in rows):
        frappe.throw(_("An active rule has no visible party approval; rule sync stopped."))
    return {"rows": visible, "has_more": len(rows) == limit, "next_start": start + len(rows)}


@frappe.whitelist(methods=["POST"])
def acknowledge_hint_rules(names):
    """Mark successfully published rules; retries stay safe if the acknowledgement is lost."""
    return _mark_hint_sync(names, "SYNCED")


@frappe.whitelist(methods=["POST"])
def fail_hint_rules(names):
    """Record a failed or uncertain write only for the unchanged attempted version."""
    return _mark_hint_sync(names, "FAILED")


def _mark_hint_sync(names, target):
    _require("write")
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the movement integration owner may acknowledge Am synchronization."), frappe.PermissionError)
    names = _data(names)
    if not isinstance(names, list) or len(names) > 100:
        frappe.throw(_("Send up to 100 rule names."))
    updated, missing = 0, 0
    stale = []
    for entry in names:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("modified"):
            frappe.throw(_("Each acknowledgement requires the rule name and version."))
        rule_name = str(entry["name"])
        frappe.db.sql("SELECT name FROM `tabSNB Party Hint Rule` WHERE name=%s FOR UPDATE", (rule_name,))
        if not frappe.db.exists("SNB Party Hint Rule", rule_name):
            missing += 1
            continue
        rule = frappe.get_doc("SNB Party Hint Rule", rule_name)
        rule.check_permission("write")
        if str(rule.modified) != str(entry["modified"]):
            stale.append(rule_name)
            continue
        rule.flags.snb_router_write = True
        rule.sync_status = target
        rule.save()
        updated += 1
    return {"updated": updated, "missing": missing, "stale": stale}


@frappe.whitelist(methods=["POST"])
def retry_hint_rule(name, modified):
    _require("write")
    frappe.db.sql("SELECT name FROM `tabSNB Party Hint Rule` WHERE name=%s FOR UPDATE", (name,))
    rule = frappe.get_doc("SNB Party Hint Rule", name)
    rule.check_permission("write")
    if str(rule.modified) != str(modified) or rule.sync_status != "FAILED":
        frappe.throw(_("This rule changed or is no longer failed. Refresh before retrying."))
    rule.sync_status = "PENDING"
    rule.flags.snb_router_write = True
    rule.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": rule.status, "note": "Am synchronization queued for retry"})
    rule.save()
    return {"name": rule.name, "sync_status": rule.sync_status, "modified": rule.modified}


@frappe.whitelist()
def list_reviewed_for_sync(start=0, limit=200):
    """Reviewed Customer/Supplier decisions, so the sync can show them on the Sheet Am movement row.

    Only the review identity (a hash of account and statement key) and the party leave ERP, never bank evidence.
    A party the integration user cannot read stays off the sheet and is counted in `skipped`.
    """
    _require("read")
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the movement integration owner may read decisions for sync."), frappe.PermissionError)
    start = max(0, int(start)); limit = min(200, max(1, int(limit)))
    rows = frappe.get_list(DOCTYPE, filters={"review_status": "REVIEWED", "party_type": ["in", list(PARTY_DOCTYPES)], "party": ["is", "set"]},
        fields=["name", "source_key", "party_type", "party", "review_status", "modified"],
        order_by="name asc", start=start, page_length=limit)
    labels = {}
    for doctype in PARTY_DOCTYPES:
        names = list({row.party for row in rows if row.party_type == doctype})
        if names and frappe.has_permission(doctype, "read"):
            field = "customer_name" if doctype == "Customer" else "supplier_name"
            labels[doctype] = {row.name: row.get(field) or row.name for row in frappe.get_list(
                doctype, filters={"name": ["in", names]}, fields=["name", field], page_length=5000)}
    result = [{"source_key": row.source_key, "party_type": row.party_type,
               "party": row.party, "party_label": labels[row.party_type][row.party], "review_status": row.review_status}
              for row in rows if row.party in labels.get(row.party_type, {})]
    return {"rows": result, "has_more": len(rows) == limit, "next_start": start + len(rows), "skipped": len(rows) - len(result)}


FAMILIES = {"IPS_LOCAL", "INTERNAL_SNB", "LARGE_LOCAL"}


def _party_approved(doctype, name):
    key = hashlib.sha256((doctype + "|" + name).encode("utf-8")).hexdigest()
    return bool(frappe.db.exists(PARTY_APPROVAL, key)) and frappe.db.get_value(PARTY_APPROVAL, key, "status") == "APPROVED"


def _sheet_rule(entry):
    """Validate one payer row typed in Sheet Am. Returns (rule fields, rejection reason)."""
    if not isinstance(entry, dict):
        return None, "invalid_row"
    party_type = str(entry.get("party_type") or "").strip().title()
    party = str(entry.get("erp_record_id") or "").strip()
    family = str(entry.get("transfer_type") or "").strip().upper()
    kind = str(entry.get("hint_kind") or "").strip().upper()
    status = str(entry.get("status") or "").strip().upper()
    scope = str(entry.get("account_scope_hash") or "").strip().lower()
    text = str(entry.get("hint_text") or "").strip()[:180]
    if party_type not in PARTY_DOCTYPES or not party:
        return None, "invalid_party"
    if family not in FAMILIES or kind not in HINT_KINDS or status not in ("ACTIVE", "REVOKED"):
        return None, "invalid_value"
    if not re.fullmatch(r"[0-9a-f]{64}", scope):
        return None, "unknown_account"
    normalized = _hint_key(kind, text)
    if len(normalized) < MIN_HINT_LENGTH[kind]:
        return None, "hint_too_short"
    if kind != "NAME" and _is_company_number(text):
        return None, "own_account_number"
    direction = "CREDIT" if party_type == "Customer" else "DEBIT"
    key = hashlib.sha256("|".join(("SNB", scope, direction, family, kind, normalized)).encode("utf-8")).hexdigest()
    return {"rule_key": key, "account_scope_hash": scope, "account_tail": str(entry.get("account_tail") or "")[-4:].zfill(4),
            "direction": direction, "narrative_family": family, "hint_kind": kind, "display_hint": text,
            "normalized_hint": normalized, "party_type": party_type, "party": party, "status": status,
            "reviewer": str(entry.get("updated_by") or "").strip()[:140]}, ""


@frappe.whitelist(methods=["POST"])
def import_sheet_hint_rules(rows):
    """Apply payer rows edited by hand in Sheet Am; every row is validated here, none is trusted.

    Rejected rows are reported, never partly applied, and they never stop the other rows.
    A row that disagrees with an ERP rule updates it with an audit entry (last write wins).
    """
    _require("write")
    from sig_warehouse.sig_operations.app_connections import TODOIST_OWNER
    if frappe.session.user != TODOIST_OWNER and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the movement integration owner may import Sheet Am rules."), frappe.PermissionError)
    rows = _data(rows)
    if not isinstance(rows, list) or len(rows) > 500:
        frappe.throw(_("Send up to 500 rows."))
    parsed = [(entry.get("row") if isinstance(entry, dict) else None, *_sheet_rule(entry)) for entry in rows]
    owners = {}
    for _row, rule, reason in parsed:
        if rule and rule["status"] == "ACTIVE":
            owners.setdefault(rule["rule_key"], set()).add((rule["party_type"], rule["party"]))
    results = []
    for row, rule, reason in parsed:
        if not rule:
            results.append({"row": row, "status": "REJECTED", "reason": reason})
            continue
        if len(owners.get(rule["rule_key"], ())) > 1 and rule["status"] == "ACTIVE":
            results.append({"row": row, "status": "REJECTED", "reason": "same_hint_two_parties"})
            continue
        existing = frappe.db.exists("SNB Party Hint Rule", rule["rule_key"])
        if rule["status"] == "REVOKED" and not existing:
            results.append({"row": row, "status": "IGNORED", "reason": "revoked_unknown_rule"})
            continue
        try:
            _check_link(rule["party_type"], rule["party"])
            party_doc = frappe.get_doc(rule["party_type"], rule["party"])
        except Exception:
            results.append({"row": row, "status": "REJECTED", "reason": "party_not_readable"})
            continue
        if rule["status"] == "ACTIVE" and (party_doc.disabled or not _party_approved(rule["party_type"], rule["party"])):
            results.append({"row": row, "status": "REJECTED", "reason": "party_disabled" if party_doc.disabled else "party_not_approved"})
            continue
        label = str(party_doc.get("customer_name" if rule["party_type"] == "Customer" else "supplier_name") or rule["party"]).strip()
        note = "Edited in Sheet Am" + (" by " + rule["reviewer"] if rule["reviewer"] else "")
        if existing:
            frappe.db.sql("SELECT name FROM `tabSNB Party Hint Rule` WHERE name=%s FOR UPDATE", (rule["rule_key"],))
            doc = frappe.get_doc("SNB Party Hint Rule", rule["rule_key"])
            doc.check_permission("write")
            if (doc.party_type, doc.party, doc.status) == (rule["party_type"], rule["party"], rule["status"]):
                if doc.sync_status != "SYNCED":
                    doc.sync_status = "SYNCED"
                    doc.flags.snb_router_write = True
                    doc.save()
                results.append({"row": row, "status": "UNCHANGED", "name": doc.name, "party_label": doc.party_label})
                continue
            doc.party_type, doc.party, doc.party_label = rule["party_type"], rule["party"], label
            doc.display_hint, doc.status, doc.sync_status = rule["display_hint"], rule["status"], "SYNCED"
            doc.flags.snb_router_write = True
            doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": rule["status"], "note": note})
            doc.save()
            results.append({"row": row, "status": "UPDATED", "name": doc.name, "party_label": label})
            continue
        doc = frappe.get_doc({"doctype": "SNB Party Hint Rule", "rule_key": rule["rule_key"], "source_bank": "SNB",
            "account_scope_hash": rule["account_scope_hash"], "account_tail": rule["account_tail"], "direction": rule["direction"],
            "narrative_family": rule["narrative_family"], "hint_kind": rule["hint_kind"], "display_hint": rule["display_hint"],
            "normalized_hint": rule["normalized_hint"], "party_type": rule["party_type"], "party": rule["party"],
            "party_label": label, "status": "ACTIVE", "sync_status": "SYNCED"})
        doc.flags.snb_router_write = True
        doc.append("audit", {"reviewer": frappe.session.user, "reviewed_at": now_datetime(), "status": "ACTIVE", "note": note})
        doc.insert()
        results.append({"row": row, "status": "CREATED", "name": doc.name, "party_label": label})
    return results


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


def _document_matches_movement(doc, movement, source, account_number):
    """Validate the bank-side GL and amount after document and Account read checks."""
    direction = source.get("direction") or movement.direction
    expected = abs(flt(movement.amount))
    currency = str(source.get("currency") or movement.currency or "")
    if not expected or not currency:
        return False
    if doc.doctype == "Payment Entry":
        is_pay = direction == "DEBIT" and doc.get("payment_type") == "Pay"
        is_receive = direction == "CREDIT" and doc.get("payment_type") == "Receive"
        if not (is_pay or is_receive):
            return False
        account = doc.get("paid_from" if is_pay else "paid_to")
        amount = flt(doc.get("paid_amount" if is_pay else "received_amount"))
        account_currency = doc.get("paid_from_account_currency" if is_pay else "paid_to_account_currency")
        reference = str(source.get("reference") or "").strip()
        if reference and str(doc.get("reference_no") or "").strip() != reference:
            return False
        lines = [(account, amount, 0, account_currency)]
    else:
        lines = []
        for line in doc.get("accounts") or []:
            correct = flt(line.get("credit_in_account_currency" if direction == "DEBIT" else "debit_in_account_currency"))
            opposite = flt(line.get("debit_in_account_currency" if direction == "DEBIT" else "credit_in_account_currency"))
            lines.append((line.get("account"), correct, opposite, line.get("account_currency")))
    bank_lines = []
    for account, amount, opposite, account_currency in lines:
        if not account:
            return False
        account_doc = frappe.get_doc("Account", account)
        account_doc.check_permission("read")
        if str(account_doc.get("account_number") or "") == account_number and account_doc.get("company") == doc.get("company"):
            bank_lines.append((amount, opposite, account_currency))
    return (len(bank_lines) == 1 and str(bank_lines[0][2] or "") == currency and
            not bank_lines[0][1] and abs(bank_lines[0][0] - expected) <= 0.005)


@frappe.whitelist(methods=["POST"])
def readback_movements(names):
    """Read marked PE/JE status only when marker, document, source account and amount agree."""
    _require("read")
    names = _data(names)
    if not isinstance(names, list) or len(names) > 100:
        frappe.throw(_("Send up to 100 movement names."))
    available = all(frappe.has_permission(dt, "read") for dt in ("Payment Entry", "Journal Entry", "Account"))
    markers = (("Payment Entry", "custom_snb_idempotency_key"), ("Journal Entry", "custom_pc_statement_key"))
    results = []
    for name in names:
        movement = frappe.get_doc(DOCTYPE, str(name))
        movement.check_permission("read")
        result = {"name": movement.name, "status": "UNKNOWN", "documents": []}
        source = _data(movement.source_json) or {}
        hint = str((_data(movement.erp_hint_json) or {}).get("linked_doc") or "").strip()
        statement_key = str(source.get("statement_key") or "").strip()
        bank_gl = SNB_BANK_GL_BY_SCOPE.get(str(movement.account_scope_hash or ""))
        if not available:
            result["status"] = "UNAVAILABLE"
        elif str(source.get("bank") or "SNB").upper() == "SNB" and hint and statement_key and bank_gl:
            matches = []
            inaccessible = False
            for doctype, marker in markers:
                total = frappe.db.count(doctype, filters={marker: statement_key})
                if total > 10:
                    matches.extend([None, None])
                    break
                visible = frappe.get_list(doctype, filters={marker: statement_key}, fields=["name"], page_length=10)
                if len(visible) != total:
                    inaccessible = True
                    break
                matches.extend((doctype, row.name) for row in visible)
            if inaccessible:
                result["status"] = "UNAVAILABLE"
            elif matches and all(match is not None for match in matches):
                hint_name = hint.split(":", 1)[-1].strip().split("/")[-1].strip()
                if any(docname == hint_name for _, docname in matches):
                    all_verified = True
                    for doctype, docname in matches:
                        doc = frappe.get_doc(doctype, docname)
                        try:
                            doc.check_permission("read")
                            verified = _document_matches_movement(doc, movement, source, bank_gl)
                        except frappe.PermissionError:
                            result["status"] = "UNAVAILABLE"
                            all_verified = False
                            break
                        if not verified:
                            all_verified = False
                            continue
                        status = {0: "DRAFT", 1: "POSTED", 2: "CANCELLED"}.get(int(doc.docstatus), "UNKNOWN")
                        result["documents"].append({"doctype": doctype, "name": docname, "status": status})
                    if all_verified and len(result["documents"]) == 1:
                        result["status"] = result["documents"][0]["status"]
                    elif all_verified and len(result["documents"]) > 1:
                        result["status"] = "AMBIGUOUS"
        results.append(result)
    return results


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
        if clean["party_type"] in PARTY_DOCTYPES and (clean["party_type"] != doc.party_type or clean["party"] != doc.party):
            _require_approved_party(clean["party_type"], clean["party"])
        else:
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
