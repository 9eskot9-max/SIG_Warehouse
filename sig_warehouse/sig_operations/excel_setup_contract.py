"""Pure, shared Excel Setup validation. No Frappe or workbook dependencies."""
import copy
import hashlib
import json
import re

CONTRACT = "SIG_EXCEL_SETUP_V1"
ADAPTER_VERSION = 1
FIELDS = {
    "projects": ("id", "project", "po", "alias", "family", "stream", "template", "internal_pm", "tawal_contact", "contact_name", "contact_phone", "contact_email", "upl_revision", "enabled"),
    "tag_definitions": ("id", "item", "rule", "priority", "po", "enabled"),
    "tag_upl_links": ("id", "tag_item", "cuc", "description", "tag_matcher", "builder_rule", "po", "upl_revision", "enabled"),
    "material_upl_links": ("id", "item_code", "cuc", "source_uom", "target_uom", "treatment", "quantity_basis", "po", "upl_revision", "enabled"),
    "builder_defaults": ("id", "kind", "key", "value", "value2", "po", "enabled"),
}
REQUIRED = {
    "projects": ("id", "project", "po", "alias"),
    "tag_definitions": ("id", "item", "rule"),
    "tag_upl_links": ("id", "tag_item", "cuc"),
    "material_upl_links": ("id", "item_code", "treatment"),
    "builder_defaults": ("id", "kind", "key", "value"),
}
KINDS = {"purpose_reason", "csv_remarks", "tms_implementer"}
WORKBOOK_DATASETS = {
    "RV80": ("projects", "tag_definitions", "builder_defaults"),
    "SIGPC": ("projects", "tag_definitions", "tag_upl_links", "material_upl_links"),
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def natural_key(dataset, row):
    keys = {
        "projects": ("project", "alias", "contact_email", "contact_name"),
        "tag_definitions": ("po", "item", "rule"),
        "tag_upl_links": ("po", "upl_revision", "tag_item", "cuc", "tag_matcher"),
        "material_upl_links": ("po", "upl_revision", "item_code", "cuc"),
        "builder_defaults": ("po", "kind", "key"),
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
            if name == "material_upl_links":
                if row["treatment"] not in ("Direct 1:1", "Excluded", "Manual"):
                    raise ValueError("Material link treatment must be Direct 1:1, Excluded or Manual")
                if row["treatment"] == "Direct 1:1":
                    if not all(row[k] for k in ("cuc", "source_uom", "target_uom", "quantity_basis")):
                        raise ValueError("Direct material link needs CUC, both UOMs and reviewed quantity basis")
                    if row["source_uom"].casefold() != row["target_uom"].casefold():
                        raise ValueError("Direct material links cannot convert UOM")
            if name == "builder_defaults" and row["kind"] not in KINDS:
                raise ValueError("Adapter v1 supports purpose_reason, csv_remarks and tms_implementer Builder lists")
            if name == "builder_defaults" and row["po"]:
                raise ValueError("Adapter v1 Builder wording is shared; PO-scoped wording needs a scoped consumer")
            result[name].append(row)
    definitions = {}
    for row in result["tag_definitions"]:
        if row["enabled"]:
            definitions.setdefault(row["item"].casefold(), set()).add(row["po"].casefold())
    if sum(row["enabled"] for row in result["projects"]) > 999:
        raise ValueError("Current RV80 Builder consumers support at most 999 enabled contact rows")
    aliases, revisions = {}, {}
    for row in result["projects"]:
        if not row["enabled"]:
            continue
        alias = row["alias"].casefold()
        if alias in aliases and aliases[alias] != row["project"]:
            raise ValueError("One Builder alias cannot select multiple canonical Projects")
        aliases[alias] = row["project"]
        if row["upl_revision"]:
            revisions.setdefault(row["po"], set()).add(row["upl_revision"].casefold())
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
    if not isinstance(package, dict) or package.get("schema_version") != 1:
        raise ValueError("Import requires schema_version 1")
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
