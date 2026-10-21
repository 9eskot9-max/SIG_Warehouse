"""Public document check behind the QR (guest, rate limited).

GET /api/method/sig_warehouse.sig_verify.api.verify?t=<token>

Returns only what proves a printed document is genuine (see ``registry.summary``). Never line
items, customer or contact details. An unknown, malformed or missing token returns {"valid": 0}.
"""

import frappe
from frappe.rate_limiter import rate_limit

from .registry import TOKEN_FIELD, VERIFIABLE, query_fields, summary
from .tokens import is_plausible_token


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=3600)
def verify(t=None):
    token = (t or "").strip()
    if not is_plausible_token(token):
        return {"valid": 0}
    for doctype in VERIFIABLE:
        if not frappe.get_meta(doctype).has_field(TOKEN_FIELD):
            continue
        row = frappe.db.get_value(doctype, {TOKEN_FIELD: token}, query_fields(doctype), as_dict=True)
        if row:
            return summary(doctype, row)
    return {"valid": 0}
