import frappe
from frappe.model.document import Document


class SIGPlanDecision(Document):
    """Append-only log of PM planning decisions. Entries are never edited or deleted; a blank entry clears."""

    def validate(self):
        if not self.is_new():
            frappe.throw("PM decisions are a log: change the cycle by adding a new decision, not by editing this one.")

    def on_trash(self):
        frappe.throw("PM decisions are a log and cannot be deleted.")
