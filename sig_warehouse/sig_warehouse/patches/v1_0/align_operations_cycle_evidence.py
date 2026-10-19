"""Align evidence intake, daily flags and existing open cycles without altering evidence."""
import inspect

import frappe

from sig_warehouse.sig_warehouse.cycle_rules import derive_cycle_state


MARKER = "    # SIG canonical cycle rules v2\n"


def rewrite_evidence_writer(source):
    end = "    cycdoc.set('stage', stage)"
    start = MARKER if MARKER in source else "    stage = '1 - Initial'\n"
    if source.count(start) != 1 or source.count(end) != 1:
        frappe.throw("Cycle evidence migration stopped: stage block is not recognized.")
    before, rest = source.split(start, 1)
    old, after = rest.split(end, 1)
    if start != MARKER and ("stage = '4 - Invoicing'" not in old or "stage = '3 - Handover'" not in old):
        frappe.throw("Cycle evidence migration stopped: unexpected existing stage rules.")
    # Use exactly the same function body as the app read model. No sandbox
    # imports, callbacks or duplicated condition tree are needed.
    lines = inspect.getsource(derive_cycle_state).splitlines()[1:]
    if lines[-1].strip() != "return stage, anchor":
        frappe.throw("Cycle evidence migration stopped: canonical return contract changed.")
    body = "\n".join(lines[:-1]).replace("row.get(", "sig_rule_row.get(") + "\n"
    context = (
        "    sig_rule_row = cycdoc.as_dict()\n"
        "    if int(cycdoc.get('sessions_completed') or 0) + int(cycdoc.get('sessions_auto_closed') or 0) >= 2:\n"
        "        sig_rule_visits = frappe.get_all('SIG Field Visit',\n"
        "            filters={'cycle': cyc, 'status': ['in', ['COMPLETED', 'AUTO_CLOSED']]},\n"
        "            fields=['start_at'], order_by='start_at asc, name asc', limit_page_length=2)\n"
        "        if len(sig_rule_visits) == 2:\n"
        "            sig_rule_row['second_visit_at'] = sig_rule_visits[1].start_at\n"
    )
    fallback = "    if not anchor and stage != '5 - Closed':\n        anchor = occurred\n"
    return before + MARKER + context + body + fallback + end + after


def rewrite_daily_flags(source):
    if "stage_checkpoint =" not in source or "'3 - Handover': 'handover'" not in source:
        frappe.throw("Cycle evidence migration stopped: daily flag writer is not recognized.")
    return source.replace("'4 - As-Built': 'asbuilt'", "'4 - Invoicing': 'invoicing'").replace(
        "initial\\nplan\\nhandover\\nasbuilt", "initial\\nplan\\nhandover\\ninvoicing")


def reconcile_open_cycles():
    fields = ["name", "stage", "terminal", "mapping_at", "boq_at", "pimp_at", "tcn_at", "mir_at",
              "first_visit_at", "last_visit_at", "tags_at", "photos_at", "warranty_at", "asbuilt_at",
              "ho_at", "invoice_at", "sessions_completed", "sessions_auto_closed", "last_event_at",
              "stage_anchor_at", "stage_due_on", "is_delayed", "is_aged"]
    rows = frappe.get_all("SIG Site Cycle", filters={"terminal": 0}, fields=fields, limit_page_length=0)
    second_visits = {}
    seen = set()
    if rows:
        visits = frappe.get_all("SIG Field Visit", filters={"cycle": ["in", [r.name for r in rows]],
                               "status": ["in", ["COMPLETED", "AUTO_CLOSED"]]},
                                fields=["name", "cycle", "start_at"],
                                order_by="start_at asc, name asc", limit_page_length=0)
        for visit in visits:
            if visit.cycle in seen:
                second_visits.setdefault(visit.cycle, visit.start_at)
            seen.add(visit.cycle)
    settings = frappe.get_single("SIG Field Ops Settings")
    today = frappe.utils.nowdate()
    checkpoint_value = str(settings.get("delay_checkpoints") or "initial\nplan\nhandover\ninvoicing")
    checkpoints = {s.strip().lower().replace("asbuilt", "invoicing")
                   for s in checkpoint_value.replace(",", "\n").splitlines() if s.strip()}
    stage_keys = {"1 - Initial": "initial", "2 - Plan": "plan", "3 - Handover": "handover", "4 - Invoicing": "invoicing"}
    sla_fields = {"1 - Initial": "sla_stage1_days", "2 - Plan": "sla_plan_days",
                  "3 - Handover": "sla_handover_days", "4 - Invoicing": "sla_asbuilt_days"}
    changed = 0
    for row in rows:
        row["second_visit_at"] = second_visits.get(row.name)
        stage, anchor = derive_cycle_state(row)
        anchor = anchor or row.get("stage_anchor_at")
        sla = settings.get(sla_fields[stage]) or (30 if stage == "1 - Initial" else settings.get("sla_standard_days") or 14)
        due = frappe.utils.add_days(str(anchor)[:10], sla) if anchor else None
        values = {"stage": stage, "stage_anchor_at": anchor, "stage_due_on": due,
                  "is_delayed": int(bool(stage_keys[stage] in checkpoints and due and str(due)[:10] < today)),
                  "is_aged": int(bool(anchor and frappe.utils.date_diff(today, str(anchor)[:10]) > (settings.get("aged_days") or 30)))}
        if any(str(row.get(key) or "") != str(value or "") for key, value in values.items()):
            frappe.db.set_value("SIG Site Cycle", row.name, values, update_modified=False)
            changed += 1
    return changed


def execute():
    # Validate both scripts before making any writes. The migration transaction
    # rolls back all changes if a later reconciliation step fails.
    updates = {}
    for name, rewrite in (("register_evidence_event", rewrite_evidence_writer),
                          ("sig_field_ops_daily", rewrite_daily_flags)):
        if not frappe.db.exists("Server Script", name):
            frappe.throw("Cycle evidence migration stopped: required Server Script is missing.")
        source = frappe.db.get_value("Server Script", name, "script") or ""
        updates[name] = rewrite(source)
    for name, source in updates.items():
        frappe.db.set_value("Server Script", name, "script", source)
    count = reconcile_open_cycles()
    frappe.clear_cache(doctype="SIG Site Cycle")
    frappe.logger("sig_warehouse").info("Canonical Operations evidence rules applied; open cycles updated=%s", count)
