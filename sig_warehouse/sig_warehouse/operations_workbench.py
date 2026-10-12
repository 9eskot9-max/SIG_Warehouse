"""Permission-respecting operations dashboard read model and cycle close action."""
import json
from html import unescape
from html.parser import HTMLParser

import frappe

PAGE_SIZE = 500
MAX_ROWS = 20000
ROSTER = {
    "Capex": {"pm": ["Mohammed Sohail Mohammed Ilyas"], "co": ["Farooq Ansary", "Ghlzar Ahmad Fazal Malik"]},
    "Incident": {"pm": ["Abdulraheem Mohammed", "Mohammed Sohail Mohammed Ilyas"], "co": ["Arshad ahmed abdulhameed"]},
    "Colocation": {"pm": ["Mohammed Imran Ansary"], "co": ["Mohamed Walid Khalil Nmer Rahma", "Obed Sharrif"]},
}

class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.suppressed = [], 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "iframe", "object"):
            self.suppressed += 1
        elif tag.lower() in ("br", "p", "div", "li") and not self.suppressed:
            self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style", "iframe", "object") and self.suppressed:
            self.suppressed -= 1
        elif tag.lower() in ("p", "div", "li") and not self.suppressed:
            self.parts.append(" ")
    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)

def _plain_text(value):
    parser = _PlainText(); parser.feed(str(value or ""))
    return " ".join(unescape("".join(parser.parts)).split())

def _all_visible(doctype, fields, filters=None, order_by=None, max_rows=MAX_ROWS):
    rows, start = [], 0
    while start < max_rows:
        limit = min(PAGE_SIZE, max_rows - start)
        batch = frappe.get_list(doctype, filters=filters or {}, fields=fields,
                                order_by=order_by or "name asc", start=start, page_length=limit)
        rows.extend(batch)
        if len(batch) < limit:
            return rows, True
        start += len(batch)
    return rows, False

def _flag(row, field):
    return row.get(field) in (1, True, "1", "Yes", "yes")

def _family(value):
    normalized = str(value or "").strip().lower()
    if normalized in ("5g", "colocation", "colo"):
        return "Colocation"
    if normalized == "capex":
        return "Capex"
    if normalized == "incident":
        return "Incident"
    return ""

def _cycle_view(row, project, today):
    """Derive display-stage from source events, avoiding stale projected stage labels."""
    closed = _flag(row, "terminal")
    has_prep = bool(row.get("mapping_at") or row.get("boq_at") or row.get("pimp_at")
                    or row.get("tcn_at") or row.get("mir_at") or row.get("first_visit_at"))
    prepared = bool(row.get("tcn_at") and row.get("mir_at") and row.get("first_visit_at"))
    handover_done = bool(row.get("tags_at") and row.get("photos_at") and row.get("asbuilt_at"))
    if closed:
        stage = "Closed"
    elif prepared and not handover_done:
        stage = "Handover"
    elif prepared and handover_done:
        stage = "Completion documents"
    elif has_prep:
        stage = "Preparation"
    else:
        stage = "Scope & readiness"
    work = []
    family = _family(project.get("custom_family") if project else "")
    people = ROSTER.get(family, {"pm": [], "co": []})
    if not closed and (row.get("mapping_at") or row.get("boq_at") or row.get("pimp_at")):
        for key, label, field, role in (
            ("tcn", "TCN / MDT", "tcn_at", "co"),
            ("mir", "MIR", "mir_at", "co"),
            ("visit", "Visit", "first_visit_at", "pm"),
        ):
            if not row.get(field):
                work.append({"key": key, "label": label, "owner_role": role,
                             "owners": people[role], "closes_on": label + " evidence"})
    if not closed and prepared:
        for key, label, field, role in (
            ("tags", "Tags", "tags_at", "co"),
            ("photos", "Photos", "photos_at", "co"),
            ("asbuilt", "As-Built BOQ file", "asbuilt_at", "pm"),
        ):
            if not row.get(field):
                work.append({"key": key, "label": label, "owner_role": role,
                             "owners": people[role], "closes_on": label + " evidence"})
    for item in work:
        item["shared"] = True
    delay = _flag(row, "is_delayed") or _flag(row, "is_aged") or bool(row.get("stage_due_on") and str(row.stage_due_on)[:10] < today)
    return {
        "name": row.name, "site": str(row.get("site_key") or row.get("site") or row.name),
        "project": str((project or {}).get("project_name") or row.get("project") or ""),
        "project_id": str((project or {}).get("name") or row.get("erp_project") or ""),
        "family": family, "stage": stage, "legacy_stage": str(row.get("stage") or ""),
        "terminal": closed, "closed_on": str(row.get("closed_on") or ""),
        "closed_by": str(row.get("closed_by") or ""),
        "delay_reason": str(row.get("delay_reason") or ""),
        "delay_note": str(row.get("delay_note") or ""),
        "stage_due_on": str(row.get("stage_due_on") or ""),
        "last_event_at": str(row.get("last_event_at") or ""),
        "is_delayed": _flag(row, "is_delayed"), "is_aged": _flag(row, "is_aged"),
        "past_due": bool(row.get("stage_due_on") and str(row.stage_due_on)[:10] < today),
        "needs_review": bool(delay and not closed), "work": work,
        "people": {"pm": people["pm"], "co": people["co"]},
        "events": {key: str(row.get(key) or "") for key in (
            "mapping_at", "boq_at", "tcn_at", "mir_at", "first_visit_at",
            "tags_at", "photos_at", "asbuilt_at", "warranty_at", "ho_at")},
    }

@frappe.whitelist()
def get_overview():
    """Read current ToDos, evidence-derived pipeline work and authorized cycles."""
    result = {"todos": [], "cycles": [], "projects": [],
              "roster": ROSTER,
              "summary": {"todos": 0, "overdue_todos": 0, "cycles": 0, "delayed": 0,
                          "aged": 0, "past_due": 0, "closed": 0, "exceptions": 0,
                          "stages": {}},
              "complete": {"todos": True, "cycles": True},
              "can_close_cycles": False, "person": frappe.session.user}
    user, today = frappe.session.user, frappe.utils.nowdate()
    roles = set(frappe.get_roles(user))
    result["can_close_cycles"] = bool(roles.intersection(
        {"SIG Field Ops", "System Manager", "Projects Manager", "Projects User"}))
    if frappe.has_permission("ToDo", "read"):
        todos, result["complete"]["todos"] = _all_visible(
            "ToDo", ["name", "description", "date", "status", "reference_type", "reference_name", "allocated_to"],
            filters={"allocated_to": user, "status": ["not in", ["Closed", "Cancelled"]]},
            order_by="date asc, modified desc", max_rows=5000)
        result["summary"]["todos"] = len(todos)
        result["summary"]["overdue_todos"] = sum(1 for row in todos if row.get("date") and str(row.date) < today)
        result["todos"] = [{**row, "description": _plain_text(row.get("description"))} for row in todos[:50]]
    if not frappe.has_permission("SIG Site Cycle", "read"):
        return result
    fields = ["name", "site", "site_key", "project", "erp_project", "stage", "stage_due_on", "terminal",
              "closed_on", "closed_by", "is_delayed", "is_aged", "delay_reason", "delay_note", "last_event_at",
              "mapping_at", "boq_at", "pimp_at", "tcn_at", "mir_at", "first_visit_at", "tags_at", "photos_at",
              "asbuilt_at", "warranty_at", "ho_at"]
    rows, result["complete"]["cycles"] = _all_visible(
        "SIG Site Cycle", fields, order_by="terminal asc, stage_due_on asc, last_event_at desc")
    projects_by_name = {}
    project_names = sorted({str(r.get("erp_project")) for r in rows if r.get("erp_project")})
    if project_names and frappe.has_permission("Project", "read"):
        projects, _ = _all_visible("Project", ["name", "project_name", "status", "custom_family"],
                                   filters={"name": ["in", project_names]}, order_by="project_name asc")
        projects_by_name = {p.name: p for p in projects}
    counts = result["summary"]
    for row in rows:
        project = projects_by_name.get(str(row.get("erp_project") or ""))
        cycle = _cycle_view(row, project, today)
        result["cycles"].append(cycle)
        if cycle["terminal"]:
            counts["closed"] += 1
        else:
            counts["cycles"] += 1
            counts["delayed"] += int(cycle["is_delayed"])
            counts["aged"] += int(cycle["is_aged"])
            counts["past_due"] += int(cycle["past_due"])
            counts["exceptions"] += int(cycle["needs_review"])
        counts["stages"][cycle["stage"]] = counts["stages"].get(cycle["stage"], 0) + 1
    result["cycles"].sort(key=lambda r: (r["terminal"], not r["needs_review"], r["stage_due_on"] or "9999-12-31", r["site"].lower()))
    return result

@frappe.whitelist()
def close_cycles(cycles, reason):
    """Write explicit SITE_CLOSED evidence for selected cycles after role and permission checks."""
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    if user == "Guest" or not roles.intersection(
            {"SIG Field Ops", "System Manager", "Projects Manager", "Projects User"}):
        frappe.throw("Only Field Ops users may close site cycles.", frappe.PermissionError)
    try:
        names = cycles if isinstance(cycles, list) else json.loads(cycles or "[]")
    except Exception:
        frappe.throw("Invalid cycle selection.")
    names = list(dict.fromkeys(str(n).strip() for n in names if str(n).strip()))
    reason = str(reason or "").strip().replace("|", "/")
    if not names or len(names) > 50 or not reason or len(reason) > 500:
        frappe.throw("Select 1–50 cycles and enter a closure reason up to 500 characters.")
    if not frappe.has_permission("SIG Site Cycle", "write") or not frappe.has_permission("SIG Evidence Event", "create"):
        frappe.throw("Your role cannot close cycles or record closure evidence.", frappe.PermissionError)
    docs = []
    for name in names:
        if not frappe.db.exists("SIG Site Cycle", name):
            frappe.throw("A selected site cycle no longer exists. Refresh and review the selection.")
        if not frappe.has_permission("SIG Site Cycle", "write", name):
            frappe.throw("You cannot close every selected cycle. No changes were made.", frappe.PermissionError)
        doc = frappe.get_doc("SIG Site Cycle", name)
        if _flag(doc, "terminal"):
            continue
        docs.append(doc)
    now = frappe.utils.now()
    stamp = now.replace("-", "").replace(" ", "").replace(":", "")
    safe_user = user.replace("@", "_").replace(".", "_")
    batch = "MANUAL-" + safe_user + "-" + stamp
    closed = []
    for seq, cycle in enumerate(docs, start=1):
        cycle.terminal = 1
        cycle.closed_on = now[:10]
        cycle.closed_by = user
        cycle.stage = "5 - Closed"
        cycle.stage_anchor_at = None
        cycle.stage_due_on = None
        cycle.is_delayed = 0
        cycle.last_event_at = now
        cycle.last_event_code = "SITE_CLOSED"
        cycle.save()
        event_id = batch + "-" + str(seq).zfill(6)
        event = frappe.get_doc({
            "doctype": "SIG Evidence Event", "event_id": event_id,
            "schema_version": "EV1", "event_code": "SITE_CLOSED",
            "occurred_at": now, "recorded_at": now, "site_id": cycle.site_id,
            "site_key": cycle.site_key, "project": cycle.project, "po": cycle.po,
            "wo": cycle.wo, "artifact_ref": "MANUAL_CLOSE|" + user + "|" + now + "|" + reason,
            "batch_id": batch, "seq": seq, "source_sub": "operations_workbench",
            "source_workbook": "ERP", "operator": user, "machine": "neosys",
            "core_version": "erp", "cycle": cycle.name,
        })
        event.insert()
        closed.append(cycle.name)
    return {"result": "ok", "closed": closed, "already_closed": len(names) - len(docs),
            "batch": batch, "operator": user, "reason": reason}

