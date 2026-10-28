import json

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from sig_warehouse.sig_letters import blocks as block_model
from sig_warehouse.sig_letters.reference import day_prefix, next_reference


class SIGLetter(Document):
    def autoname(self):
        """name = yymmddA (A, B, ... per letter date), the reference printed on the letter."""
        prefix = day_prefix(getdate(self.letter_date or nowdate()))
        existing = frappe.get_all("SIG Letter", filters={"name": ["like", f"{prefix}%"]}, pluck="name")
        self.name = next_reference(prefix, existing)

    def validate(self):
        if not self.blocks:
            frappe.throw("Add at least one block to the letter.")
        for row in self.blocks:
            try:
                block_model.block_to_row(block_model.row_to_block(row.as_dict()))
            except (block_model.BlockError, KeyError, ValueError) as exc:
                frappe.throw(f"Row {row.idx}: {exc}")
        if self.related_document and not self.related_doctype:
            frappe.throw("Set Related Document Type for the related document.")


@frappe.whitelist()
def make_from_template(template, context=None):
    """Return a SIG Letter dict filled from a template, with {{ jinja }} variables rendered.

    ``context`` is a JSON object of the values the template's variables expect. The caller then inserts the
    returned dict (after adding addressee / date) - nothing is saved here.
    """
    if not frappe.has_permission("SIG Letter Template", "read", template):
        frappe.throw("You do not have permission to use this letter template.", frappe.PermissionError)

    return _template_payload(template, context)


def _template_payload(template, context=None):
    """Render a SIG Letter Template for an authorized server-side workflow."""
    tpl = frappe.get_doc("SIG Letter Template", template)
    if tpl.disabled:
        frappe.throw(f"Template {template} is disabled")
    values = json.loads(context) if isinstance(context, str) else (context or {})

    def render(text):
        return frappe.render_template(text, values) if text else text

    rows = []
    for row in tpl.blocks:
        out = {"block_type": row.block_type}
        for field in ("content", "bullets", "table_json"):
            value = row.get(field)
            if value:
                out[field] = render(value)
        rows.append(out)
    return {
        "doctype": "SIG Letter",
        "template": tpl.name,
        "language": tpl.language,
        "addressee": render(tpl.default_addressee),
        "attn": render(tpl.default_attn),
        "subject": render(tpl.subject),
        "greeting": render(tpl.greeting),
        "closing": render(tpl.closing),
        "blocks": rows,
    }
