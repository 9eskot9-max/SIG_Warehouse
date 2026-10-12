"""Permission-respecting data for the SIG field-delivery workbench."""

from html import unescape
from html.parser import HTMLParser

import frappe


PAGE_SIZE = 500
MAX_ROWS = 20000


class _PlainText(HTMLParser):
    """Extract visible text from a ToDo description without retaining markup."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.suppressed = 0

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
    parser = _PlainText()
    parser.feed(str(value or ""))
    return " ".join(unescape("".join(parser.parts)).split())


def _all_visible(doctype, fields, filters=None, order_by=None, max_rows=MAX_ROWS):
    """Read all visible rows in pages; `get_list` applies user permissions."""
    rows = []
    start = 0
    while start < max_rows:
        batch = frappe.get_list(
            doctype,
            filters=filters or {},
            fields=fields,
            order_by=order_by or "name asc",
            start=start,
            page_length=min(PAGE_SIZE, max_rows - start),
        )
        rows.extend(batch)
        if len(batch) < min(PAGE_SIZE, max_rows - start):
            return rows, True
        start += len(batch)
    return rows, False


def _flag(row, field):
    return row.get(field) in (1, True, "1", "Yes", "yes")


@frappe.whitelist()
def get_overview():
    """Return allocated tasks and open-cycle signals visible to this user.

    Project membership is not asserted: the source system has no verified internal
    Project assignment. Project rollups are grouped only when the user can read the
    linked Project record; cycles and ToDos are fetched through permission-aware lists.
    """
    result = {
        "todos": [], "projects": [], "exceptions": [],
        "summary": {"todos": 0, "overdue_todos": 0, "cycles": 0,
                    "delayed": 0, "aged": 0, "past_due": 0, "exceptions": 0},
        "complete": {"todos": True, "cycles": True},
    }
    today = frappe.utils.nowdate()
    user = frappe.session.user

    if frappe.has_permission("ToDo", "read"):
        todos, result["complete"]["todos"] = _all_visible(
            "ToDo",
            ["name", "description", "date", "status", "reference_type", "reference_name"],
            filters={"allocated_to": user, "status": ["not in", ["Closed", "Cancelled"]]},
            order_by="date asc, modified desc",
            max_rows=5000,
        )
        result["summary"]["todos"] = len(todos)
        result["summary"]["overdue_todos"] = sum(
            1 for row in todos if row.get("date") and str(row.date) < today
        )
        result["todos"] = [
            {**row, "description": _plain_text(row.get("description"))}
            for row in todos[:30]
        ]

    if not frappe.has_permission("SIG Site Cycle", "read"):
        return result

    cycles, result["complete"]["cycles"] = _all_visible(
        "SIG Site Cycle",
        ["name", "site", "site_key", "project", "erp_project", "stage", "stage_due_on",
         "terminal", "is_delayed", "is_aged", "delay_reason", "last_event_at"],
        filters={"terminal": 0},
        order_by="stage_due_on asc, last_event_at desc",
    )

    project_names = sorted({str(row.get("erp_project")) for row in cycles if row.get("erp_project")})
    readable_projects = {}
    if project_names and frappe.has_permission("Project", "read"):
        projects, _projects_complete = _all_visible(
            "Project", ["name", "project_name", "status"],
            filters={"name": ["in", project_names]}, order_by="project_name asc",
        )
        readable_projects = {row.name: row for row in projects}

    project_rollups = {}
    exceptions = []
    for row in cycles:
        linked_project = str(row.get("erp_project") or "")
        readable_project = readable_projects.get(linked_project)
        delayed = _flag(row, "is_delayed")
        aged = _flag(row, "is_aged")
        due = bool(row.get("stage_due_on") and str(row.stage_due_on) < today)

        if readable_project:
            bucket = project_rollups.setdefault(linked_project, {
                "name": linked_project,
                "project_name": str(readable_project.get("project_name") or linked_project),
                "status": str(readable_project.get("status") or ""),
                "cycles": 0, "delayed": 0, "aged": 0, "past_due": 0,
            })
            bucket["cycles"] += 1
            bucket["delayed"] += int(delayed)
            bucket["aged"] += int(aged)
            bucket["past_due"] += int(due)

        result["summary"]["cycles"] += 1
        result["summary"]["delayed"] += int(delayed)
        result["summary"]["aged"] += int(aged)
        result["summary"]["past_due"] += int(due)
        if delayed or aged or due:
            result["summary"]["exceptions"] += 1
            exceptions.append({
                "name": row.name,
                "site": str(row.get("site_key") or row.get("site") or row.name),
                "project": (str(readable_project.get("project_name") or linked_project)
                            if readable_project else (str(row.get("project") or "") if not linked_project else "")),
                "stage": str(row.get("stage") or ""),
                "delay_reason": str(row.get("delay_reason") or ""),
                "stage_due_on": str(row.get("stage_due_on") or ""),
                "last_event_at": str(row.get("last_event_at") or ""),
                "delayed": delayed, "aged": aged, "past_due": due,
            })

    result["projects"] = sorted(
        project_rollups.values(),
        key=lambda row: (-row["delayed"], -row["aged"], -row["past_due"], row["project_name"].lower()),
    )
    exceptions.sort(key=lambda row: (
        -int(row["delayed"]), -int(row["aged"]), -int(row["past_due"]),
        row["stage_due_on"] or "9999-12-31", row["site"].lower(),
    ))
    result["exceptions"] = exceptions[:30]
    return result
