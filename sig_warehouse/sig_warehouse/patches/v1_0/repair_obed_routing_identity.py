"""Replace the confirmed stale Obed routing ID without changing routing policy."""

import copy
import json

import frappe

from sig_warehouse.sig_warehouse.pc_clearance_rules import compile_scopes
from sig_warehouse.sig_warehouse.pc_review_routing import active_employees, effective_scopes, load_matrix


OLD = "HR-EMP-00039"
NEW = "Mohammed Obed Shareef"
NAME = "Obed Sharrif"
USER = "obed.sharrif@sigtele.com"


def _rename_scopes(scopes):
    return {
        NEW if employee == OLD else employee: sorted(NEW if reviewer == OLD else reviewer for reviewer in reviewers)
        for employee, reviewers in scopes.items()
    }


def execute():
    # Serialize with the ordinary People routing publisher.
    with frappe.cache().lock("sig_people_routing_publish", timeout=60):
        frappe.db.sql("SELECT value FROM tabSingles WHERE doctype=%s AND field='revision' FOR UPDATE", ("SIG People Routing Setup",))
        doc = frappe.get_single("SIG People Routing Setup")
        matrix = load_matrix()
        rows = [row for row in matrix.get("employees", []) if row.get("employee") == OLD]
        if not rows:
            # Repeat migrations are no-ops only when the intended identity is present.
            matches = [row for row in matrix.get("employees", []) if row.get("employee") == NEW and row.get("employee_name") == NAME]
            if len(matches) == 1:
                return
            frappe.throw("Obed routing repair stopped: expected identity is absent or ambiguous.")
        person = frappe.db.get_value("Employee", NEW, ["employee_name", "status", "user_id"], as_dict=True)
        if (len(rows) != 1 or rows[0].get("employee_name") != NAME or frappe.db.exists("Employee", OLD)
                or not person or person.employee_name != NAME or person.status != "Active" or person.user_id != USER
                or not frappe.db.get_value("User", USER, "enabled")
                or any(row.get("employee") == NEW for row in matrix["employees"])):
            frappe.throw("Obed routing repair stopped: identity or Employee state changed; review manually.")
        before = compile_scopes(matrix)["employees"]
        revised = copy.deepcopy(matrix)
        next(row for row in revised["employees"] if row.get("employee") == OLD)["employee"] = NEW
        after = effective_scopes(revised, active_employees())["employees"]
        if _rename_scopes(before) != after:
            frappe.throw("Obed routing repair stopped: reviewer scopes differ beyond the approved identity correction.")
        history = json.loads(doc.history_json or "[]")
        history.append({"revision": int(doc.revision or 0), "matrix": matrix,
                        "saved_by": frappe.session.user, "saved_at": str(frappe.utils.now_datetime()),
                        "reason": "Correct stale Obed Employee identity"})
        doc.revision = int(doc.revision or 0) + 1
        revised["routing_version"] = "people-setup-" + str(doc.revision)
        doc.configuration_json = json.dumps(revised, ensure_ascii=False, sort_keys=True)
        doc.history_json = json.dumps(history, ensure_ascii=False, sort_keys=True)
        previous = frappe.flags.sig_people_routing_service
        frappe.flags.sig_people_routing_service = True
        try:
            doc.save(ignore_permissions=True)
        finally:
            frappe.flags.sig_people_routing_service = previous
