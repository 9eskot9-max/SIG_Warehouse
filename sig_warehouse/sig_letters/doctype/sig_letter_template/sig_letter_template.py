import json

import frappe
from frappe.model.document import Document

from sig_warehouse.sig_letters import blocks as block_model


class SIGLetterTemplate(Document):
    def validate(self):
        if self.variables:
            try:
                variables = json.loads(self.variables)
            except ValueError as exc:
                frappe.throw(f"Variables must be valid JSON: {exc}")
            if not isinstance(variables, list) or not all(isinstance(v, dict) and v.get("key") for v in variables):
                frappe.throw('Variables must be a list of objects with a "key", e.g. [{"key": "site_id"}]')
        for row in self.blocks:
            try:
                kind = block_model.LABEL_TO_TYPE[row.block_type]
            except KeyError:
                frappe.throw(f"Row {row.idx}: unknown block type {row.block_type}")
            if kind in ("p", "h", "note") and not (row.content or "").strip():
                frappe.throw(f"Row {row.idx}: {row.block_type} needs text")
