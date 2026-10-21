from frappe.model.document import Document


class SIGMappingMasterRevision(Document):
    def validate(self):
        # Frappe runs on_update during insert as well as update. Guard at
        # validate time so the first insert succeeds while later edits fail.
        if not self.is_new():
            self._deny_mutation()

    def on_trash(self):
        self._deny_mutation()

    @staticmethod
    def _deny_mutation():
        import frappe
        frappe.throw("Mapping Master revision receipts are immutable")
