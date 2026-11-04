"""Permission-aware projections for people sections of the setup page.

Business records stay in their owning DocTypes; this module does not publish
employee details to the workbook configuration or bypass their permissions.
"""

import frappe
from frappe import _
from frappe.model import get_permitted_fields


SECTIONS = {
    "employees": ("Employee", ("name", "employee_name", "status", "designation", "department", "cell_number", "user_id", "custom_custody_account")),
    "project_assignments": ("SIG Employee Project Assignment", ("name", "employee", "employee_name", "project", "project_role", "start_date", "end_date", "status")),
    "reporter_maps": ("SIG Field Reporter Map", ("name", "reporter_phone", "employee")),
    "candidates": ("SIG Candidate Intake", ("name", "candidate_name", "status")),
    "onboarding": ("SIG Employee Onboarding", ("name", "employee")),
}

# These are narrow edits to existing records, not an alternate generic document API.
EDITABLE = {
    "project_assignments": ("employee", "project", "project_role", "start_date", "end_date"),
    "reporter_maps": ("employee",),
}


@frappe.whitelist()
def get_section(section):
    """Return only permitted records and fields for an explicitly supported section."""
    if section not in SECTIONS:
        frappe.throw("Unknown people setup section.")
    doctype, proposed_fields = SECTIONS[section]
    if not frappe.has_permission(doctype, "read"):
        frappe.throw("You do not have access to this section.", frappe.PermissionError)
    meta = frappe.get_meta(doctype)
    # Respect field permlevels in addition to document and user permissions.
    allowed = set(get_permitted_fields(doctype, user=frappe.session.user, permission_type="read"))
    fields = [field for field in proposed_fields if field == "name" or (meta.has_field(field) and field in allowed)]
    fields.append("modified")
    return {
        "doctype": doctype,
        "fields": fields,
        "rows": frappe.get_list(doctype, fields=fields, limit_page_length=0, order_by="modified desc"),
        "can_create": bool(frappe.has_permission(doctype, "create")),
        "can_write": bool(frappe.has_permission(doctype, "write")),
    }


@frappe.whitelist(methods=["POST"])
def update_section_record(section, name, modified, values):
    """Save narrow edits through the owning controller and its permissions."""
    if section not in EDITABLE:
        frappe.throw(_("This section cannot be edited here."), frappe.PermissionError)
    values = frappe.parse_json(values)
    if not isinstance(values, dict) or set(values) - set(EDITABLE[section]):
        frappe.throw(_("Unsupported fields."))
    doctype = SECTIONS[section][0]
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw(_("This record changed. Reload it before saving."))
    permitted = set(get_permitted_fields(doctype, user=frappe.session.user, permission_type="write"))
    if set(values) - permitted:
        frappe.throw(_("You cannot edit one or more selected fields."), frappe.PermissionError)
    doc.update(values)
    doc.save()
    return {"name": doc.name, "modified": doc.modified}


@frappe.whitelist(methods=["POST"])
def create_project_assignment(values):
    """Create an unapproved assignment through the normal DocType controller."""
    doctype = SECTIONS["project_assignments"][0]
    if not frappe.has_permission(doctype, "create"):
        frappe.throw(_("You cannot create project assignments."), frappe.PermissionError)
    values = frappe.parse_json(values)
    if not isinstance(values, dict) or set(values) - set(EDITABLE["project_assignments"]):
        frappe.throw(_("Unsupported fields."))
    allowed = set(get_permitted_fields(doctype, user=frappe.session.user, permission_type="write"))
    if set(values) - allowed:
        frappe.throw(_("You cannot edit one or more selected fields."), frappe.PermissionError)
    doc = frappe.get_doc({"doctype": doctype, "status": "Draft", **values})
    doc.insert()
    return {"name": doc.name}
