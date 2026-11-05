import pytest

from sig_warehouse.sig_operations.excel_setup_contract import validate
from sig_warehouse.sig_warehouse.project_family import resolve_project_family, legacy_mop_token


def test_family_aliases_preserve_legacy_template_and_conflicts_are_unresolved():
    result = resolve_project_family({"custom_project_family": "5G", "custom_family": "5G / Colocation"})
    assert result["family"] == "Colocation"
    assert legacy_mop_token(result["label"]) == "5G"
    conflict = resolve_project_family({"custom_project_family": "Incident", "custom_family": "Colocation"})
    assert conflict["conflict"] and not conflict["family"]


def test_family_defaults_cannot_overlap_across_legacy_aliases():
    rows = [
        {"id": "a", "family": "Colocation", "tawal_contact": "C1", "effective_from": "2026-01-01", "enabled": True},
        {"id": "b", "family": "5G / Colocation", "tawal_contact": "C2", "effective_from": "2026-06-01", "enabled": True},
    ]
    with pytest.raises(ValueError, match="Overlapping"):
        validate({"family_tawal_defaults": rows})


def test_team_membership_rejects_invalid_calendar_date():
    with pytest.raises(ValueError, match="calendar date"):
        validate({"team_memberships": [{"id": "m", "team": "t", "employee": "E", "role": "leader",
                                         "effective_from": "2026-02-31", "enabled": True}]})
