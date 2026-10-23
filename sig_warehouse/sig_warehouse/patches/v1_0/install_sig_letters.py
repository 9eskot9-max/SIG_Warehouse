"""Install the SIG Letter print format and seed the template library (post_model_sync).

Idempotent. The print format is refreshed from the app file on every run (the app is its source of truth);
seed templates are created only when missing and are never overwritten, because people edit them in the ERP.
"""
import json
from pathlib import Path

import frappe

from sig_warehouse.sig_letters.blocks import block_to_row

PRINT_FORMAT = "SIG Letter (Infographic)"
BASE = Path(frappe.get_app_path("sig_warehouse")) / "sig_letters"


def execute():
    _install_print_format()
    _seed_templates()


def _install_print_format():
    html = (BASE / "print_format" / "sig_letter.html").read_text(encoding="utf-8-sig")
    values = {"doc_type": "SIG Letter", "print_format_type": "Jinja", "custom_format": 1, "standard": "No",
              "disabled": 0, "html": html, "module": "SIG Letters"}
    if frappe.db.exists("Print Format", PRINT_FORMAT):
        frappe.db.set_value("Print Format", PRINT_FORMAT, values)
    else:
        frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT, **values}).insert(ignore_permissions=True)
    frappe.make_property_setter({"doctype": "SIG Letter", "doctype_or_field": "DocType",
                                 "property": "default_print_format", "value": PRINT_FORMAT, "property_type": "Data"})


def _seed_templates():
    for path in sorted((BASE / "templates").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if frappe.db.exists("SIG Letter Template", data["template_name"]):
            continue
        frappe.get_doc({
            "doctype": "SIG Letter Template",
            "template_name": data["template_name"],
            "letter_type": data.get("letter_type", "General"),
            "language": data.get("language", "English"),
            "default_addressee": data.get("default_addressee"),
            "default_attn": data.get("default_attn"),
            "subject": data.get("subject"),
            "greeting": data.get("greeting"),
            "closing": data.get("closing"),
            "variables": json.dumps(data.get("variables", []), ensure_ascii=False),
            "blocks": [block_to_row(b) for b in data["blocks"]],
        }).insert(ignore_permissions=True)
