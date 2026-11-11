"""App-owned daily refresh for SIG Employee Onboarding controls."""

import frappe


ONBOARDING = "SIG Employee Onboarding"
EMPLOYEE = "Employee"


def run_daily_refresh():
    """Refresh each active Employee control, isolating failures with savepoints.

    A failure rolls back only the current Employee's writes. Other controls can
    still refresh, and Frappe commits the scheduler transaction after return.
    """
    employees = frappe.get_all(
        EMPLOYEE,
        filters={"status": "Active"},
        pluck="name",
        limit_page_length=0,
    )

    for index, employee in enumerate(employees, start=1):
        save_point = f"sig_hr_onboarding_{index}"
        frappe.db.savepoint(save_point)
        try:
            control = frappe.db.get_value(ONBOARDING, {"employee": employee}, "name")
            if control:
                doc = frappe.get_doc(ONBOARDING, control)
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({"doctype": ONBOARDING, "employee": employee})
                doc.insert(ignore_permissions=True)
        except Exception:
            frappe.db.rollback(save_point=save_point)
            frappe.log_error(title=f"SIG HR daily refresh failed for {employee}")
        else:
            frappe.db.release_savepoint(save_point)
