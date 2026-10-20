import frappe
from frappe.model.document import Document


class SIGExcelSetup(Document):
    def validate(self):
        if not frappe.flags.excel_setup_service:
            frappe.throw("Use the Excel Setup page to publish configuration", frappe.PermissionError)
        if self.doctype == "SIG Excel Setup Revision" and not self.is_new():
            frappe.throw("Published setup revisions are immutable")

    def on_trash(self):
        frappe.throw("Published Excel Setup cannot be deleted")
