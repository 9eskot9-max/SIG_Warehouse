"""Park reviewed active-work cycles that were historically marked closed."""

import json
from pathlib import Path

import frappe

from sig_warehouse.sig_warehouse.legacy_cycle_parking import parked_values, validate


MANIFEST = Path(__file__).with_suffix(".json")


def execute():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cycle_fields = [
        "name", "modified", "terminal", "site_key", "po", "wo", "sig_lifecycle",
        "sig_parked_at", "sig_parked_by", "sig_park_reason",
    ]
    cycles = frappe.get_all("SIG Site Cycle", fields=cycle_fields, limit_page_length=0)
    by_name = {row["name"]: row for row in cycles}
    selected_names = [row["name"] for row in manifest]
    already_parked = [
        row for name in selected_names if (row := by_name.get(name))
        and not row["terminal"] and row["sig_lifecycle"] == "Parked"
        and row["sig_parked_at"] and row["sig_parked_by"] and row["sig_park_reason"] == (
            "Legacy in-progress work; original closure retained in history."
        )
    ]
    if len(already_parked) == len(manifest):
        return
    if already_parked:
        frappe.throw("Legacy cycle conversion is partial; no records were changed.")

    event_names = [row["closure_event"] for row in manifest]
    events = frappe.get_all(
        "SIG Evidence Event",
        filters={"name": ["in", event_names]},
        fields=["name", "event_code", "cycle"],
        limit_page_length=0,
    )
    errors = validate(manifest, cycles, events, expected_count=136)
    if errors:
        frappe.throw("Legacy cycle conversion preflight failed: " + json.dumps(errors[:20], default=str))

    actor = getattr(frappe.session, "user", None) or "Administrator"
    if not frappe.db.exists("User", actor):
        actor = "Administrator"
    values = parked_values(actor=actor, parked_at=frappe.utils.now_datetime())
    for item in manifest:
        frappe.db.set_value("SIG Site Cycle", item["name"], values, update_modified=True)
