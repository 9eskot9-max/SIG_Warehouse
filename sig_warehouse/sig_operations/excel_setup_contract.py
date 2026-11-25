"""Pure, shared Excel Setup validation. No Frappe or workbook dependencies.

The legacy Builder, Planner-leader, team-Project, Project-responsibility and PO
TAWAL-rule lists were removed on 24 November 2026 (snapshot kept under
ERPNext/backups/ops_setup_legacy_20261124). A one-run TAWAL exception is chosen
in the RV80 TCN batch prompt and is never stored here.
"""
import copy
import hashlib
import json
import re
from datetime import date

SCHEMA_VERSION = 2
FIELDS = {
    "projects": ("id", "project", "po", "upl_revision", "enabled"),
    "tag_definitions": ("id", "item", "rule", "priority", "po", "enabled"),
    "tag_upl_links": ("id", "tag_item", "cuc", "description", "tag_matcher", "builder_rule", "po", "upl_revision", "enabled"),
    "material_upl_links": ("id", "item_code", "cuc", "source_uom", "target_uom", "treatment", "quantity_basis", "po", "upl_revision", "enabled"),
    "builder_defaults": ("id", "kind", "key", "value", "value2", "po", "enabled"),
    "family_tawal_defaults": ("id", "family", "tawal_contact", "enabled"),
    "operational_teams": ("id", "team_name", "family", "archetype", "no_visit_message", "enabled"),
    "team_memberships": ("id", "team", "employee", "role", "effective_from", "effective_to", "enabled"),
    "ops_team_members": ("id", "family", "project", "employee", "role", "weekly_pm", "effective_from", "effective_to", "enabled"),
    "pc_family_defaults": ("id", "family", "review_group", "enabled"),
}
REQUIRED = {
    "projects": ("id", "project"),
    "tag_definitions": ("id", "item", "rule"),
    "tag_upl_links": ("id", "tag_item", "cuc"),
    "material_upl_links": ("id", "item_code", "treatment"),
    "builder_defaults": ("id", "kind", "key", "value"),
    "family_tawal_defaults": ("id", "family", "tawal_contact"),
    "operational_teams": ("id", "team_name", "family", "archetype"),
    "team_memberships": ("id", "team", "employee", "role", "effective_from"),
    "ops_team_members": ("id", "employee", "role", "effective_from"),
    "pc_family_defaults": ("id", "family", "review_group"),
}
# Boolean columns and the value used when a row does not supply one.
BOOLEANS = {"enabled": True, "weekly_pm": False, "no_visit_message": True}
KINDS = {"purpose_reason", "csv_remarks", "tms_implementer"}
FAMILIES = ("Capex", "Incident", "Colocation", "5G / Colocation")
# Project (DC) and Incident teams are planned in separate Field Planner modes.
TEAM_ARCHETYPES = ("Project", "Incident")
OPS_ROLES = ("pm", "coordinator", "warehouse")
WORKBOOK_DATASETS = {"RV80": ("projects", "tag_definitions", "tag_upl_links", "material_upl_links", "builder_defaults", "family_tawal_defaults")}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def family_key(value):
    return "Colocation" if value == "5G / Colocation" else value


def _validate_date(value, label, required=False):
    if not value:
        if required:
            raise ValueError(label + " is required as YYYY-MM-DD")
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(label + " must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(label + " must be a real calendar date") from exc


def _period(row, label):
    start = _validate_date(row["effective_from"], label + " effective_from", True)
    end = _validate_date(row["effective_to"], label + " effective_to")
    if end and end < start:
        raise ValueError(label + " end date must not precede its start date")


def _no_overlap(rows, key, label):
    groups = {}
    for row in rows:
        if row["enabled"]:
            groups.setdefault(key(row), []).append(row)
    for group, items in groups.items():
        items.sort(key=lambda row: row["effective_from"])
        for prior, current in zip(items, items[1:]):
            if not prior["effective_to"] or prior["effective_to"] >= current["effective_from"]:
                raise ValueError("Overlapping " + label + " periods for " + str(group))


def natural_key(dataset, row):
    keys = {
        "projects": ("project",),
        "tag_definitions": ("po", "item", "rule"),
        "tag_upl_links": ("po", "upl_revision", "tag_item", "cuc", "tag_matcher"),
        "material_upl_links": ("po", "upl_revision", "item_code", "cuc"),
        "builder_defaults": ("po", "kind", "key"),
        "family_tawal_defaults": ("family", "tawal_contact"),
        "operational_teams": ("team_name",),
        "team_memberships": ("team", "employee", "role", "effective_from"),
        "ops_team_members": ("family", "project", "employee", "role", "effective_from"),
        "pc_family_defaults": ("family",),
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
                if field in BOOLEANS:
                    if value in ("", None):
                        value = BOOLEANS[field]
                    if value not in (True, False, 0, 1):
                        raise ValueError(f"{name} row {index}: {field} must be boolean")
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
            if name == "family_tawal_defaults":
                # One family spelling, so "Colocation" and "5G / Colocation" cannot hide a duplicate.
                if row["family"] not in FAMILIES:
                    raise ValueError("TAWAL family defaults must use Capex, Incident or 5G / Colocation")
                if row["family"] == "Colocation":
                    row["family"] = "5G / Colocation"
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
            if name == "pc_family_defaults" and row["family"] not in ("Capex", "Incident", "5G / Colocation"):
                raise ValueError("PC family default needs Capex, Incident or 5G / Colocation")
            if name == "operational_teams":
                if row["family"] not in FAMILIES:
                    raise ValueError("Field crew needs a reviewed family: Capex, Incident or 5G / Colocation")
                if row["archetype"] not in TEAM_ARCHETYPES:
                    raise ValueError("Field crew archetype must be Project or Incident")
            if name == "team_memberships":
                if row["role"] not in ("leader", "member"):
                    raise ValueError("Crew membership role must be leader or member")
                _period(row, "Crew membership")
            if name == "ops_team_members":
                if row["role"] not in OPS_ROLES:
                    raise ValueError("Operations role must be pm, coordinator or warehouse")
                if row["role"] == "warehouse":
                    # Warehouse owners cover every family and are not scoped to a Project.
                    if row["family"] or row["project"] or row["weekly_pm"]:
                        raise ValueError("A warehouse owner has no family, Project or weekly PM check")
                else:
                    if row["family"] not in FAMILIES:
                        raise ValueError("Operations team needs a supported family")
                    if row["family"] == "Colocation":
                        row["family"] = "5G / Colocation"
                if row["weekly_pm"] and row["role"] != "pm":
                    raise ValueError("Only a PM can receive the weekly PM check")
                _period(row, "Operations team")
            if name == "builder_defaults":
                if row["kind"] not in KINDS:
                    raise ValueError("Adapter v1 supports purpose_reason, csv_remarks and tms_implementer Builder lists")
                if row["po"]:
                    raise ValueError("Adapter v1 Builder wording is shared; PO-scoped wording needs a scoped consumer")
            result[name].append(row)
    definitions = {}
    for row in result["tag_definitions"]:
        if row["enabled"]:
            definitions.setdefault(row["item"].casefold(), set()).add(row["po"].casefold())
    active = [family_key(r["family"]) for r in result["family_tawal_defaults"] if r["enabled"]]
    for family in sorted(set(active)):
        if active.count(family) > 1:
            raise ValueError("More than one active TAWAL PM for " + family + "; keep only one ticked Active")
    teams = {row["id"] for row in result["operational_teams"] if row["enabled"]}
    for row in result["team_memberships"]:
        if row["enabled"] and row["team"] not in teams:
            raise ValueError("team_memberships references a missing or disabled field crew")
    _no_overlap(result["team_memberships"], lambda r: (r["team"], r["employee"], r["role"]), "Crew membership")
    _no_overlap([r for r in result["team_memberships"] if r["role"] == "leader"], lambda r: r["team"], "Crew leader")
    _no_overlap(result["ops_team_members"], lambda r: (r["family"], r["project"], r["employee"], r["role"]), "Operations team")
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


def active_on(row, day):
    """True when an enabled dated row covers the ISO date `day`."""
    start, end = str(row.get("effective_from") or "")[:10], str(row.get("effective_to") or "")[:10]
    return bool(row.get("enabled") and start and start <= day and (not end or day <= end))


def setup_warnings(datasets, day):
    """Plain-language problems an Operations editor should fix. Never blocks a save."""
    notes = []
    for family in ("Capex", "Incident", "Colocation"):
        if not any(family_key(r["family"]) == family and r["enabled"] for r in datasets.get("family_tawal_defaults", [])):
            notes.append(f"No TAWAL PM is ticked Active for {family}: its POs get no PM in TCN.")
        members = [r for r in datasets.get("ops_team_members", []) if active_on(r, day) and family_key(r["family"]) == family]
        for role in ("pm", "coordinator"):
            if not any(r["role"] == role for r in members):
                notes.append(f"{family} has no active Operations {role}.")
    leaders = {}
    for row in datasets.get("team_memberships", []):
        if row["role"] == "leader" and active_on(row, day):
            leaders.setdefault(row["team"], set()).add(row["employee"])
    for team in datasets.get("operational_teams", []):
        if team["enabled"] and len(leaders.get(team["id"], ())) != 1:
            notes.append(f"Crew {team['team_name']} needs exactly one active leader today; Planner skips it otherwise.")
    return notes


def merge_import(current, package):
    if not isinstance(package, dict) or package.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Import requires schema_version 2")
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
