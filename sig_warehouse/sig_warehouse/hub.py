"""SIG Hub: one front door to every SIG interface.

The SIG app spans several modules (warehouse, operations, finance, HR). Frappe v16 shows one tile per app,
so this page lists every interface the signed-in user may open. Visibility reuses each Page's own role
permission; nothing here grants access.
"""
import frappe

# (group, [(page name, description)]). Labels come from the Page title, so a rename follows automatically.
GROUPS = [
    ("Warehouse and purchasing", [
        ("warehouse-workspace", "Dispatch, returns, custody and the warehouse front door."),
        ("purchasing-receiving", "Items, purchase orders and purchase receipts."),
        ("purchase-receipt-pricing", "Complete missing prices on draft receipts."),
    ]),
    ("Operations and field", [
        ("operations-workbench", "Projects, site cycles, evidence and the work queue."),
        ("field-planner", "Weekly team routes, TCN cut-offs and critical sites."),
        ("site-cycles", "Every site cycle and its stage, with KPIs."),
        ("site-visits", "Visits reported by the field teams."),
        ("my-visit-schedule", "Your own planned visits."),
        ("project-progress", "Progress by project and PO."),
        ("excel-setup", "Projects, scope and setup shared with the Excel workbooks."),
        ("app-connections", "Connected services such as Todoist."),
    ]),
    ("Finance", [
        ("finance-workbench", "Daily finance work, statements and receivables."),
        ("pc-invoice-review", "Review petty-cash receipts and create draft entries."),
        ("pc-transaction-status", "Petty-cash cycles, top-ups and balances."),
        ("client-collections", "Payment reminders with invoice copies."),
    ]),
    ("People", [
        ("hr-workbench", "HR queues, compliance renewals and headcount."),
        ("hr-attendance", "Attendance for today, history and exceptions."),
        ("employee-workbench", "Your own work, tasks and records."),
    ]),
]

WORKSPACE_LINKS = [
    # (workspace, group, label, description, route)
    ("ZATCA Integrations", "Finance", "ZATCA", "E-invoicing setup, CSIDs and transactions.", ["Workspaces", "ZATCA Integrations"]),
]


def _page_allowed(name):
    if not frappe.db.exists("Page", name):
        return None
    try:
        return frappe.get_doc("Page", name).is_permitted()
    except Exception:
        roles = frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Page"}, pluck="role")
        return not roles or bool(set(roles) & set(frappe.get_roles()))


def _workspace_allowed(name):
    if not frappe.db.exists("Workspace", name):
        return False
    roles = frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Workspace"}, pluck="role")
    return not roles or bool(set(roles) & set(frappe.get_roles()))


@frappe.whitelist()
def get_cards():
    out = []
    for group, entries in GROUPS:
        cards = []
        for name, description in entries:
            if _page_allowed(name):
                cards.append({"label": frappe.db.get_value("Page", name, "title") or name,
                              "description": description, "route": [name]})
        for workspace, wgroup, label, description, route in WORKSPACE_LINKS:
            if wgroup == group and _workspace_allowed(workspace):
                cards.append({"label": label, "description": description, "route": route})
        if cards:
            out.append({"group": group, "cards": cards})
    return out
