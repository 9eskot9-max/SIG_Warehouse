import frappe
from frappe import _
from frappe.model.document import Document


class SIGClientCollectionDraft(Document):
    def validate(self):
        if not self.invoices:
            frappe.throw(_("Add at least one invoice to the reminder draft."))
        if self.status not in ("Draft", "Sending", "Queued", "Partially Sent", "Failed"):
            frappe.throw(_("Invalid reminder status."))
        old = self.get_doc_before_save()
        if old and old.status != self.status and not self.flags.get("collection_dispatch"):
            frappe.throw(_("Reminder status is managed by the send workflow."))
        if old and old.status != "Draft":
            locked = (
                "naming_series", "customer", "company", "letter_date", "letter_type", "language", "channel",
                "recipient_whatsapp", "recipient_email", "currency", "total_outstanding",
                "is_overdue", "subject", "greeting", "letter_body", "whatsapp_message", "closing",
            )
            changed = [field for field in locked if old.get(field) != self.get(field)]
            invoice_fields = ("sales_invoice", "posting_date", "due_date", "currency", "invoice_total", "outstanding_amount")
            old_invoices = [tuple(row.get(field) for field in invoice_fields) for row in old.get("invoices", [])]
            new_invoices = [tuple(row.get(field) for field in invoice_fields) for row in self.get("invoices", [])]
            if old_invoices != new_invoices:
                changed.append("invoices")
            if changed:
                frappe.throw(_("This reminder has already been sent or attempted. Create a new draft to change recipient or content."))
            log_fields = ("delivery_key", "channel", "component", "recipient", "status", "attempts", "attempted_at", "message_id", "queue_reference", "error")
            old_log = [tuple(row.get(field) for field in log_fields) for row in old.get("deliveries", [])]
            new_log = [tuple(row.get(field) for field in log_fields) for row in self.get("deliveries", [])]
            if old_log != new_log and not self.flags.get("collection_dispatch"):
                frappe.throw(_("Delivery history is managed by the send workflow."))

