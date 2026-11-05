"""Compatibility boundary for project-family labels used by SIG workflows.

``Colocation`` remains the internal key for existing task rosters and legacy
cycle consumers. ``5G / Colocation`` is the display label; RV80's legacy MOP
template token remains ``5G``. Conflicting populated Project fields fail closed.
"""
import re


DISPLAY_LABELS = {
    "Capex": "Capex",
    "Incident": "Incident",
    "Colocation": "5G / Colocation",
}


def normalize_family(value):
    key = re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())
    if key in {"5g", "colocation", "colo", "5gcolocation"}:
        return "Colocation"
    if key == "capex":
        return "Capex"
    if key == "incident":
        return "Incident"
    return ""


def resolve_project_family(project):
    """Return canonical family, display label and any conflicting source values."""
    project = project or {}
    sources = []
    for field in ("custom_project_family", "custom_family"):
        value = str(project.get(field) or "").strip()
        if value:
            sources.append({"field": field, "value": value, "family": normalize_family(value)})
    known = {row["family"] for row in sources if row["family"]}
    unknown = [row for row in sources if not row["family"]]
    unknown_values = {row["value"].casefold() for row in unknown}
    conflict = len(known) > 1 or bool(unknown and known) or len(unknown_values) > 1
    family = next(iter(known)) if len(known) == 1 and not conflict else ""
    return {
        "family": family,
        "label": DISPLAY_LABELS.get(family, ""),
        "source": sources[0]["field"] if family and sources else "",
        "conflict": conflict,
        "values": sources,
    }


def legacy_mop_token(value):
    """Project-family compatibility token required by existing RV80 templates."""
    family = normalize_family(value)
    return "5G" if family == "Colocation" else family or str(value or "").strip()
