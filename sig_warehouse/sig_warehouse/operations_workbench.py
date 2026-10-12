"""Read-only, permission-respecting data for the Field Delivery workbench."""

import frappe


def _can_read(doctype):
    return frappe.has_permission(doctype, "read")


@frappe.whitelist()
def get_overview():
    """Return only records visible to the current ERP user.

    Project membership is not assumed: the Projects table has no verified internal
    assignment source, so its section is explicitly a permission-filtered overview.
    """
    data = {"todos": [], "projects": [], "cycles": [], "counts": {}}
    user = frappe.session.user

    if _can_read("ToDo"):
        data["todos"] = frappe.get_list(
            "ToDo",
            filters={"allocated_to": user, "status": ["not in", ["Closed", "Cancelled"]]},
            fields=["name", "description", "date", "status", "reference_type", "reference_name"],
            order_by="date asc, modified desc",
            page_length=30,
        )

    if _can_read("Project"):
        data["projects"] = frappe.get_list(
            "Project",
            fields=["name", "project_name", "status", "expected_start_date", "expected_end_date"],
            order_by="modified desc",
            page_length=30,
        )

    if _can_read("SIG Site Cycle"):
        data["cycles"] = frappe.get_list(
            "SIG Site Cycle",
            fields=["name", "site", "site_key", "project", "stage", "stage_due_on", "terminal", "last_event_at"],
            order_by="terminal asc, stage_due_on asc, last_event_at desc",
            page_length=60,
        )

    data["counts"] = {
        "todos": len(data["todos"]),
        "projects": len(data["projects"]),
        "cycles": len(data["cycles"]),
        "overdue": sum(1 for row in data["todos"] if row.get("date") and str(row.date) < frappe.utils.nowdate()),
    }
    return data
