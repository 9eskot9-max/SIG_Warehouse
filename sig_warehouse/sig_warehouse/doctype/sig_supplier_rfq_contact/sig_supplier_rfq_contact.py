import re

import frappe
from frappe import _
from frappe.model.document import Document


class SIGSupplierRFQContact(Document):
    def validate(self):
        self.whatsapp_number = re.sub(r"[\s()+-]", "", str(self.whatsapp_number or ""))
        if not re.fullmatch(r"\d{8,15}", self.whatsapp_number):
            frappe.throw(_("Enter a phone number with country code (8 to 15 digits)."))
