"""One setup page, transactional publication, ACN read-anchor export. No stock writes."""
import base64
import hashlib
import json

import frappe
from frappe.utils import now_datetime

from sig_warehouse.sig_operations.excel_setup_contract import (
    ADAPTER_VERSION, CONTRACT, SCHEMA_VERSION, FIELDS, KINDS, TEAM_ARCHETYPES, canonical, digest, merge_import,
    project_bundle, validate, is_legacy, upgrade_legacy, bundle_complete,
)
from sig_warehouse.sig_warehouse.project_family import resolve_project_family
from sig_warehouse.sig_warehouse.people_model_gate import PEOPLE_MODEL_ACTIVE

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
    return doc, json.loads(doc.configuration_json or canonical({name: [] for name in FIELDS}))


def _linked_masters(datasets, current=None):
    # Validate identifiers without disclosing unrelated master fields or requiring
    # Operations editors to acquire broad master write/read permissions.
    if any(row["enabled"] for row in datasets.get("pc_family_defaults", [])):
        from sig_warehouse.sig_warehouse.pc_review_routing import load_matrix
        groups = set(load_matrix()["review_groups"])
        if any(row["enabled"] and row["review_group"] not in groups for row in datasets["pc_family_defaults"]):
            frappe.throw("PC family defaults must refer to an existing review group.")
    current_projects = {str(row.get("id")): row for row in (current or {}).get("projects", [])}
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
            project_family = frappe.db.get_value("Project", row["project"], family_fields, as_dict=True) if family_fields else {}
            resolved_family = resolve_project_family(project_family)
            if resolved_family["conflict"]:
                frappe.throw("Project family fields disagree for {}. Reconcile custom_project_family and custom_family before publishing.".format(row["project"]))
            # Family is sourced from the native Project when a project link is
            # first created or changed. Do not rewrite every cached family on
            # unrelated setup saves (for example, a People-only edit).
            previous = current_projects.get(str(row.get("id")))
            if not previous or previous.get("project") != row["project"]:
                row["family"] = resolved_family["family"]
            if meta.has_field("custom_is_canonical_agreement") and not frappe.db.get_value("Project", row["project"], "custom_is_canonical_agreement"):
                frappe.throw(f"Select the canonical Project for PO {row['po']}")
    for row in datasets.get("project_builder_links", []):
        if row["enabled"]:
            if row["stream"] and (
                not frappe.db.exists("DocType", "SIG Project Stream")
                or frappe.db.get_value("SIG Project Stream", row["stream"], "project") != row["project"]
            ):
                frappe.throw("Select an existing stream belonging to this canonical Project")
            row["stream_alias"] = str(frappe.db.get_value("SIG Project Stream", row["stream"], "alias") or "") if row["stream"] else ""
    for row in datasets.get("builder_contacts", []):
        if row["enabled"]:
            _resolve_contact(row)
    if any(row["enabled"] for row in datasets.get("family_tawal_defaults", [])):
        doctype = "SIG TAWAL Contact"
        if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field("active"):
            frappe.throw("Family TAWAL defaults require the active SIG TAWAL Contact directory.")
        for row in datasets["family_tawal_defaults"]:
            if row["enabled"] and not frappe.db.get_value(doctype, {"name": row["tawal_contact"], "active": 1}, "name"):
                frappe.throw("Select an existing active TAWAL contact for family default " + row["id"])
    for row in datasets.get("teams", []):
        # A team is its leader: the team name and phone come from the Employee, never typed.
        person = frappe.db.get_value("Employee", row["leader"], ["employee_name", "cell_number"], as_dict=True)
        if not person:
            frappe.throw(f"Team leader {row['leader']} is not an Employee")
        row["team"] = person.employee_name or row["leader"]
        row["phone"] = str(person.cell_number or "")
    configured_teams = {row["id"]: row for row in datasets.get("operational_teams", []) if row["enabled"]}
    for row in datasets.get("team_memberships", []):
        if not row["enabled"]:
            continue
        if row["team"] not in configured_teams:
            frappe.throw("Team membership references a missing or disabled team: " + row["team"])
        employee = frappe.db.get_value("Employee", row["employee"], ["name", "status"], as_dict=True)
        if not employee or employee.status != "Active":
            frappe.throw("Active ERP Employee required for membership: " + row["employee"])
    if datasets.get("team_projects"):
        meta = frappe.get_meta("Project")
        family_fields = [field for field in ("custom_project_family", "custom_family") if meta.has_field(field)]
        for row in datasets["team_projects"]:
            if not row["enabled"]:
                continue
            team = configured_teams.get(row["team"])
            if not team or not frappe.db.exists("Project", row["project"]):
                frappe.throw("Team Project link needs an enabled team and an existing ERP Project.")
            project = frappe.db.get_value("Project", row["project"], family_fields, as_dict=True) if family_fields else {}
            resolved = resolve_project_family(project)
            team_family = "Colocation" if team["family"] == "5G / Colocation" else team["family"]
            if resolved["conflict"] or not resolved["family"] or resolved["family"] != team_family:
                frappe.throw("Team Project family must match a resolved Project family before publishing: " + row["project"])
    for row in datasets.get("ops_team_members", []):
        if row["enabled"]:
            employee = frappe.db.get_value("Employee", row["employee"], ["name", "status"], as_dict=True)
            if not employee or employee.status != "Active":
                frappe.throw("Active ERP Employee required for Operations team: " + row["employee"])
            if row["project"]:
                meta = frappe.get_meta("Project")
                if not frappe.db.exists("Project", row["project"]):
                    frappe.throw("Operations exception needs an existing ERP Project.")
                fields = [field for field in ("custom_project_family", "custom_family") if meta.has_field(field)]
                project = frappe.db.get_value("Project", row["project"], fields, as_dict=True) if fields else {}
                resolved = resolve_project_family(project)
                family = "Colocation" if row["family"] == "5G / Colocation" else row["family"]
                if resolved["conflict"] or resolved["family"] != family:
                    frappe.throw("Operations exception Project must match its family: " + row["project"])
    for row in datasets.get("project_responsibilities", []):
        if row["enabled"]:
            employee = frappe.db.get_value("Employee", row["employee"], ["name", "status"], as_dict=True)
            if not employee or employee.status != "Active":
                frappe.throw("Active ERP Employee required for Project responsibility: " + row["employee"])
            if not frappe.db.exists("Project", row["project"]):
                frappe.throw("Project responsibility references a missing ERP Project: " + row["project"])
    if any(row["enabled"] and row["mode"] == "exception" for row in datasets.get("project_tawal_rules", [])):
        if not frappe.db.exists("DocType", "SIG TAWAL Contact") or not frappe.get_meta("SIG TAWAL Contact").has_field("active"):
            frappe.throw("PO TAWAL exceptions require the active SIG TAWAL Contact directory.")
    for row in datasets.get("project_tawal_rules", []):
        if row["enabled"]:
            if not frappe.db.exists("Project", row["project"]):
                frappe.throw("PO TAWAL rule references a missing ERP Project: " + row["project"])
            if row["mode"] == "exception" and not frappe.db.get_value(
                    "SIG TAWAL Contact", {"name": row["tawal_contact"], "active": 1}, "name"):
                frappe.throw("PO TAWAL exception must reference an active directory contact.")
    for row in datasets["material_upl_links"]:
        if row["enabled"] and not frappe.db.exists("Item", row["item_code"]):
            frappe.throw(f"ERP Item {row['item_code']} does not exist")
        if row["enabled"] and row["source_uom"]:
            unit = frappe.db.get_value("Item", row["item_code"], "stock_uom")
            if str(unit).casefold() != row["source_uom"].casefold():
                frappe.throw(f"Source UOM does not match Item {row['item_code']}")
        if row["enabled"] and row["target_uom"] and not frappe.db.exists("UOM", row["target_uom"]):
            frappe.throw(f"Mapping UOM {row['target_uom']} does not exist in ERP")


def _resolve_contact(row):
    """Reusable Builder contacts reference the existing directory, not a PO row.

    This never creates Project PM assignments or changes Project contact defaults.
    Those remain the native Project setup's responsibility.
    """
    if not any(row[key] for key in ("tawal_contact", "contact_name", "contact_phone", "contact_email")):
        return
    doctype = "SIG TAWAL Contact"
    if not frappe.db.exists("DocType", doctype):
        frappe.throw("The existing TAWAL contact directory is required before importing contact setup")
    filters = {"name": row["tawal_contact"]} if row["tawal_contact"] else (
        {"email": row["contact_email"]} if row["contact_email"] else {"full_name": row["contact_name"], "mobile": row["contact_phone"]})
    contacts = frappe.get_all(doctype, filters=filters, fields=["name", "full_name", "mobile", "email"], limit_page_length=2)
    if not contacts and not row["tawal_contact"] and row.get("origin") == "RV80 Builder":
        # Keep genuine legacy profile data visible for directory reconciliation.
        # Pending rows cannot produce a complete RV80 import bundle.
        return
    if len(contacts) != 1:
        frappe.throw("Select one exact contact from the existing TAWAL directory; ambiguous/new directory entries need its existing setup workflow")
    contact = contacts[0]
    row.update(tawal_contact=contact.name, contact_name=contact.full_name or "", contact_phone=contact.mobile or "", contact_email=contact.email or "")


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
    if datasets.get("project_responsibilities", []) != current.get("project_responsibilities", []):
        frappe.throw("Legacy Project responsibility rows are read-only. Use Operations Project team members for cycle visibility.")
    governed = ("family_tawal_defaults", "project_tawal_rules", "operational_teams",
                "team_memberships", "team_projects", "project_responsibilities", "ops_team_members", "pc_family_defaults")
    if any(datasets[key] != current.get(key, []) for key in governed) and "System Manager" not in frappe.get_roles():
        frappe.throw("Only System Manager can change the new family, contact and People configuration while its permissions are under review.", frappe.PermissionError)
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


@frappe.whitelist()
def get_page_state():
    _require(editor=True)
    doc, datasets = _state()
    migration_pending = is_legacy(datasets)
    if migration_pending:
        datasets = upgrade_legacy(datasets)
    for name in FIELDS:     # lists added after the last publication start empty
        datasets.setdefault(name, [])
    references = _reference_choices()
    references["operational_teams"] = [
        {"name": row["id"], "team_name": row["team_name"], "family": row["family"],
         "archetype": row["archetype"]}
        for row in datasets["operational_teams"] if row["enabled"]
    ]
    return {"schema_version": SCHEMA_VERSION, "migration_pending": migration_pending,
            "people_model_active": bool(PEOPLE_MODEL_ACTIVE),
            "revision": int(doc.revision or 0), "datasets": datasets, "fields": FIELDS,
            "published_at": doc.published_at, "published_by": doc.published_by,
            "options": {"builder_defaults.kind": sorted(KINDS), "material_upl_links.treatment": ["Direct 1:1", "Excluded", "Manual"],
                        "teams.archetype": list(TEAM_ARCHETYPES),
                        "family_tawal_defaults.family": ["Capex", "Incident", "5G / Colocation"],
                        "pc_family_defaults.family": ["Capex", "Incident", "5G / Colocation"],
                        "pc_family_defaults.review_group": ["capex", "incident", "colocation", "warehouse", "general", "unassigned"],
                        "operational_teams.family": ["Capex", "Incident", "5G / Colocation"],
                        "operational_teams.archetype": list(TEAM_ARCHETYPES),
                        "team_memberships.role": ["leader", "pm", "coordinator", "member"],
                        "ops_team_members.family": ["Capex", "Incident", "5G / Colocation"],
                        "project_responsibilities.role": ["pm", "coordinator", "weekly_pm"],
                        "project_tawal_rules.mode": ["inherit", "exception", "cleared"]},
            "references": references,
            "pending_builder_contacts": sum(r["enabled"] and not r["tawal_contact"] for r in datasets["builder_contacts"]),
            "counts": {key: len(value) for key, value in datasets.items()}}


@frappe.whitelist()
def get_history():
    _require(editor=True)
    return frappe.get_all(REVISION, fields=["revision", "published_at", "published_by", "content_hash"], order_by="revision desc", limit_page_length=50)


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
    streams = frappe.get_all("SIG Project Stream", fields=["name", "alias", "project"], limit_page_length=10000) if frappe.db.exists("DocType", "SIG Project Stream") else []
    return {"projects": projects, "contacts": contacts, "active_contacts": active_contacts,
            "items": items, "streams": streams, "uoms": uoms, "employees": employees}


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
    if merged.get("project_responsibilities", []) != current.get("project_responsibilities", []):
        frappe.throw("Import cannot change legacy Project responsibility rows. Use Operations Project team members instead.")
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


@frappe.whitelist()
def get_setup_bundle(workbook_type, adapter_version=0, last_revision=0, revision=None):
    _require()
    if int(adapter_version) != ADAPTER_VERSION:
        frappe.throw("Unsupported Excel Setup adapter. Import the matching BAS release.")
    doc, datasets = _state()
    current = int(doc.revision or 0)
    if revision is not None:
        old = frappe.get_doc(REVISION, {"revision": int(revision)})
        current, datasets = int(old.revision), json.loads(old.configuration_json)
        doc = old
    if is_legacy(datasets):
        frappe.throw("Legacy Project/Builder associations are unverified. Publish the split setup and re-export Builder profiles.")
    datasets = _validated(datasets)
    projected = project_bundle(datasets, workbook_type)
    result = {"result": "ok", "contract": CONTRACT, "schema_version": SCHEMA_VERSION, "revision": current,
              "minimum_adapter_version": ADAPTER_VERSION, "workbook_type": workbook_type,
              "scope": "shared_published_setup", "complete": current > 0 and bundle_complete(datasets, workbook_type),
              "hash": digest(projected), "published_at": str(doc.published_at or ""),
              "counts": {key: len(value) for key, value in projected.items()}}
    result["unchanged"] = current > 0 and int(last_revision) == current
    result["datasets"] = {} if result["unchanged"] else projected
    if not result["unchanged"]:
        payload = canonical(projected)
        result["payload_json"] = payload
        result["payload_sha256_b64"] = base64.b64encode(hashlib.sha256(payload.encode("utf-8")).digest()).decode("ascii")
    return result


def prepare_roles():
    """Before model sync: only these two new roles, no existing matrix changes."""
    for role in ("SIG Excel Setup Editor", "SIG Excel Setup Reader"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": int(role.endswith("Editor"))}).insert(ignore_permissions=True)
