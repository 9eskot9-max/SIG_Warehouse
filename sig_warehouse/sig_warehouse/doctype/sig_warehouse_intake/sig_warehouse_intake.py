import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SIGWarehouseIntake(Document):
    def before_insert(self):
        if not self.operation_id:
            self.operation_id = frappe.generate_hash(length=32)

    def validate(self):
        if not self.intake_type:
            frappe.throw("Select an intake action.")
        for row in self.lines:
            if flt(row.qty) <= 0:
                frappe.throw(f"Line {row.idx}: quantity must be greater than zero.")
            if not row.description and not row.item_code:
                frappe.throw(f"Line {row.idx}: enter a description or select an Item.")
        if self.source_file:
            private = frappe.db.get_value("File", {"file_url": self.source_file}, "is_private")
            if not private:
                frappe.throw("Attach a private File as the source document.")
