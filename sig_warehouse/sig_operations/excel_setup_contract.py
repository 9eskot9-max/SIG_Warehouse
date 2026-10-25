"""Pure, shared Excel Setup validation. No Frappe or workbook dependencies."""
import copy
import hashlib
import json
import re

CONTRACT = "SIG_EXCEL_SETUP_V2"
ADAPTER_VERSION = 2
SCHEMA_VERSION = 2
FIELDS = {
    "projects": ("id", "project", "po", "family", "upl_revision", "enabled"),
    "builder_profiles": ("id", "alias", "template", "internal_pm", "enabled"),
    "builder_contacts": ("id", "profile", "tawal_contact", "contact_name", "contact_phone", "contact_email", "origin", "enabled"),
    "project_builder_links": ("id", "project", "profile", "stream", "stream_alias", "enabled"),
    "tag_definitions": ("id", "item", "rule", "priority", "po", "enabled"),
    "tag_upl_links": ("id", "tag_item", "cuc", "description", "tag_matcher", "builder_rule", "po", "upl_revision", "enabled"),
    "material_upl_links": ("id", "item_code", "cuc", "source_uom", "target_uom", "treatment", "quantity_basis", "po", "upl_revision", "enabled"),
    "builder_defaults": ("id", "kind", "key", "value", "value2", "po", "enabled"),
    "teams": ("id", "leader", "team", "phone", "archetype", "enabled"),
}
REQUIRED = {
    "projects": ("id", "project"),
    "builder_profiles": ("id", "alias"),
    "builder_contacts": ("id", "profile"),
    "project_builder_links": ("id", "project", "profile"),
    "tag_definitions": ("id", "item", "rule"),
    "tag_upl_links": ("id", "tag_item", "cuc"),
    "material_upl_links": ("id", "item_code", "treatment"),
    "builder_defaults": ("id", "kind", "key", "value"),
    "teams": ("id", "leader"),
}
KINDS = {"purpose_reason", "csv_remarks", "tms_implementer"}
# Project teams are planned by the Field Planner; Incident teams are labelled and never planned.
TEAM_ARCHETYPES = ("Project", "Incident")
WORKBOOK_DATASETS = {
    "RV80": ("projects", "builder_profiles", "builder_contacts", "project_builder_links", "tag_definitions", "builder_defaults"),
    "SIGPC": ("projects", "tag_definitions", "tag_upl_links", "material_upl_links"),
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def natural_key(dataset, row):
    keys = {
        "projects": ("project",),
        "builder_profiles": ("alias",),
        "builder_contacts": ("profile", "tawal_contact", "contact_email", "contact_name"),
        "project_builder_links": ("project", "profile", "stream"),
        "tag_definitions": ("po", "item", "rule"),
        "tag_upl_links": ("po", "upl_revision", "tag_item", "cuc", "tag_matcher"),
        "material_upl_links": ("po", "upl_revision", "item_code", "cuc"),
        "builder_defaults": ("po", "kind", "key"),
        "teams": ("leader",),
    }[dataset]
    return tuple(str(row.get(k, "")).strip().casefold() for k in keys)


def validate(datasets):
    if not isinstance(datasets, dict) or set(datasets) - set(FIELDS):
        raise ValueError("Unknown or invalid setup dataset")
    result = {name: [] for name in FIELDS}
    for name, rows in datasets.items():
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError(f"{name}: expected at most 10,000 rows")
        ids, keys = set(), set()
        for index, supplied in enumerate(rows, 1):
            if not isinstance(supplied, dict) or set(supplied) - set(FIELDS[name]):
                raise ValueError(f"{name} row {index}: unknown fields")
            row = {}
            for field in FIELDS[name]:
                value = supplied.get(field, "")
                if field == "enabled":
                    if value in ("", None):
                        value = True
                    if value not in (True, False, 0, 1):
                        raise ValueError(f"{name} row {index}: enabled must be boolean")
                    row[field] = bool(value)
                else:
                    if isinstance(value, (dict, list, bool)):
                        raise ValueError(f"{name} row {index}: {field} must be text")
                    row[field] = str(value if value is not None else "").strip()
                    if len(row[field]) > 2000:
                        raise ValueError(f"{name} row {index}: {field} is too long")
            for field in REQUIRED[name]:
                if not row[field]:
                    raise ValueError(f"{name} row {index}: {field} is required")
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", row["id"]) or row["id"] in ids:
                raise ValueError(f"{name} row {index}: invalid/duplicate ID")
            ids.add(row["id"])
            key = natural_key(name, row)
            if key in keys:
                raise ValueError(f"{name} row {index}: duplicate scoped rule")
            keys.add(key)
            if name == "tag_definitions":
                try:
                    row["priority"] = str(int(row["priority"] or "0"))
                except ValueError as exc:
                    raise ValueError("Tags rule priority must be an integer") from exc
            if name == "builder_contacts":
                row["origin"] = row["origin"] or "ERP directory"
                if row["origin"] not in ("ERP directory", "RV80 Builder"):
                    raise ValueError("Builder contact origin must be ERP directory or RV80 Builder")
            if name == "material_upl_links":
                if row["treatment"] not in ("Direct 1:1", "Excluded", "Manual"):
                    raise ValueError("Material link treatment must be Direct 1:1, Excluded or Manual")
                if row["treatment"] == "Direct 1:1":
                    if not all(row[k] for k in ("cuc", "source_uom", "target_uom", "quantity_basis")):
                        raise ValueError("Direct material link needs CUC, both UOMs and reviewed quantity basis")
                    if row["source_uom"].casefold() != row["target_uom"].casefold():
                        raise ValueError("Direct material links cannot convert UOM")
            if name == "teams":
                row["archetype"] = row["archetype"] or "Project"
                if row["archetype"] not in TEAM_ARCHETYPES:
                    raise ValueError("Team archetype must be Project or Incident")
            if name == "builder_defaults" and row["kind"] not in KINDS:
                raise ValueError("Adapter v1 supports purpose_reason, csv_remarks and tms_implementer Builder lists")
            if name == "builder_defaults" and row["po"]:
                raise ValueError("Adapter v1 Builder wording is shared; PO-scoped wording needs a scoped consumer")
            result[name].append(row)
    definitions = {}
    for row in result["tag_definitions"]:
        if row["enabled"]:
            definitions.setdefault(row["item"].casefold(), set()).add(row["po"].casefold())
    profiles = {r["id"]: r for r in result["builder_profiles"] if r["enabled"]}
    projects = {r["project"] for r in result["projects"] if r["enabled"]}
    for row in result["builder_contacts"]:
        if row["enabled"] and row["profile"] not in profiles:
            raise ValueError("Builder contact requires an enabled Builder profile")
        if row["enabled"] and not any(row[k] for k in ("tawal_contact", "contact_name", "contact_email")):
            raise ValueError("Builder contact requires an existing directory contact")
    for row in result["project_builder_links"]:
        if row["enabled"] and (row["profile"] not in profiles or row["project"] not in projects):
            raise ValueError("Assignment requires an enabled ERP Project and Builder profile")
    # A legacy Builder block includes one placeholder row for a profile without contacts.
    contact_profiles = {r["profile"] for r in result["builder_contacts"] if r["enabled"]}
    if sum(row["enabled"] for row in result["builder_contacts"]) + len(set(profiles) - contact_profiles) > 999:
        raise ValueError("Current RV80 Builder consumers support at most 999 enabled contact rows")
    revisions = {}
    for row in result["projects"]:
        if not row["enabled"]:
            continue
        if row["upl_revision"]:
            scope = row["po"].casefold() or ("project:" + row["project"].casefold())
            revisions.setdefault(scope, set()).add(row["upl_revision"].casefold())
    if any(len(values) > 1 for values in revisions.values()):
        raise ValueError("Conflicting UPL revisions for one PO")
    for row in result["tag_upl_links"]:
        if row["enabled"]:
            scopes = definitions.get(row["tag_item"].casefold(), set())
            if "" not in scopes and (not row["po"] or row["po"].casefold() not in scopes):
                raise ValueError(f"Tags definition missing for {row['tag_item']} in this PO scope")
    # Stable publication and importer order, independent of UI sort order.
    for name in result:
        result[name].sort(key=(lambda row: (int(row["priority"]), row["id"])) if name == "tag_definitions" else (lambda row: row["id"]))
    return result


def merge_import(current, package):
    if not isinstance(package, dict) or package.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Import requires schema_version 2; re-export independent Builder lists")
    if set(package) - {"schema_version", "batch_id", "source", "datasets"}:
        raise ValueError("Unknown import envelope fields")
    if not isinstance(package.get("batch_id"), str) or not 1 <= len(package["batch_id"]) <= 120:
        raise ValueError("Import requires batch_id (1–120 characters)")
    incoming = package.get("datasets")
    if not isinstance(incoming, dict) or set(incoming) - set(FIELDS):
        raise ValueError("Unknown import dataset")
    merged = copy.deepcopy(current)
    counts = {"added": 0, "changed": 0, "unchanged": 0}
    for name, rows in incoming.items():
        if not isinstance(rows, list):
            raise ValueError(f"{name}: rows must be an array")
        by_id = {row["id"]: row for row in merged.get(name, [])}
        incoming_ids = set()
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                raise ValueError("Every imported row needs an ID")
            if row["id"] in incoming_ids:
                raise ValueError(f"{name}: duplicate ID inside import batch")
            incoming_ids.add(row["id"])
            old = by_id.get(row["id"])
            counts["added" if old is None else "unchanged" if old == row else "changed"] += 1
            by_id[row["id"]] = row
        merged[name] = list(by_id.values())
    return validate(merged), counts


def project_bundle(datasets, workbook_type):
    if workbook_type not in WORKBOOK_DATASETS:
        raise ValueError("workbook_type must be RV80 or SIGPC")
    result = {name: copy.deepcopy(datasets[name]) for name in WORKBOOK_DATASETS[workbook_type]}
    if workbook_type == "SIGPC":
        # SIGPC needs scope identity, never RV80's contact/template directory.
        result["projects"] = [{key: row[key] for key in ("id", "project", "po", "upl_revision", "enabled")} for row in result["projects"]]
    return result


def is_legacy(datasets):
    return "builder_profiles" not in datasets


def upgrade_legacy(datasets):
    """Keep canonical scope facts. Never infer a profile/PO relation from v1 rows.

    The immutable v1 revision retains the rejected associations for audit. Profiles
    and their contacts must be re-exported from the independent Builder block.
    """
    if not is_legacy(datasets):
        return validate(datasets)
    result = {name: copy.deepcopy(datasets.get(name, [])) for name in FIELDS if name != "projects"}
    result["builder_profiles"] = []
    result["builder_contacts"] = []
    result["project_builder_links"] = []
    by_project = {}
    for old in datasets.get("projects", []):
        project = str(old.get("project", "")).strip()
        if not project:
            continue
        row = {k: old.get(k, "") for k in FIELDS["projects"]}
        row["id"] = "erp-project-" + hashlib.sha256(project.encode()).hexdigest()[:24]
        if project in by_project and any(str(row[k] or "").casefold() != str(by_project[project][k] or "").casefold()
                                         for k in ("po", "upl_revision")):
            raise ValueError("Conflicting legacy scope facts for " + project)
        by_project[project] = row
    result["projects"] = list(by_project.values())
    return validate(result)


def bundle_complete(datasets, workbook_type):
    needed = ("builder_profiles", "builder_contacts", "tag_definitions") if workbook_type == "RV80" else ("tag_definitions", "tag_upl_links")
    complete = all(any(row["enabled"] for row in datasets.get(name, [])) for name in needed)
    if workbook_type == "RV80":
        complete = complete and all(row["tawal_contact"] for row in datasets.get("builder_contacts", []) if row["enabled"])
    return bool(complete)
