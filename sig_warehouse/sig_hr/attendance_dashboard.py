"""Permission-filtered attendance events for the HR attendance page."""
import csv
import io

import frappe
from frappe.utils import add_days, getdate, nowdate


def _data(date=None, employee=None):
    frappe.only_for(("HR Manager", "HR User", "System Manager"))
    frappe.has_permission("Employee", "read", throw=True)
    frappe.has_permission("Employee Checkin", "read", throw=True)
    day = getdate(date or nowdate())
    filters = {"status": "Active"}
    if employee:
        filters["name"] = employee
    employees = frappe.get_list("Employee", filters=filters,
        fields=["name", "employee_name", "department", "custom_office_signin"],
        order_by="employee_name asc", limit_page_length=0)
    ids = [e.name for e in employees]
    logs = frappe.get_list("Employee Checkin", filters={"employee": ["in", ids],
        "time": ["between", [str(day) + " 00:00:00", str(add_days(day, 1)) + " 00:00:00"]]},
        fields=["name", "employee", "time", "log_type"], order_by="time asc", limit_page_length=0) if ids else []
    grouped = {e.name: [] for e in employees}
    for log in logs:
        if getdate(log.time) == day and log.employee in grouped:
            grouped[log.employee].append(log)
    rows = []
    for e in employees:
        events = grouped[e.name]
        if not events and not e.custom_office_signin:
            continue
        ins = [x for x in events if x.log_type == "IN"]
        outs = [x for x in events if x.log_type == "OUT"]
        if not ins:
            state = "Needs review" if outs else "No sign-in"
        elif outs and outs[-1].time > ins[-1].time:
            state = "Signed out"
        else:
            state = "Signed in"
        rows.append({"employee": e.name, "employee_name": e.employee_name, "department": e.department,
            "first_in": ins[0].time if ins else None, "last_out": outs[-1].time if outs else None,
            "status": state, "events": events})
    return rows


@frappe.whitelist()
def get_day(date=None, employee=None):
    return _data(date, employee)


@frappe.whitelist()
def get_history(employee, from_date, to_date):
    frappe.only_for(("HR Manager", "HR User", "System Manager"))
    start, end = getdate(from_date), getdate(to_date)
    if end < start or (end - start).days > 366:
        frappe.throw("Choose a valid date range of up to 367 days.")
    frappe.has_permission("Employee", "read", throw=True)
    frappe.has_permission("Employee Checkin", "read", throw=True)
    if not frappe.get_list("Employee", filters={"name": employee}, pluck="name", limit_page_length=1):
        frappe.throw("Employee is not accessible.", frappe.PermissionError)
    return frappe.get_list("Employee Checkin", filters={"employee": employee,
        "time": ["between", [str(start) + " 00:00:00", str(add_days(end, 1)) + " 00:00:00"]]},
        fields=["name", "time", "log_type"], order_by="time desc", limit_page_length=0)


@frappe.whitelist()
def export_day(date=None):
    rows = _data(date)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Employee", "Department", "In", "Out", "Status"])
    for row in rows:
        writer.writerow([row["employee_name"], row["department"], row["first_in"], row["last_out"], row["status"]])
    frappe.local.response.filename = "attendance.csv"
    frappe.local.response.filecontent = "\ufeff" + output.getvalue()
    frappe.local.response.type = "download"
