"""Permission-respecting operations dashboard read model and cycle close action."""
import json
from io import BytesIO
from html import unescape
from html.parser import HTMLParser

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

import frappe

PAGE_SIZE = 500
MAX_ROWS = 20000
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
    if not closed and (row.get("mapping_at") or row.get("boq_at") or row.get("pimp_at")):
        for key, label, field, role in (
            ("tcn", "TCN / MDT", "tcn_at", "co"),
            ("mir", "MIR", "mir_at", "co"),
            ("visit", "Visit", "first_visit_at", "pm"),
        ):
            if not row.get(field):
                work.append({"key": key, "label": label, "owner_role": role,
                             "closes_on": label + " evidence"})
    if not closed and prepared:
        for key, label, field, role in (
            ("tags", "Tags", "tags_at", "co"),
            ("photos", "Photos", "photos_at", "co"),
            ("asbuilt", "As-Built BOQ file", "asbuilt_at", "pm"),
        ):
            if not row.get(field):
                work.append({"key": key, "label": label, "owner_role": role,
                             "closes_on": label + " evidence"})
    for item in work:
        item["shared"] = True
    delay = _flag(row, "is_delayed") or _flag(row, "is_aged") or bool(row.get("stage_due_on") and str(row.stage_due_on)[:10] < today)
    return {
        "name": row.name, "site": str(row.get("site_key") or row.get("site") or row.name),
        "project": str((project or {}).get("project_name") or row.get("project") or ""),
        "project_id": str((project or {}).get("name") or row.get("erp_project") or ""),
        "ba": str((project or {}).get("custom_agreement_no") or row.get("po") or ""),
        "alias": str(row.get("project_alias") or ""), "wo": str(row.get("wo") or ""),
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
        "events": {key: str(row.get(key) or "") for key in (
            "mapping_at", "boq_at", "tcn_at", "mir_at", "first_visit_at",
            "tags_at", "photos_at", "asbuilt_at", "warranty_at", "ho_at")},
    }

@frappe.whitelist()
def get_overview():
    """Read current ToDos, evidence-derived pipeline work and authorized cycles."""
    result = {"todos": [], "cycles": [], "projects": [],
                    "summary": {"todos": 0, "overdue_todos": 0, "cycles": 0, "delayed": 0,
                          "aged": 0, "past_due": 0, "closed": 0, "exceptions": 0,
                          "stages": {}},
              "complete": {"todos": True, "cycles": True}, "todo_access": False,
              "can_close_cycles": False, "todo_create": False, "person": frappe.session.user}
    user, today = frappe.session.user, frappe.utils.nowdate()
    roles = set(frappe.get_roles(user))
    result["can_close_cycles"] = bool(roles.intersection(
        {"SIG Field Ops", "System Manager", "Projects Manager", "Projects User"}))
    todos = []
    result["todo_create"] = bool(frappe.has_permission("ToDo", "create"))
    if frappe.has_permission("ToDo", "read"):
        result["todo_access"] = True
        todos, result["complete"]["todos"] = _all_visible(
            "ToDo", ["name", "description", "date", "status", "reference_type", "reference_name", "allocated_to"],
            filters={"allocated_to": user, "status": ["not in", ["Closed", "Cancelled"]]},
            order_by="date asc, modified desc", max_rows=5000)
        result["summary"]["todos"] = len(todos)
        result["summary"]["overdue_todos"] = sum(1 for row in todos if row.get("date") and str(row.date) < today)
        result["todos"] = [{**row, "description": _plain_text(row.get("description"))} for row in todos[:50]]
    if not frappe.has_permission("SIG Site Cycle", "read"):
        return result
    fields = ["name", "site", "site_key", "project", "erp_project", "project_stream", "po", "wo", "stage", "stage_due_on", "terminal",
              "closed_on", "closed_by", "is_delayed", "is_aged", "delay_reason", "delay_note", "last_event_at",
              "mapping_at", "boq_at", "pimp_at", "tcn_at", "mir_at", "first_visit_at", "tags_at", "photos_at",
              "asbuilt_at", "warranty_at", "ho_at"]
    rows, result["complete"]["cycles"] = _all_visible(
        "SIG Site Cycle", fields, order_by="terminal asc, stage_due_on asc, last_event_at desc")
    projects_by_name = {}
    project_names = sorted({str(r.get("erp_project")) for r in rows if r.get("erp_project")})
    if project_names and frappe.has_permission("Project", "read"):
        projects, _ = _all_visible("Project", ["name", "project_name", "status", "custom_family", "custom_agreement_no"],
                                   filters={"name": ["in", project_names]}, order_by="project_name asc")
        projects_by_name = {p.name: p for p in projects}
    aliases_by_stream = {}
    stream_names = sorted({str(r.get("project_stream")) for r in rows if r.get("project_stream")})
    if stream_names and frappe.db.exists("DocType", "SIG Project Stream") and frappe.has_permission("SIG Project Stream", "read"):
        streams, _ = _all_visible("SIG Project Stream", ["name", "alias"],
                                  filters={"name": ["in", stream_names]}, max_rows=5000)
        aliases_by_stream = {str(stream.name): str(stream.get("alias") or "") for stream in streams}
    counts = result["summary"]
    for row in rows:
        project_key = str(row.get("erp_project") or "")
        project = projects_by_name.get(project_key)
        row["project_alias"] = aliases_by_stream.get(str(row.get("project_stream") or ""), "")
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
    result["todos_has_more"] = len(todos) > len(result["todos"]) if result["todo_access"] else False
    return result

@frappe.whitelist()
def export_workbook(filter="open"):
    """Download all permission-visible cycles and their evidence-derived stage milestones."""
    if not frappe.has_permission("SIG Site Cycle", "read") or not frappe.has_permission("SIG Site Cycle", "export"):
        frappe.throw("You need SIG Site Cycle read and export permission to download this workbook.",
                     frappe.PermissionError)
    data = get_overview()
    if not data.get("complete", {}).get("cycles"):
        frappe.throw("The visible cycle read reached its safety limit. Refine the source data before exporting.")
    cycles = list(data.get("cycles") or [])
    if filter == "review":
        cycles = [c for c in cycles if c.get("needs_review")]
    elif filter.startswith("stage:"):
        cycles = [c for c in cycles if c.get("stage") == filter[6:]]
    else:
        cycles = [c for c in cycles if not c.get("terminal")]

    wb = Workbook()
    ws = wb.active
    ws.title = "Cycles"
    headers = ["Cycle ID", "Site", "WO", "BA", "Project alias", "ERP Project", "Scope",
               "Stage", "Status", "Pending work", "Review due", "Delayed", "Aged",
               "Due date", "Delay reason", "Delay note", "Closed on", "Closed by",
               "Mapping at", "BOQ at", "TCN at", "MIR at", "Visit at",
               "Tags at", "Photos at", "As-Built BOQ at", "Warranty at", "Handover at"]
    ws.append(headers)
    stage_ws = wb.create_sheet("Stage tasks")
    stage_ws.append(["Cycle ID", "Site", "WO", "BA", "Project alias", "Stage",
                     "Task", "Role", "Status", "Evidence recorded at"])
    specs = [
        ("mapping", "Mapping / BOQ", "Scope", "either", ("mapping_at", "boq_at")),
        ("tcn", "TCN / MDT", "Preparation", "co", ("tcn_at",)),
        ("mir", "MIR", "Preparation", "co", ("mir_at",)),
        ("visit", "Visit", "Preparation", "pm", ("first_visit_at",)),
        ("tags", "Tags", "Handover", "co", ("tags_at",)),
        ("photos", "Photos", "Handover", "co", ("photos_at",)),
        ("asbuilt", "As-Built BOQ file", "Handover", "pm", ("asbuilt_at",)),
        ("warranty", "Warranty", "Completion documents", "co", ("warranty_at",)),
        ("handover", "Handover documents", "Completion documents", "either", ("ho_at",)),
        ("rfi", "RFI", "Completion documents", "pm", ()),
    ]
    for cycle in cycles:
        events = cycle.get("events") or {}
        pending = {w.get("key") for w in cycle.get("work") or []}
        ws.append([cycle.get("name"), cycle.get("site"), cycle.get("wo"), cycle.get("ba"),
                   cycle.get("alias"), cycle.get("project_id"), cycle.get("family"),
                   cycle.get("stage"), "Closed" if cycle.get("terminal") else "Open",
                   "; ".join(w.get("label", "") for w in cycle.get("work") or []),
                   bool(cycle.get("needs_review")), bool(cycle.get("is_delayed")), bool(cycle.get("is_aged")),
                   cycle.get("stage_due_on"), cycle.get("delay_reason"), cycle.get("delay_note"),
                   cycle.get("closed_on"), cycle.get("closed_by")] +
                  [events.get(field) for field in ("mapping_at", "boq_at", "tcn_at", "mir_at",
                   "first_visit_at", "tags_at", "photos_at", "asbuilt_at", "warranty_at", "ho_at")])
        for key, label, stage, role, fields in specs:
            recorded = next((events.get(field) for field in fields if events.get(field)), "")
            if recorded:
                status = "Complete · evidence"
            elif not fields:
                status = "Not projected · evidence source not wired"
            elif key in pending:
                status = "Pending evidence"
            else:
                status = "Not yet open / not applicable"
            stage_ws.append([cycle.get("name"), cycle.get("site"), cycle.get("wo"), cycle.get("ba"),
                             cycle.get("alias"), stage, label, role, status, recorded])
    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="173F62")
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = min(42, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
    output = BytesIO()
    wb.save(output)
    frappe.local.response.filename = "operations-cycle-stage.xlsx"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "download"

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

