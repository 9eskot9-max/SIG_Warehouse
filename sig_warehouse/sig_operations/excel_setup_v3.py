"""Version 3 Excel reference projection and native PO contact setup.

Version 2 remains available through ``excel_setup.get_setup_bundle``. This
module gives updated workbooks a PO-first projection without changing the
stored v2 configuration or deriving contacts from Builder aliases.
"""
import json

import frappe

from sig_warehouse.sig_operations.excel_setup import (
    EDIT_ROLES,
    READ_ROLES,
    SETUP,
    _state,
)
from sig_warehouse.sig_operations.excel_setup_contract import canonical, digest, validate


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


def _effective_default_contact(project, field_contact):
    defaults = frappe.get_all("SIG Project PM Assignment",
        filters={"project": project, "active": 1, "is_default": 1},
        fields=["tawal_contact"], limit_page_length=2)
    if len(defaults) > 1:
        frappe.throw("More than one active default TAWAL assignment exists for " + project)
    assigned = str(defaults[0].tawal_contact or "").strip() if defaults else ""
    field_contact = str(field_contact or "").strip()
    if assigned and field_contact and assigned != field_contact:
        frappe.throw("Project default and active TAWAL assignment disagree for " + project + "; reconcile them before syncing")
    return field_contact or assigned


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
        family = next((str(project.get(key) or "").strip() for key in
                       ("custom_project_family", "custom_family")
                       if str(project.get(key) or "").strip()), str(setup_row.get("family") or "").strip())
        result.append({
            "id": str(setup_row["id"]),
            "project": project.name,
            "project_name": project.project_name or project.name,
            "po": po,
            "family": family,
            "upl_revision": str(setup_row.get("upl_revision") or ""),
            "csv_alias": str(project.custom_excel_csv_alias or "").strip(),
            "default_contact": _effective_default_contact(project.name, project.custom_default_tawal_contact),
            "enabled": True,
        })
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
    projects = _configured_project_rows(datasets)
    result = {"projects": projects}
    if workbook_type == "RV80":
        result["contacts"] = _active_contacts()
        result["tag_definitions"] = datasets["tag_definitions"]
        result["builder_defaults"] = datasets["builder_defaults"]
    elif workbook_type == "SIGPC":
        result["tag_definitions"] = datasets["tag_definitions"]
        result["tag_upl_links"] = datasets["tag_upl_links"]
        result["material_upl_links"] = datasets["material_upl_links"]
    else:
        frappe.throw("workbook_type must be RV80 or SIGPC")
    return result


def _validated_v3(datasets, workbook_type):
    """Validate only the published datasets consumed by this workbook.

    Builder profiles and profile-linked contacts/assignments remain in the
    V2 archive for compatibility. They must not be a prerequisite for the
    PO-first V3 sync.
    """
    names = ("projects", "tag_definitions", "builder_defaults") if workbook_type == "RV80" else (
        "projects", "tag_definitions", "tag_upl_links", "material_upl_links")
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
    """Edit PO CSV labels and default TAWAL PMs through the existing setup authority."""
    _require(editor=True)
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except ValueError:
            frappe.throw("Invalid PO setup rows")
    if not isinstance(rows, list):
        frappe.throw("PO setup must be a list")

    setup_doc, datasets = _state(lock=True)
    if int(base_revision) != int(setup_doc.revision or 0):
        frappe.throw("Excel Setup changed in another session. Reload before saving PO defaults.")
    datasets = _validated_v3(datasets, "RV80")
    current = _po_setup_state(datasets)
    if str(base_hash or "") != current["hash"]:
        frappe.throw("PO defaults or contact directory changed in another session. Reload before saving.")

    expected = {row["project"]: row for row in current["projects"]}
    supplied = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            frappe.throw("PO setup row " + str(index) + " is invalid")
        project = str(row.get("project") or "").strip()
        if project not in expected or project in supplied:
            frappe.throw("PO setup includes an unknown or duplicate Project")
        alias = str(row.get("csv_alias") or "").strip()
        if len(alias) > 140:
            frappe.throw("CSV alias must be 140 characters or fewer")
        supplied[project] = {"csv_alias": alias, "default_contact": str(row.get("default_contact") or "").strip()}
    if set(supplied) != set(expected):
        frappe.throw("Submit the complete visible Project list. No PO setting was changed.")

    directory = {row["id"]: row for row in current["contacts"]}
    for project, row in supplied.items():
        contact = row["default_contact"]
        if contact and contact not in directory and contact != expected[project]["default_contact"]:
            frappe.throw("Select an active TAWAL contact for " + project)

    current_projects = {row["project"]: row for row in current["projects"]}
    for project, row in supplied.items():
        before = current_projects[project]
        project_values = {}
        if before["csv_alias"] != row["csv_alias"]:
            project_values["custom_excel_csv_alias"] = row["csv_alias"]
        if before["default_contact"] != row["default_contact"]:
            project_values["custom_default_tawal_contact"] = row["default_contact"] or None
        if project_values:
            frappe.db.set_value("Project", project, project_values)
        if before["default_contact"] == row["default_contact"]:
            continue  # Alias-only/unchanged saves must not rewrite native assignments.
        assignments = frappe.get_all("SIG Project PM Assignment", filters={"project": project},
                                     fields=["name", "tawal_contact", "active", "is_default"],
                                     limit_page_length=1000)
        selected_assignment = None
        if row["default_contact"]:
            selected_assignment = next((item for item in assignments
                                        if item.tawal_contact == row["default_contact"]), None)
            if not selected_assignment:
                selected_assignment = frappe.get_doc({
                    "doctype": "SIG Project PM Assignment", "project": project,
                    "tawal_contact": row["default_contact"], "active": 1,
                    "is_default": 1, "source": "Excel Setup",
                }).insert(ignore_permissions=True)
        for assignment in assignments:
            is_selected = bool(selected_assignment and assignment.name == selected_assignment.name)
            values = {}
            if int(assignment.is_default or 0) != int(is_selected):
                values["is_default"] = int(is_selected)
            if is_selected and int(assignment.active or 0) != 1:
                values["active"] = 1
            if values:
                frappe.db.set_value("SIG Project PM Assignment", assignment.name, values)
        # Newly inserted row is already the sole active default.
    return {"result": "saved", **_po_setup_state(datasets)}
