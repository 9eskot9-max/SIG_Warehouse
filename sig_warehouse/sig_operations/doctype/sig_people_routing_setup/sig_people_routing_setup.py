import frappe
from frappe.model.document import Document


class SIGPeopleRoutingSetup(Document):
    def validate(self):
        if not frappe.flags.sig_people_routing_service:
            frappe.throw("Use the People Setup publication action to change routing.", frappe.PermissionError)
