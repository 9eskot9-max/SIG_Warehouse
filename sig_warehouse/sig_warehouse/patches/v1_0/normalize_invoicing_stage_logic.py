"""Keep stage-four evidence, SLA, and delay settings aligned with Invoicing."""

import frappe


SERVER_SCRIPT = "register_evidence_event"
SETTINGS = "SIG Field Ops Settings"
SLA_FIELD = "sla_asbuilt_days"  # Keep the saved fieldname; its visible label is now Invoicing.
OLD_LABEL = "As-Built SLA (days)"
NEW_LABEL = "Invoicing SLA (days)"


def _replace_once_or_already_updated(source, old, new, description):
    old_count = source.count(old)
    new_count = source.count(new)
    if old_count == 1 and new_count == 0:
        return source.replace(old, new, 1), True
    if old_count == 0 and new_count == 1:
        return source, False
    frappe.throw(
        "Cannot normalize Operations Invoicing logic: unexpected %s in %s."
        % (description, SERVER_SCRIPT)
    )


def _rewrite_evidence_writer(script):
    replacements = (
        ("if stage == '4 - As-Built':", "if stage == '4 - Invoicing':", "Stage 4 SLA branch"),
        ("'4 - As-Built': 'asbuilt'", "'4 - Invoicing': 'invoicing'", "Stage 4 delay-checkpoint mapping"),
        (
            "'initial\\nplan\\nhandover\\nasbuilt'",
            "'initial\\nplan\\nhandover\\ninvoicing'",
            "default delay-checkpoint list",
        ),
    )
    updated = False
    for old, new, description in replacements:
        script, changed = _replace_once_or_already_updated(script, old, new, description)
        updated = updated or changed
    return script, updated


def _normalize_delay_checkpoints(checkpoints):
    normalized = []
    changed = False
    for line in (checkpoints or "").replace(",", "\n").splitlines():
        token = line.strip()
        if token.lower() == "asbuilt":
            token = "invoicing"
            changed = True
        normalized.append(token)
    return "\n".join(normalized), changed


def _persist_delay_checkpoints(db, checkpoints):
    normalized, changed = _normalize_delay_checkpoints(checkpoints)
    if changed:
        db.set_single_value(SETTINGS, "delay_checkpoints", normalized)
    return normalized, changed


def _update_evidence_writer():
    if not frappe.db.exists("Server Script", SERVER_SCRIPT):
        frappe.throw("Cannot normalize Operations Invoicing logic: evidence writer is missing.")

    script = frappe.db.get_value("Server Script", SERVER_SCRIPT, "script") or ""
    script, updated = _rewrite_evidence_writer(script)
    if updated:
        frappe.db.set_value("Server Script", SERVER_SCRIPT, "script", script)


def _update_settings():
    if not frappe.db.exists("DocType", SETTINGS):
        frappe.throw("Cannot normalize Operations Invoicing settings: settings DocType is missing.")

    checkpoints = frappe.db.get_single_value(SETTINGS, "delay_checkpoints") or ""
    if checkpoints:
        _persist_delay_checkpoints(frappe.db, checkpoints)

    custom_field = frappe.db.get_value(
        "Custom Field", {"dt": SETTINGS, "fieldname": SLA_FIELD}, "name"
    )
    if custom_field:
        label = frappe.db.get_value("Custom Field", custom_field, "label") or ""
        if label == OLD_LABEL:
            frappe.db.set_value("Custom Field", custom_field, "label", NEW_LABEL)
        elif label != NEW_LABEL:
            frappe.throw("Cannot rename the existing Invoicing SLA field: its label changed unexpectedly.")
    else:
        settings_doctype = frappe.get_doc("DocType", SETTINGS)
        field = next((row for row in settings_doctype.fields if row.fieldname == SLA_FIELD), None)
        if not field:
            frappe.throw("Cannot rename the Invoicing SLA field: %s is missing." % SLA_FIELD)
        if field.label == OLD_LABEL:
            field.label = NEW_LABEL
            settings_doctype.save(ignore_permissions=True)
        elif field.label != NEW_LABEL:
            frappe.throw("Cannot rename the existing Invoicing SLA field: its label changed unexpectedly.")


def execute():
    """Preserve the existing SLA slot while using Invoicing stage terminology."""
    _update_evidence_writer()
    _update_settings()
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.clear_cache(doctype=SETTINGS)
