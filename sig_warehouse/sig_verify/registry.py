"""Which doctypes issue a verification token + QR, and what the public check may reveal.

Pure Python (no frappe import) so it can be unit-tested and imported from ``hooks.py``.
"""

TOKEN_FIELD = "custom_verify_token"
QR_FILE_PREFIX = "verify_qr_"
VERIFY_PATH = "/verify"

# doctype -> how to summarise it on the public page. Every key is optional.
VERIFIABLE = {
    "Quotation": {
        "date_field": "transaction_date",
        "valid_till_field": "valid_till",
        "company_field": "company",
        "total_field": "grand_total",
        "currency_field": "currency",
        "insert_after": "naming_series",
    },
    # Later (letters, warranty): add the doctype here, e.g.
    # "SIG Letter": {"date_field": "date", "company_field": "company"},
}


def qr_file_name(name):
    """File name of the QR image attached to a document."""
    return f"{QR_FILE_PREFIX}{name}.png"


def state_for(docstatus):
    """Public state word for a document's docstatus."""
    if docstatus == 1:
        return "Valid"
    if docstatus == 2:
        return "Cancelled"
    return "Draft"


def query_fields(doctype):
    """Columns to read for a doctype's public summary (always name and docstatus)."""
    cfg = VERIFIABLE[doctype]
    fields = ["name", "docstatus"]
    for key in ("date_field", "valid_till_field", "company_field", "total_field", "currency_field"):
        if cfg.get(key):
            fields.append(cfg[key])
    return fields


def summary(doctype, row):
    """The only facts the public page may see. ``row`` is a dict of the queried columns."""
    cfg = VERIFIABLE[doctype]

    def pick(key):
        field = cfg.get(key)
        return row.get(field) if field else None

    def text(value):
        return "" if value is None else str(value)

    return {
        "valid": 1,
        "doctype": doctype,
        "name": row["name"],
        "state": state_for(row.get("docstatus")),
        "date": text(pick("date_field")),
        "valid_till": text(pick("valid_till_field")),
        "company": text(pick("company_field")),
        "total": pick("total_field"),
        "currency": text(pick("currency_field")),
    }


def token_field_spec(doctype):
    """Custom Field definition for the hidden token column."""
    spec = {
        "fieldname": TOKEN_FIELD,
        "label": "Verify Token",
        "fieldtype": "Data",
        "read_only": 1,
        "hidden": 1,
        "no_copy": 1,
        "allow_on_submit": 1,
        "print_hide": 1,
        "translatable": 0,
    }
    after = VERIFIABLE[doctype].get("insert_after")
    if after:
        spec["insert_after"] = after
    return spec
