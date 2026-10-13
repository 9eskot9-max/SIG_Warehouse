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

# Owner-confirmed Operations routing. Employee.user_id resolves the opener to
# this allowlisted roster; these names do not grant access to a Site Cycle.
OPS_ROSTER = {
    "Capex": {
        "pm": ("Mohammed Sohail Mohammed Ilyas",),
        "co": ("Ghlzar Ahmad Fazal Malik",),
    },
    "Incident": {
        "pm": ("Abdulraheem Mohammed", "Mohammed Sohail Mohammed Ilyas"),
        "co": ("Arshad ahmed abdulhameed",),
    },
    "Colocation": {
        "pm": ("Mohammed Imran Ansary",),
        "co": ("Mohamed Walid Khalil Nmer Rahma", "Obed Sharrif"),
    },
}

# Warehouse owns the operational DN closure check. These accounts are the
# confirmed operational contacts; this list does not grant Page or DocType
# access. Ramzan currently lacks SIG Site Cycle/Workbench access, so the
# permission checks below intentionally leave his queue unavailable until the
# site role setup is changed through its own reviewed release.
WAREHOUSE_USERS = {
    "m.ramzan@sigtele.com",
    "tahir.shahzad@sigtele.com",
}

TASK_STAGE = {
    "mapping": "1 - Initial", "boq": "1 - Initial",
    "tcn": "2 - Plan", "mir": "2 - Plan", "visit": "2 - Plan",
    "tags": "3 - Handover", "photos": "3 - Handover", "asbuilt": "3 - Handover",
    "asbuilt_operational": "3 - Handover",
}


def _normalize_person(value):
    return " ".join(str(value or "").split()).casefold()


def _current_ops_membership(user):
    """Resolve only this opener's Employee link and confirmed Operations scope."""
    if user in WAREHOUSE_USERS:
        return {"ready": True, "issue": "", "memberships": [
            {"scope": scope, "role": "warehouse"} for scope in OPS_ROSTER
        ]}
    if user in ("", "Guest") or not frappe.db.exists("DocType", "Employee"):
        return {"ready": False, "issue": "Employee identity is unavailable.", "memberships": []}
    if not frappe.has_permission("Employee", "read"):
        return {"ready": False, "issue": "Your Employee link cannot be read for task routing.", "memberships": []}
    try:
        employees = frappe.get_list(
            "Employee", filters={"user_id": user, "status": "Active"},
            fields=["name", "employee_name", "user_id"], page_length=2)
    except Exception:
        return {"ready": False, "issue": "Employee identity lookup needs review.", "memberships": []}
    if len(employees) != 1:
        return {"ready": False, "issue": "A unique active Employee link is required for task routing.", "memberships": []}
    employee_name = _normalize_person(employees[0].get("employee_name"))
    memberships = []
    for scope, roles in OPS_ROSTER.items():
        for role, names in roles.items():
            if any(_normalize_person(name) == employee_name for name in names):
                memberships.append({"scope": scope, "role": role})
    if not memberships:
        return {"ready": False, "issue": "This Employee is not in the confirmed Operations roster.", "memberships": []}
    return {"ready": True, "issue": "", "memberships": memberships}


def _task_audience(family, owner_role, memberships):
    """A shared task is visible to a roster member of its scope and role."""
    if owner_role == "either":
        return any(m["scope"] == family and m["role"] in ("pm", "co") for m in memberships)
    return any(m["scope"] == family and m["role"] == owner_role for m in memberships)


def _asbuilt_operational_status(cycle, lines):
    """Use an explicit site DN line decision; quantities never imply closure."""
    site_refs = {
        str(cycle.get(field) or "").strip().casefold()
        for field in ("site_key", "site") if str(cycle.get(field) or "").strip()
    }
    matched = []
    for line in lines:
        site = str(line.get("custom_site") or "").strip().casefold()
        if not site or site not in site_refs:
            continue
        matched.append(line)
    return {
        "applicable": bool(matched),
        "closed": any(_flag(line, "custom_return_closed") for line in matched),
        "source_dns": sorted({str(line.get("parent") or "") for line in matched if line.get("parent")}),
    }


def _warehouse_operational_lines(cycles):
    """Read closure flags only from Stock Entries visible to the current user."""
    if not frappe.has_permission("Stock Entry", "read"):
        return [], None
    try:
        detail_meta = frappe.get_meta("Stock Entry Detail")
        if not all(detail_meta.has_field(field) for field in ("custom_site", "custom_return_closed")):
            return [], False
        closed_field = detail_meta.get_field("custom_return_closed")
        permlevel = int(getattr(closed_field, "permlevel", 0) or 0)
        if permlevel:
            roles = set(frappe.get_roles(frappe.session.user)) | {"All"}
            stock_meta = frappe.get_meta("Stock Entry")
            field_read = any(
                str(getattr(permission, "role", "")) in roles
                and int(getattr(permission, "permlevel", 0) or 0) == permlevel
                and getattr(permission, "read", 0) in (1, True, "1", "Yes", "yes")
                for permission in stock_meta.permissions
            )
            if not field_read:
                return [], None
        site_refs = sorted({
            str(cycle.get(field) or "").strip()
            for cycle in cycles for field in ("site_key", "site")
            if str(cycle.get(field) or "").strip()
        })
        if not site_refs:
            return [], True
        sources, complete = _all_visible(
            "Stock Entry", ["name"],
            filters={"docstatus": 1, "is_return": 0, "purpose": ["in", ["Material Issue", "Material Transfer"]]},
            order_by="posting_date asc, name asc", max_rows=MAX_ROWS)
        if not complete:
            return [], False
        source_names = [str(row.name) for row in sources if row.get("name")]
        lines = []
        for start in range(0, len(source_names), 400):
            batch = source_names[start:start + 400]
            lines.extend(frappe.get_all(
                "Stock Entry Detail",
                filters={"parent": ["in", batch], "parenttype": "Stock Entry", "custom_site": ["in", site_refs]},
                fields=["parent", "custom_site", "project", "custom_return_closed"],
                limit_page_length=0))
        return lines, True
    except Exception:
        return [], False


def _stage_tasks_for_user(cycles, memberships):
    """Project one queue row per logical task; never create one per employee."""
    tasks = []
    for cycle in cycles:
        if cycle.get("terminal") or not any(m.get("scope") == cycle.get("family") for m in memberships):
            continue
        for work in cycle.get("work") or []:
            role = work.get("owner_role") or "either"
            if not _task_audience(cycle.get("family"), role, memberships):
                continue
            tasks.append({
                "id": cycle["name"] + "::" + str(work.get("key") or "work"),
                "kind": "stage", "cycle": cycle["name"], "site": cycle["site"],
                "project_id": cycle["project_id"], "ba": cycle["ba"],
                "alias": cycle["alias"], "wo": cycle["wo"],
                "family": cycle["family"], "cycle_stage": cycle["stage"],
                "stage": str(work.get("stage") or TASK_STAGE.get(str(work.get("key") or ""), cycle["stage"])),
                "key": str(work.get("key") or ""), "label": str(work.get("label") or "Work"),
                "owner_role": role, "shared": True,
                "status": "Review due" if cycle.get("needs_review") else "Pending evidence",
                "needs_review": bool(cycle.get("needs_review")),
                "review_reason": str(cycle.get("delay_reason") or cycle.get("delay_note") or ""),
                "expected_evidence": str(work.get("closes_on") or ""),
            })

    return tasks


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


def _can_close_cycles(user, memberships=None):
    memberships = memberships if memberships is not None else _current_ops_membership(user).get("memberships", [])
    roles = set(frappe.get_roles(user))
    admin = user != "Guest" and "System Manager" in roles
    ops_closer = any(m.get("role") in ("pm", "co") for m in memberships)
    field_ops = user != "Guest" and "SIG Field Ops" in roles and ops_closer
    return bool((admin or field_ops)
                and frappe.has_permission("SIG Site Cycle", "write")
                and frappe.has_permission("SIG Evidence Event", "create"))

def _family(value):
    normalized = str(value or "").strip().lower()
    if normalized in ("5g", "colocation", "colo"):
        return "Colocation"
    if normalized == "capex":
        return "Capex"
    if normalized == "incident":
        return "Incident"
    return ""


def _cycle_view(row, project, today, operational=None):
    """Derive the highest evidenced stage without inventing missing predecessors."""
    operational_visible = operational is not None
    operational = operational or {"applicable": False, "closed": False, "source_dns": []}
    closed = _flag(row, "terminal")
    has_prep = bool(row.get("mapping_at") or row.get("boq_at") or row.get("pimp_at")
                    or row.get("tcn_at") or row.get("mir_at") or row.get("first_visit_at"))
    prepared = bool(row.get("tcn_at") and row.get("mir_at") and row.get("first_visit_at"))
    if closed:
        stage = "Closed"
    elif row.get("invoice_at") or row.get("ho_at"):
        # Applicable handover evidence starts the final active Invoicing stage.
        # The PM-owned As-Built BOQ file remains a task within this stage.
        stage = "4 - Invoicing"
    elif prepared:
        stage = "3 - Handover"
    elif has_prep:
        stage = "2 - Plan"
    else:
        stage = "1 - Initial"
    work = []
    family = _family((project or {}).get("custom_family") or row.get("project"))
    if (not closed and not row.get("ho_at") and not row.get("asbuilt_at")
            and not row.get("invoice_at")
            and (row.get("mapping_at") or row.get("boq_at") or row.get("pimp_at"))):
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
        ):
            if not row.get(field):
                work.append({"key": key, "label": label, "owner_role": role,
                             "closes_on": label + " evidence"})
        if operational.get("applicable") and not operational.get("closed"):
            work.append({"key": "asbuilt_operational", "label": "As-Built Operational",
                         "owner_role": "warehouse", "stage": "3 - Handover",
                         "closes_on": "Any linked site DN line custom_return_closed = 1",
                         "source_dns": operational.get("source_dns") or []})
    if not closed and (prepared or row.get("ho_at") or row.get("invoice_at")) and not row.get("asbuilt_at"):
        work.append({"key": "asbuilt", "label": "As-Built BOQ file", "owner_role": "pm",
                     "stage": "4 - Invoicing" if row.get("ho_at") or row.get("invoice_at") else "3 - Handover",
                     "closes_on": "ASBUILT_BOQ_GENERATED"})
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
        "needs_review": bool(delay and not closed and work), "work": work,
        "events": {key: str(row.get(key) or "") for key in (
            "mapping_at", "boq_at", "tcn_at", "mir_at", "first_visit_at",
            "tags_at", "photos_at", "asbuilt_at", "warranty_at", "ho_at", "invoice_at")},
        "asbuilt_operational": {"visible": operational_visible,
                                 "applicable": bool(operational.get("applicable")) if operational_visible else None,
                                 "closed": bool(operational.get("closed")) if operational_visible else None,
                                 "source_dns": operational.get("source_dns") or []},
    }

@frappe.whitelist()
def get_overview():
    """Read current ToDos, evidence-derived pipeline work and authorized cycles."""
    result = {"todos": [], "cycles": [], "projects": [], "stage_tasks": [],
                    "summary": {"todos": 0, "overdue_todos": 0, "cycles": 0, "delayed": 0,
                          "aged": 0, "past_due": 0, "closed": 0, "exceptions": 0,
                          "stages": {}, "stage_tasks": 0, "review_tasks": 0},
              "complete": {"todos": True, "cycles": True}, "todo_access": False,
              "can_close_cycles": False, "todo_create": False, "person": frappe.session.user,
              "task_route": {"ready": False, "issue": "", "memberships": []}}
    user, today = frappe.session.user, frappe.utils.nowdate()
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
              "asbuilt_at", "warranty_at", "ho_at", "invoice_at"]
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
    warehouse_lines, warehouse_complete = _warehouse_operational_lines(rows)
    result["complete"]["asbuilt_operational"] = warehouse_complete
    result["operational_access"] = (
        "available" if warehouse_complete is True
        else "restricted" if warehouse_complete is None
        else "unavailable"
    )
    for row in rows:
        project_key = str(row.get("erp_project") or "")
        project = projects_by_name.get(project_key)
        row["project_alias"] = aliases_by_stream.get(str(row.get("project_stream") or ""), "")
        operational = _asbuilt_operational_status(row, warehouse_lines) if warehouse_complete else None
        cycle = _cycle_view(row, project, today, operational)
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
    result["task_route"] = _current_ops_membership(user)
    route_memberships = result["task_route"].get("memberships") or []
    result["can_close_cycles"] = _can_close_cycles(user, route_memberships)
    if result["task_route"]["ready"]:
        result["stage_tasks"] = _stage_tasks_for_user(result["cycles"], result["task_route"]["memberships"])
        result["summary"]["stage_tasks"] = sum(1 for task in result["stage_tasks"] if task["kind"] == "stage")
        result["summary"]["review_tasks"] = sum(1 for task in result["stage_tasks"]
                                                if task["kind"] == "stage" and task["needs_review"])
    result["todos_has_more"] = len(todos) > len(result["todos"]) if result["todo_access"] else False
    return result

@frappe.whitelist()
def export_workbook(filter="open"):
    """Export the opener's routed task queue and permission-visible cycles."""
    if not frappe.has_permission("SIG Site Cycle", "read") or not frappe.has_permission("SIG Site Cycle", "export"):
        frappe.throw("You need SIG Site Cycle read and export permission to download this workbook.",
                     frappe.PermissionError)
    data = get_overview()
    if not data.get("complete", {}).get("cycles"):
        frappe.throw("The visible cycle read reached its safety limit. Refine the source data before exporting.")
    if not data.get("complete", {}).get("asbuilt_operational"):
        frappe.throw("As-Built Operational coverage could not be verified for this account. Check Stock Entry read access and retry.")
    all_cycles = list(data.get("cycles") or [])
    if filter == "cycles" or filter == "open":
        cycles = [c for c in all_cycles if not c.get("terminal")]
        tasks = [t for t in data.get("stage_tasks") or [] if t.get("cycle") in {c.get("name") for c in cycles}]
    else:
        tasks = list(data.get("stage_tasks") or [])
        if filter == "review":
            tasks = [t for t in tasks if t.get("needs_review") or t.get("kind") == "review"]
        elif filter.startswith("stage:"):
            stage = filter[6:]
            tasks = [t for t in tasks if (t.get("kind") == "closure" if stage == "Cycle closure" else t.get("stage") == stage and t.get("kind") != "closure")]
        else:
            tasks = [t for t in tasks if t.get("kind") != "review"]
        cycle_names = {t.get("cycle") for t in tasks}
        cycles = [c for c in all_cycles if c.get("name") in cycle_names and not c.get("terminal")]

    wb = Workbook()
    ws = wb.active
    ws.title = "Cycles"
    headers = ["Cycle ID", "Site", "WO", "BA", "Project alias", "ERP Project", "Scope",
               "Stage", "Status", "Pending work", "Review due", "Delayed", "Aged",
               "Due date", "Delay reason", "Delay note", "Closed on", "Closed by",
               "Mapping at", "BOQ at", "TCN at", "MIR at", "Visit at",
               "Tags at", "Photos at", "As-Built BOQ at", "As-Built Operational closed",
               "As-Built DN source(s)", "Warranty at", "Handover at", "Invoice at"]
    ws.append(headers)
    stage_ws = wb.create_sheet("Stage tasks")
    stage_ws.append(["Task ID", "Cycle ID", "Site", "WO", "BA", "Project alias",
                     "Task stage", "Cycle stage", "Task", "Role", "Status",
                     "Expected evidence", "Review reason"])
    cycle_by_name = {c.get("name"): c for c in all_cycles}
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
                   "first_visit_at", "tags_at", "photos_at", "asbuilt_at")])
        operational = cycle.get("asbuilt_operational") or {}
        ws.cell(ws.max_row, 25, bool(operational.get("closed")))
        ws.cell(ws.max_row, 26, "; ".join(operational.get("source_dns") or []))
        ws.cell(ws.max_row, 27, events.get("warranty_at"))
        ws.cell(ws.max_row, 28, events.get("ho_at"))
        ws.cell(ws.max_row, 29, events.get("invoice_at"))
    for task in tasks:
        cycle = cycle_by_name.get(task.get("cycle"))
        if not cycle:
            continue
        role = task.get("owner_role") or "either"
        audience = "PM" if role == "pm" else "Coordinator" if role == "co" else "Warehouse" if role == "warehouse" else "PM or Coordinator"
        stage_ws.append([task.get("id"), cycle.get("name"), cycle.get("site"), cycle.get("wo"),
                         cycle.get("ba"), cycle.get("alias"), task.get("stage"), cycle.get("stage"),
                         task.get("label"), audience, task.get("status"),
                         task.get("expected_evidence"), task.get("review_reason")])
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
    if not _can_close_cycles(user):
        frappe.throw("Only Field Ops users may close site cycles.", frappe.PermissionError)
    try:
        names = cycles if isinstance(cycles, list) else json.loads(cycles or "[]")
    except Exception:
        frappe.throw("Invalid cycle selection.")
    names = list(dict.fromkeys(str(n).strip() for n in names if str(n).strip()))
    reason = str(reason or "").strip().replace("|", "/")
    if not names or len(names) > 50 or not reason or len(reason) > 500:
        frappe.throw("Select 1–50 cycles and enter a closure reason up to 500 characters.")
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

