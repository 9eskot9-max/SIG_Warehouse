"""Preview and reconcile the complete reviewed RV80 critical-site code list."""

import hashlib
import json
import re

import frappe


MAX_CODES = 10000


def _normalize(code):
    return str(code or "").replace("\u00a0", " ").strip().upper()


def _require_access():
    if frappe.session.user == "Guest" or "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Only a System Manager can reconcile critical sites.", frappe.PermissionError)
    if not frappe.has_permission("SIG Site", "read") or not frappe.has_permission("SIG Site", "write"):
        frappe.throw("SIG Site read and write access is required.", frappe.PermissionError)
    if not frappe.get_meta("SIG Site").has_field("planner_critical_status"):
        frappe.throw("Critical-site fields are not installed. Run the Field Planner migration first.")


def _parse(codes, source):
    values = json.loads(codes) if isinstance(codes, str) else codes
    if not isinstance(values, list) or not values or len(values) > MAX_CODES:
        frappe.throw("Provide a complete, non-empty RV80 critical-site list of at most 10,000 codes.")
    normalized = [_normalize(code) for code in values]
    if any(not code for code in normalized):
        frappe.throw("The RV80 critical-site list contains a blank code.")
    if any(not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,139}", code) for code in normalized):
        frappe.throw("The RV80 critical-site list contains an invalid site code.")
    codes = sorted(set(normalized))
    source = str(source or "").strip()
    if not source or len(source) > 140:
        frappe.throw("Identify the reviewed RV80 critical-site list and its source date.")
    return codes, source


def _make_plan(codes, source):
    # Read all rows for this admin-only operation so a User Permission filter
    # cannot make an incomplete subset look like the complete site master.
    rows = frappe.get_all(
        "SIG Site",
        fields=["name", "site_id", "planner_critical_status", "planner_critical_source"],
        limit_page_length=0,
    )
    index = {}
    for row in rows:
        code = _normalize(row.get("site_id"))
        if code:
            index.setdefault(code, []).append(row)

    matched, unmatched, ambiguous = {}, [], {}
    for code in codes:
        matches = index.get(code, [])
        if len(matches) == 1:
            matched[code] = matches[0]
        elif not matches:
            unmatched.append(code)
        else:
            ambiguous[code] = [row.name for row in matches]

    incoming = set(codes)
    current_critical = [row for row in rows if row.get("planner_critical_status") == "Critical"]
    to_clear = [row for row in current_critical if _normalize(row.get("site_id")) not in incoming]
    to_update = [row for row in matched.values() if (
        row.get("planner_critical_status") != "Critical" or row.get("planner_critical_source") != source
    )]
    state = sorted(
        (str(row.name), _normalize(row.get("site_id")), row.get("planner_critical_status") or "",
         row.get("planner_critical_source") or "")
        for row in current_critical + to_update
    )
    token_payload = json.dumps(
        {"codes": codes, "source": source, "state": state},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    confirmation_token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()
    return {
        "matched": matched,
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "to_update": to_update,
        "to_clear": to_clear,
        "confirmation_token": confirmation_token,
    }


@frappe.whitelist(methods=["POST"])
def preview_rv80_critical_sites(codes, source):
    """Return an exact add/clear preview; do not change any ERP records."""
    _require_access()
    codes, source = _parse(codes, source)
    plan = _make_plan(codes, source)
    return {
        "result": "preview",
        "requested": len(codes),
        "matched": len(plan["matched"]),
        "unmatched": plan["unmatched"],
        "ambiguous": plan["ambiguous"],
        "to_mark_critical": len(plan["to_update"]),
        "to_clear_critical": len(plan["to_clear"]),
        "confirmation_token": plan["confirmation_token"],
    }


@frappe.whitelist(methods=["POST"])
def apply_rv80_critical_sites(codes, source, confirmation_token):
    """Apply a confirmed full-list reconciliation by exact SIG Site.site_id."""
    _require_access()
    codes, source = _parse(codes, source)
    plan = _make_plan(codes, source)
    if plan["unmatched"] or plan["ambiguous"]:
        frappe.throw("Resolve every unmatched or ambiguous site code before applying the critical list.")
    if str(confirmation_token or "") != plan["confirmation_token"]:
        frappe.throw("The site master or critical list changed after preview. Preview the reconciliation again.")

    changed_rows = plan["to_update"] + plan["to_clear"]
    denied = [row.name for row in changed_rows if not frappe.has_permission("SIG Site", "write", row.name)]
    if denied:
        frappe.throw("Write access is missing for one or more sites: {0}".format(", ".join(denied[:10])), frappe.PermissionError)

    for row in plan["to_update"]:
        doc = frappe.get_doc("SIG Site", row.name)
        doc.set("planner_critical_status", "Critical")
        doc.set("planner_critical_source", source)
        doc.save()
    for row in plan["to_clear"]:
        doc = frappe.get_doc("SIG Site", row.name)
        doc.set("planner_critical_status", "Unknown")
        doc.set("planner_critical_source", source)
        doc.save()

    changed_names = [row.name for row in changed_rows]
    if changed_names:
        readback = frappe.get_all(
            "SIG Site",
            filters={"name": ["in", changed_names]},
            fields=["name", "site_id", "planner_critical_status", "planner_critical_source"],
            limit_page_length=0,
        )
        verified = {row.name: row for row in readback}
        for row in plan["to_update"]:
            actual = verified.get(row.name)
            if not actual or actual.planner_critical_status != "Critical" or actual.planner_critical_source != source:
                frappe.throw("Critical-site read-back failed for {0}.".format(row.site_id))
        for row in plan["to_clear"]:
            actual = verified.get(row.name)
            if not actual or actual.planner_critical_status != "Unknown" or actual.planner_critical_source != source:
                frappe.throw("Critical-site clear read-back failed for {0}.".format(row.site_id))

    frappe.clear_cache(doctype="SIG Site")
    return {
        "result": "ok",
        "applied": True,
        "requested": len(codes),
        "marked_critical": len(plan["to_update"]),
        "cleared_critical": len(plan["to_clear"]),
        "unchanged": len(codes) - len(plan["to_update"]),
        "readback_ok": True,
    }
