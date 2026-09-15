import frappe
from frappe import _
from frappe.model.document import Document


class SIGWarehouseCutover(Document):
    def validate(self):
        if self.is_new():
            return
        old = frappe.db.get_value(
            "SIG Warehouse Cutover", self.name,
            ["state", "wh_writer_disabled_confirmed", "delivery_route_mode", "delivery_route_confirmed"], as_dict=True,
        )
        protected = (
            str(old.state) != str(self.state)
            or int(old.wh_writer_disabled_confirmed or 0) != int(self.wh_writer_disabled_confirmed or 0)
            or str(old.delivery_route_mode or "") != str(self.delivery_route_mode or "")
            or int(old.delivery_route_confirmed or 0) != int(self.delivery_route_confirmed or 0)
        )
        if protected and not frappe.flags.get("sig_warehouse_cutover_transition"):
            frappe.throw(_("Cutover state and gate fields can only be changed through the approved cutover actions."))
