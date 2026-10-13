"""Repair delay configuration/flags after the initial Invoicing config patch."""

import frappe


SETTINGS = "SIG Field Ops Settings"
CANONICAL_CHECKPOINTS = "initial\nplan\nhandover\ninvoicing"

# These cycles had is_delayed=1 in the pre-rename backup. The first settings
# migration accidentally cleared the flags while writing the checkpoint string.
PREVIOUSLY_DELAYED_CYCLES = (
    "HAL0087|NA|20260727",
    "RIY2094|NA|20260910",
    "RIY2185|NA|20260912",
    "Z95004|NA|20260914",
    "Z95004|WO-SIG-DC-Z95004-12740-Capex#9-19130|20260906",
    "ZBH739|NA|20260728",
    "ZBH747|NA|20260727",
    "ZBH874|NA|20260726",
    "ZBH874|WO-SIG-IMP-ZBH739-11340-Incident-23574|20260823",
    "ZBH915|NA|20260727",
    "ZBR135|NA|20260805",
    "ZBR135|WO-SIG-IMP-ZBR135-11340-Incident-27696|20260922",
    "ZDU004|NA|20260915",
    "ZHA899|WO-SIG-IMP-ZHA899-11340-Incident-23578|20260727",
    "ZJD134|10001274|20260726",
    "ZJZ054|NA|20260914",
    "ZJZ060|NA|20260914",
    "ZJZ154|NA|20260724",
    "ZJZ184|NA|20260914",
    "ZJZ187|NA|20260724",
    "ZJZ317|NA|20260914",
    "ZJZ414|NA|20260727",
    "ZJZ574|NA|20260914",
    "ZJZ713|NA|20260727",
    "ZJZ739|NA|20260914",
    "ZMC084|NA|20260724",
    "ZNJ104|WO-SIG-IMP-ZNJ104-11340-Incident-23580|20260726",
    "ZNJ621|NA|20260914",
    "ZRW914|10001134|20260828",
    "ZTF346|NA|20260914",
    "ZTF454|NA|20260914",
)


def _checkpoint_value(value):
    """Normalize the old token, or recover the known interleaved-string defect."""
    current = str(value or "")
    tokens = [line.strip() for line in current.replace(",", "\n").splitlines() if line.strip()]
    if (len(tokens) > 20 and all(len(token) == 1 for token in tokens)
            and "".join(tokens).lower() == "initialplanhandoverinvoicing"):
        return CANONICAL_CHECKPOINTS, True

    normalized = ["invoicing" if token.lower() == "asbuilt" else token for token in tokens]
    result = "\n".join(normalized)
    return result, result != current


def _restore_delay_checkpoints():
    current = frappe.db.get_single_value(SETTINGS, "delay_checkpoints") or ""
    normalized, changed = _checkpoint_value(current)
    if changed:
        frappe.db.set_single_value(SETTINGS, "delay_checkpoints", normalized)
    return changed


def _restore_delayed_flags():
    today = frappe.utils.nowdate()
    restored = 0
    for name in PREVIOUSLY_DELAYED_CYCLES:
        if not frappe.db.exists("SIG Site Cycle", name):
            continue
        row = frappe.db.get_value(
            "SIG Site Cycle", name, ["stage", "terminal", "stage_due_on", "is_delayed"], as_dict=True
        )
        if (row and row.stage == "4 - Invoicing" and not row.terminal
                and row.stage_due_on and str(row.stage_due_on)[:10] < today
                and not row.is_delayed):
            frappe.db.set_value("SIG Site Cycle", name, "is_delayed", 1, update_modified=False)
            restored += 1
    return restored


def execute():
    """Restore the approved checkpoint list and prior overdue flags idempotently."""
    config_changed = _restore_delay_checkpoints()
    flags_restored = _restore_delayed_flags()
    frappe.clear_cache(doctype=SETTINGS)
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.logger("sig_warehouse").info(
        "Repaired Invoicing delay state; config_changed=%s delayed_flags_restored=%s",
        config_changed, flags_restored,
    )
