"""Version 3 Excel reference projection and native PO contact setup.

The only workbook bundle (the v2 bundle and Builder data were removed on
24 November 2026). A PO takes its family's dated TAWAL PM; a one-off exception
is chosen in the RV80 TCN batch prompt and is not stored in ERP.
"""
import json

import frappe

from sig_warehouse.sig_operations.excel_setup import (
    EDIT_ROLES,
    READ_ROLES,
    SETUP,
    _state,
)
from sig_warehouse.sig_operations.excel_setup_contract import WORKBOOK_DATASETS, canonical, digest, validate
from sig_warehouse.sig_warehouse.project_family import resolve_project_family
from frappe.utils import getdate, nowdate


CONTRACT = "SIG_EXCEL_SETUP_V3"
SCHEMA_VERSION = 3
ADAPTER_VERSION = 3


def _require(editor=False):
    roles = EDIT_ROLES if editor else READ_ROLES
    if frappe.session.user == "Guest" or not (set(frappe.get_roles()) & roles):
        frappe.throw("Not permitted to edit Excel PO setup" if editor else "Not permitted to fetch Excel setup", frappe.PermissionError)


def _meta_project_fields():
    meta = frappe.get_meta("Project")
    required = ("custom_default_tawal_contact", "custom_excel_csv_alias")
    missing = [field for field in required if not meta.has_field(field)]
    if missing:
        frappe.throw("Excel PO setup fields are not installed: " + ", ".join(missing))
    return meta


def _family_default(datasets, family, as_of=None):
    if not family:
        return None
    as_of = getdate(as_of or nowdate())
    family_key = "Colocation" if family == "5G / Colocation" else family
    matches = []
    for row in datasets.get("family_tawal_defaults", []):
        row_family = "Colocation" if row.get("family") == "5G / Colocation" else row.get("family")
        if not row.get("enabled") or row_family != family_key:
            continue
        start = getdate(row["effective_from"])
        end = getdate(row["effective_to"]) if row.get("effective_to") else None
        if start <= as_of and (end is None or as_of <= end):
            matches.append(row)
    if len(matches) > 1:
        frappe.throw("More than one effective TAWAL contact default exists for family " + family_key)
    return matches[0] if matches else None


def _configured_project_rows(datasets):
    meta = _meta_project_fields()
    project_fields = ["name", "project_name", "custom_default_tawal_contact", "custom_excel_csv_alias"]
    for field in ("custom_agreement_no", "custom_tawal_ba", "custom_po_number",
                  "custom_project_family", "custom_family", "custom_is_canonical_agreement"):
        if meta.has_field(field):
            project_fields.append(field)

    result = []
    seen = set()
    seen_po = set()
    for setup_row in datasets["projects"]:
        if not setup_row["enabled"]:
            continue
        project_name = setup_row["project"]
        if project_name in seen:
            frappe.throw("Excel PO setup contains duplicate Project " + project_name)
        seen.add(project_name)
        project = frappe.db.get_value("Project", project_name, project_fields, as_dict=True)
        if not project:
            frappe.throw("Configured ERP Project no longer exists: " + project_name)
        if meta.has_field("custom_is_canonical_agreement") and not project.custom_is_canonical_agreement:
            frappe.throw("Configured Project is not the canonical agreement: " + project_name)
        po = next((str(project.get(key) or "").strip() for key in
                   ("custom_agreement_no", "custom_tawal_ba", "custom_po_number")
                   if str(project.get(key) or "").strip()), str(setup_row.get("po") or "").strip())
        po_key = po.casefold()
        if po_key and po_key in seen_po:
            frappe.throw("More than one configured canonical ERP Project uses PO " + po)
        if po_key:
            seen_po.add(po_key)
        family_state = resolve_project_family(project)
        if family_state["conflict"]:
            frappe.throw("Project family fields disagree for " + project.name + "; reconcile before syncing RV80")
        family = family_state["family"] or (family_state["values"][0]["value"] if family_state["values"] else "")
        family_default = _family_default(datasets, family_state["family"])
        effective_contact = family_default.get("tawal_contact") if family_default else ""
        contact_source = "family default" if family_default else "unconfigured"
        contact_from = family_default.get("effective_from", "") if family_default else ""
        contact_to = family_default.get("effective_to", "") if family_default else ""
        project_row = {
            "id": str(setup_row["id"]),
            "project": project.name,
            "project_name": project.project_name or project.name,
            "po": po,
            "family": family,
            "family_label": family_state["label"],
            "family_conflict": family_state["conflict"],
            "family_sources": [],
            "upl_revision": str(setup_row.get("upl_revision") or ""),
            "csv_alias": str(project.custom_excel_csv_alias or "").strip(),
            "default_contact": effective_contact,
            "contact_source": contact_source,
            "contact_rule_mode": "",
            "contact_effective_from": contact_from,
            "contact_effective_to": contact_to,
            "contact_family": family_state["family"],
            "enabled": True,
        }
        result.append(project_row)
    return sorted(result, key=lambda row: (row["po"].casefold(), row["project"].casefold()))


def _active_contacts():
    doctype = "SIG TAWAL Contact"
    if not frappe.db.exists("DocType", doctype):
        frappe.throw("The native SIG TAWAL Contact directory is required for Excel Setup v3")
    meta = frappe.get_meta(doctype)
    if not meta.has_field("active"):
        frappe.throw("The TAWAL contact directory must expose an active flag before Excel Setup v3 can sync it")
    # Contact record names remain the stable selection key. Display the existing
    # serial when the installed directory has one; deployments without that
    # optional field still work and show the record ID instead of querying a
    # column that may not exist.
    serial_field = next((field for field in
                         ("contact_key", "contact_serial", "serial", "custom_contact_serial", "custom_serial")
                         if meta.has_field(field)), None)
    fields = ["name", "full_name", "mobile", "email"]
    if serial_field:
        fields.append(serial_field)
    rows = frappe.get_all(doctype, filters={"active": 1}, fields=fields,
                          order_by=(serial_field + " asc, name asc") if serial_field else "name asc",
                          limit_page_length=10000)
    result = [{"id": row.name, "serial": str(row.get(serial_field) or row.name) if serial_field else row.name,
             "full_name": str(row.full_name or ""), "mobile": str(row.mobile or ""),
             "email": str(row.email or ""), "active": True} for row in rows]
    serials = [row["serial"].casefold() for row in result]
    if len(serials) != len(set(serials)):
        frappe.throw("The active TAWAL directory has duplicate contact serials; resolve them before Excel Setup v3.")
    return result


def _v3_datasets(datasets, workbook_type):
    """RV80 is the only workbook (SIGPC was merged into it and retired)."""
    if workbook_type != "RV80":
        frappe.throw("workbook_type must be RV80")
    projects = _configured_project_rows(datasets)
    contacts = _active_contacts()
    active_contact_ids = {row["id"] for row in contacts}
    missing = [row["po"] or row["project"] for row in projects
               if row["default_contact"] and row["default_contact"] not in active_contact_ids]
    if missing:
        frappe.throw("Configured TAWAL default is missing or inactive for: " + ", ".join(missing))
    return {"projects": projects, "contacts": contacts, "tag_definitions": datasets["tag_definitions"],
            "builder_defaults": datasets["builder_defaults"], "tag_upl_links": datasets["tag_upl_links"],
            "material_upl_links": datasets["material_upl_links"]}


def _validated_v3(datasets, workbook_type):
    """Validate only the published datasets consumed by this workbook."""
    names = WORKBOOK_DATASETS[workbook_type]
    payload = {name: datasets.get(name, []) for name in names}
    try:
        return validate(payload)
    except ValueError as exc:
        frappe.throw(str(exc))


@frappe.whitelist()
def get_setup_bundle(workbook_type, adapter_version=0, last_revision=0, last_hash=""):
    _require()
    if int(adapter_version) != ADAPTER_VERSION:
        frappe.throw("Excel Setup v3 requires the matching BAS release.")
    doc, datasets = _state()
    if not datasets.get("projects"):
        frappe.throw("Publish the existing Excel Project setup before syncing v3.")
    datasets = _validated_v3(datasets, workbook_type)
    projected = _v3_datasets(datasets, workbook_type)
    current = int(doc.revision or 0)
    content_hash = digest(projected)
    required = ("projects", "tag_definitions")
    complete = current > 0 and all(projected.get(key) for key in required)
    if workbook_type == "RV80":
        complete = complete and bool(projected.get("contacts"))
    result = {
        "result": "ok", "contract": CONTRACT, "schema_version": SCHEMA_VERSION,
        "revision": current, "minimum_adapter_version": ADAPTER_VERSION,
        "workbook_type": workbook_type, "scope": "shared_published_setup",
        "complete": bool(complete), "hash": content_hash,
        "published_at": str(doc.published_at or ""),
        "counts": {key: len(value) for key, value in projected.items()},
    }
    result["unchanged"] = bool(current > 0 and str(last_hash or "") == content_hash)
    result["datasets"] = {} if result["unchanged"] else projected
    if not result["unchanged"]:
        payload = canonical(projected)
        import base64
        import hashlib
        result["payload_json"] = payload
        result["payload_sha256_b64"] = base64.b64encode(
            hashlib.sha256(payload.encode("utf-8")).digest()).decode("ascii")
    return result


def _po_setup_state(datasets):
    projects = _configured_project_rows(datasets)
    contacts = _active_contacts()
    projection = {"projects": projects, "contacts": contacts}
    return {**projection, "hash": digest(projection)}


@frappe.whitelist()
def get_po_setup_state():
    _require(editor=True)
    doc, datasets = _state()
    datasets = _validated_v3(datasets, "RV80")
    return {"revision": int(doc.revision or 0), **_po_setup_state(datasets)}


@frappe.whitelist(methods=["POST"])
def save_po_setup(rows, base_revision, base_hash):
    """Save only the optional per-PO CSV label. The TAWAL PM comes from the family default."""
    _require(editor=True)
    rows = json.loads(rows) if isinstance(rows, str) else rows
    if not isinstance(rows, list):
        frappe.throw("PO setup must be a list")
    setup_doc, datasets = _state(lock=True)
    if int(base_revision) != int(setup_doc.revision or 0):
        frappe.throw("Excel Setup changed in another session. Reload before saving PO labels.")
    datasets = _validated_v3(datasets, "RV80")
    current = _po_setup_state(datasets)
    if str(base_hash or "") != current["hash"]:
        frappe.throw("PO labels or contact directory changed in another session. Reload before saving.")
    expected = {row["project"]: row for row in current["projects"]}
    labels = {}
    for index, row in enumerate(rows, 1):
        project = str((row or {}).get("project") or "").strip() if isinstance(row, dict) else ""
        alias = str(row.get("csv_alias") or "").strip() if project else ""
        if project not in expected or project in labels or len(alias) > 140:
            frappe.throw("PO setup row " + str(index) + " is invalid, duplicate, or its label exceeds 140 characters")
        labels[project] = alias
    if set(labels) != set(expected):
        frappe.throw("Submit the complete visible Project list. No PO label was changed.")
    for project, alias in labels.items():
        if expected[project]["csv_alias"] != alias:
            frappe.db.set_value("Project", project, {"custom_excel_csv_alias": alias})
    return {"result": "saved", **_po_setup_state(datasets)}
