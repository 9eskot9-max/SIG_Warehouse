"""One setup page, transactional publication, ACN read-anchor export. No stock writes."""
import json

import frappe
from frappe.utils import now_datetime

from sig_warehouse.sig_operations.excel_setup_contract import (
    SCHEMA_VERSION, FIELDS, KINDS, TEAM_ARCHETYPES, OPS_ROLES, canonical, digest, merge_import,
    setup_warnings, validate, family_key,
)
from sig_warehouse.sig_warehouse.project_family import resolve_project_family

EDIT_ROLES = {"System Manager", "Operations Manager", "Operations User", "Projects Manager", "SIG Excel Setup Editor"}
READ_ROLES = EDIT_ROLES | {"SIG Excel Setup Reader", "SIG Stock Viewer"}
SETUP = "SIG Excel Setup"
REVISION = "SIG Excel Setup Revision"


def _require(editor=False):
    if frappe.session.user == "Guest" or not (set(frappe.get_roles()) & (EDIT_ROLES if editor else READ_ROLES)):
        frappe.throw("Not permitted to edit Excel Setup" if editor else "Not permitted to fetch Excel Setup", frappe.PermissionError)


def _parse(value):
    if isinstance(value, str):
        if len(value) > 5_000_000:
            frappe.throw("Setup package is too large")
        try:
            return json.loads(value.lstrip("\ufeff"))
        except ValueError:
            frappe.throw("Invalid setup JSON")
    return value


def _validated(datasets):
    try:
        return validate(datasets)
    except ValueError as exc:
        frappe.throw(str(exc))


def _merge(current, package):
    try:
        return merge_import(current, package)
    except ValueError as exc:
        frappe.throw(str(exc))


def _state(lock=False):
    if lock:
        # The migration creates the singleton's revision row. All writers take
        # this same database row lock; stale browser writes are rejected below.
        frappe.db.sql("SELECT value FROM tabSingles WHERE doctype=%s AND field='revision' FOR UPDATE", (SETUP,))
    doc = frappe.get_single(SETUP)
    stored = json.loads(doc.configuration_json or "{}")
    # Lists and columns removed from the contract (see excel_setup_contract) are ignored, not published again.
    return doc, {name: [{k: row.get(k, "") for k in FIELDS[name] if k in row} for row in stored.get(name, [])] for name in FIELDS}


def _linked_masters(datasets, current=None):
    # Validate identifiers without disclosing unrelated master fields or requiring
    # Operations editors to acquire broad master write/read permissions.
    if any(row["enabled"] for row in datasets.get("pc_family_defaults", [])):
        from sig_warehouse.sig_warehouse.pc_review_routing import load_matrix
        groups = set(load_matrix()["review_groups"])
        if any(row["enabled"] and row["review_group"] not in groups for row in datasets["pc_family_defaults"]):
            frappe.throw("PC family defaults must refer to an existing review group.")
    for row in datasets["projects"]:
        if row["enabled"] and not frappe.db.exists("Project", row["project"]):
            frappe.throw(f"Project {row['project']} does not exist")
        if row["enabled"]:
            meta = frappe.get_meta("Project")
            fields = [field for field in ("custom_po_number", "custom_agreement_no", "custom_tawal_ba", "name") if meta.has_field(field) or field == "name"]
            project = frappe.db.get_value("Project", row["project"], fields, as_dict=True)
            if row["po"] and row["po"] not in {str(v or "").strip() for v in project.values()}:
                frappe.throw(f"PO does not match canonical Project {row['project']}")
            row["project"] = project["name"]
            family_fields = [field for field in ("custom_project_family", "custom_family") if meta.has_field(field)]
            if resolve_project_family(frappe.db.get_value("Project", row["project"], family_fields, as_dict=True) if family_fields else {})["conflict"]:
                frappe.throw("Project family fields disagree for {}. Reconcile custom_project_family and custom_family before publishing.".format(row["project"]))
            if meta.has_field("custom_is_canonical_agreement") and not frappe.db.get_value("Project", row["project"], "custom_is_canonical_agreement"):
                frappe.throw(f"Select the canonical Project for PO {row['po']}")
    if any(row["enabled"] for row in datasets.get("family_tawal_defaults", [])):
        doctype = "SIG TAWAL Contact"
        if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field("active"):
            frappe.throw("Family TAWAL defaults require the active SIG TAWAL Contact directory.")
        for row in datasets["family_tawal_defaults"]:
            if row["enabled"] and not frappe.db.get_value(doctype, {"name": row["tawal_contact"], "active": 1}, "name"):
                frappe.throw("Select an existing active TAWAL contact for family default " + row["id"])
    for dataset in ("team_memberships", "ops_team_members"):
        for row in datasets.get(dataset, []):
            if row["enabled"]:
                employee = frappe.db.get_value("Employee", row["employee"], ["name", "status"], as_dict=True)
                if not employee or employee.status != "Active":
                    frappe.throw("Active ERP Employee required for " + dataset + ": " + row["employee"])
    for row in datasets.get("ops_team_members", []):
        if row["enabled"] and row["project"]:
            meta = frappe.get_meta("Project")
            fields = [field for field in ("custom_project_family", "custom_family") if meta.has_field(field)]
            if not frappe.db.exists("Project", row["project"]):
                frappe.throw("Operations exception needs an existing ERP Project.")
            resolved = resolve_project_family(frappe.db.get_value("Project", row["project"], fields, as_dict=True) if fields else {})
            if resolved["conflict"] or resolved["family"] != family_key(row["family"]):
                frappe.throw("Operations exception Project must match its family: " + row["project"])
    for row in datasets["material_upl_links"]:
        if row["enabled"] and not frappe.db.exists("Item", row["item_code"]):
            frappe.throw(f"ERP Item {row['item_code']} does not exist")
        if row["enabled"] and row["source_uom"]:
            unit = frappe.db.get_value("Item", row["item_code"], "stock_uom")
            if str(unit).casefold() != row["source_uom"].casefold():
                frappe.throw(f"Source UOM does not match Item {row['item_code']}")
        if row["enabled"] and row["target_uom"] and not frappe.db.exists("UOM", row["target_uom"]):
            frappe.throw(f"Mapping UOM {row['target_uom']} does not exist in ERP")


def _publish(datasets, base_revision, batch_id="", batch_hash=""):
    doc, current = _state(lock=True)
    if batch_id:
        old = frappe.db.get_value(REVISION, {"import_batch_id": batch_id}, ["revision", "import_batch_hash"], as_dict=True)
        if old:
            if old.import_batch_hash != batch_hash:
                frappe.throw("Import batch ID already used with different content")
            return {"result": "unchanged", "revision": old.revision}
    if int(base_revision) != int(doc.revision or 0):
        frappe.throw("Setup changed in another session. Reload and review again.")
    datasets = _validated(datasets)
    _linked_masters(datasets, current)
    datasets = _validated(datasets)
    encoded, content_hash = canonical(datasets), digest(datasets)
    if doc.published_hash == content_hash:
        return {"result": "unchanged", "revision": int(doc.revision)}
    revision = int(doc.revision or 0) + 1
    stamp = now_datetime()
    # These two new DocTypes expose no ordinary CRUD writer for publication.
    # The service is the sole writer, after explicit role/validation checks.
    previous = frappe.flags.excel_setup_service
    frappe.flags.excel_setup_service = True
    try:
        frappe.get_doc({"doctype": REVISION, "revision": revision,
                        "configuration_json": encoded, "content_hash": content_hash,
                        "published_at": stamp, "published_by": frappe.session.user,
                        "import_batch_id": batch_id or None, "import_batch_hash": batch_hash}).insert(ignore_permissions=True)
        doc.update({"configuration_json": encoded, "revision": revision, "published_hash": content_hash,
                    "published_at": stamp, "published_by": frappe.session.user})
        doc.save(ignore_permissions=True)
    finally:
        frappe.flags.excel_setup_service = previous
    return {"result": "published", "revision": revision, "hash": content_hash}


def _crew_warnings(datasets, day):
    """Crew leaders the Planner or the no-visit message would silently skip."""
    leaders = {r["employee"] for r in datasets["team_memberships"]
               if r["enabled"] and r["role"] == "leader" and r["effective_from"] <= day and (not r["effective_to"] or day <= r["effective_to"])}
    notes = []
    for person in frappe.get_all("Employee", filters={"name": ["in", sorted(leaders)]},
                                 fields=["name", "employee_name", "status", "cell_number"], limit_page_length=0):
        if person.status != "Active":
            notes.append(f"Crew leader {person.employee_name or person.name} is not an Active Employee: Planner skips the crew.")
        elif not person.cell_number:
            notes.append(f"Crew leader {person.employee_name or person.name} has no phone number: the no-visit message skips them.")
    return notes


@frappe.whitelist()
def get_page_state():
    _require(editor=True)
    doc, datasets = _state()
    day = str(frappe.utils.nowdate())[:10]
    references = _reference_choices()
    references["operational_teams"] = [
        {"name": row["id"], "team_name": row["team_name"], "family": row["family"],
         "archetype": row["archetype"]}
        for row in datasets["operational_teams"] if row["enabled"]
    ]
    return {"schema_version": SCHEMA_VERSION,
            "revision": int(doc.revision or 0), "datasets": datasets, "fields": FIELDS,
            "published_at": doc.published_at, "published_by": doc.published_by,
            "options": {"builder_defaults.kind": sorted(KINDS), "material_upl_links.treatment": ["Direct 1:1", "Excluded", "Manual"],
                        "family_tawal_defaults.family": ["Capex", "Incident", "5G / Colocation"],
                        "pc_family_defaults.family": ["Capex", "Incident", "5G / Colocation"],
                        "pc_family_defaults.review_group": ["capex", "incident", "colocation", "warehouse", "general", "unassigned"],
                        "operational_teams.family": ["Capex", "Incident", "5G / Colocation"],
                        "operational_teams.archetype": list(TEAM_ARCHETYPES),
                        "team_memberships.role": ["leader", "member"],
                        "ops_team_members.family": ["Capex", "Incident", "5G / Colocation"],
                        "ops_team_members.role": list(OPS_ROLES)},
            "references": references,
            "warnings": setup_warnings(datasets, day) + _crew_warnings(datasets, day),
            "counts": {key: len(value) for key, value in datasets.items()}}


@frappe.whitelist()
def get_history():
    """Who published each revision and which lists changed, for the 25 newest (the log replaces role restrictions)."""
    _require(editor=True)
    rows = frappe.get_all(REVISION, fields=["revision", "published_at", "published_by", "content_hash", "configuration_json"],
                          order_by="revision desc", limit_page_length=26)
    for index, row in enumerate(rows):
        now = json.loads(row.pop("configuration_json") or "{}")
        before = json.loads(rows[index + 1]["configuration_json"] or "{}") if index + 1 < len(rows) else None
        row["changed"] = ["%s (%d)" % (name, len(now.get(name, []))) for name in FIELDS
                          if before is not None and now.get(name, []) != before.get(name, [])]
    return rows[:25]


def _reference_choices():
    """Minimal editor-only reference projection, without broad master grants."""
    meta = frappe.get_meta("Project")
    fields = ["name", "project_name"] + [key for key in ("custom_agreement_no", "custom_tawal_ba", "custom_po_number", "custom_project_family", "custom_family") if meta.has_field(key)]
    filters = {"custom_is_canonical_agreement": 1} if meta.has_field("custom_is_canonical_agreement") else {}
    projects = frappe.get_all("Project", filters=filters, fields=fields, order_by="project_name asc", limit_page_length=10000)
    contacts = frappe.get_all("SIG TAWAL Contact", fields=["name", "full_name", "mobile", "email"], limit_page_length=10000) if frappe.db.exists("DocType", "SIG TAWAL Contact") else []
    active_contacts = frappe.get_all("SIG TAWAL Contact", filters={"active": 1},
                                     fields=["name", "full_name", "mobile", "email"],
                                     limit_page_length=10000) if frappe.db.exists("DocType", "SIG TAWAL Contact") and frappe.get_meta("SIG TAWAL Contact").has_field("active") else []
    items = frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 1}, fields=["name", "item_name", "stock_uom"], limit_page_length=10000)
    uoms = frappe.get_all("UOM", fields=["name"], order_by="name asc", limit_page_length=10000)
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"],
                               order_by="employee_name asc", limit_page_length=10000)
    return {"projects": projects, "contacts": contacts, "active_contacts": active_contacts,
            "items": items, "uoms": uoms, "employees": employees}


@frappe.whitelist(methods=["POST"])
def save_and_publish(datasets, base_revision):
    _require(editor=True)
    return _publish(_parse(datasets), base_revision)


@frappe.whitelist(methods=["POST"])
def preview_import(package, base_revision):
    _require(editor=True)
    doc, current = _state()
    if int(base_revision) != int(doc.revision or 0):
        frappe.throw("Reload setup before importing")
    merged, counts = _merge(current, _parse(package))
    _linked_masters(merged, current)
    merged = _validated(merged)
    return {"datasets": merged, "counts": counts, "base_revision": int(base_revision)}


@frappe.whitelist(methods=["POST"])
def apply_import(package, base_revision):
    _require(editor=True)
    package = _parse(package)
    if not isinstance(package, dict) or not isinstance(package.get("batch_id"), str) or not 1 <= len(package["batch_id"]) <= 120:
        frappe.throw("Import requires batch_id (1–120 characters)")
    # Lock before reading the merge base, not just before persisting it.
    _, current = _state(lock=True)
    old = frappe.db.get_value(REVISION, {"import_batch_id": package.get("batch_id")}, ["revision", "import_batch_hash"], as_dict=True)
    if old:
        if old.import_batch_hash != digest(package):
            frappe.throw("Import batch ID already used with different content")
        return {"result": "unchanged", "revision": old.revision}
    merged, _ = _merge(current, package)
    return _publish(merged, base_revision, package["batch_id"], digest(package))


def prepare_roles():
    """Before model sync: only these two new roles, no existing matrix changes."""
    for role in ("SIG Excel Setup Editor", "SIG Excel Setup Reader"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": int(role.endswith("Editor"))}).insert(ignore_permissions=True)
