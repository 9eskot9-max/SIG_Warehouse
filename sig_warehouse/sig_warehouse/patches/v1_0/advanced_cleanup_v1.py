"""v16: UI-only cleanup agreed on 4 November 2026. No data changes, nothing blocked on save.

- Site: hidden on Journal Entry, Payment Entry, Purchase Order, Purchase Invoice and Purchase Receipt (set on 0
  Journal Entries, 0 Payment Entries, 0 Purchase Orders, 0 Purchase Invoices; 1 Purchase Receipt). Sales Invoice
  is handled in restrict_legacy_import_and_site_box.
- Disable Rounded Total: on by default and read-only on every sales and purchase document that has it.
- Stock Entry: BOM fields hidden (no BOM use), plus Add to Transit, Apply Putaway Rule and Inspection Required
  (0 uses).
"""
import frappe

SITE_HIDDEN = {
    "Journal Entry": "custom_site",
    "Payment Entry": "custom_site",
    "Purchase Order": "custom_site",
    "Purchase Invoice": "custom_site",
    "Purchase Receipt": "custom_site",
}
ROUNDING_DOCTYPES = ["Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order", "Delivery Note",
                     "Purchase Receipt", "Quotation", "Supplier Quotation"]
STOCK_ENTRY_HIDDEN = ["from_bom", "use_multi_level_bom", "bom_no", "fg_completed_qty",
                      "add_to_transit", "apply_putaway_rule", "inspection_required"]
BOM_SECTION_LABELS = {"BOM Info"}


def _setter(doc_type, fieldname, prop, value, ptype):
    if frappe.db.exists("Property Setter", {"doc_type": doc_type, "field_name": fieldname, "property": prop}):
        return
    frappe.get_doc({"doctype": "Property Setter", "doctype_or_field": "DocField", "doc_type": doc_type,
                    "field_name": fieldname, "property": prop, "property_type": ptype, "value": value}
                   ).insert(ignore_permissions=True)


def _safe(label, fn):
    frappe.db.savepoint("advanced_cleanup")
    try:
        fn()
    except Exception as exc:
        frappe.db.rollback(save_point="advanced_cleanup")
        print(f"advanced_cleanup: skipped {label}: {exc!r}"[:300])


def execute():
    for doc_type, fieldname in SITE_HIDDEN.items():
        if frappe.get_meta(doc_type).has_field(fieldname):
            _safe(f"{doc_type}.{fieldname}", lambda d=doc_type, f=fieldname: _setter(d, f, "hidden", "1", "Check"))
    for doc_type in ROUNDING_DOCTYPES:
        if not frappe.get_meta(doc_type).has_field("disable_rounded_total"):
            continue
        _safe(f"{doc_type} rounding on", lambda d=doc_type: _setter(d, "disable_rounded_total", "default", "1", "Data"))
        _safe(f"{doc_type} rounding read-only", lambda d=doc_type: _setter(d, "disable_rounded_total", "read_only", "1", "Check"))
    meta = frappe.get_meta("Stock Entry")
    for fieldname in STOCK_ENTRY_HIDDEN:
        if meta.has_field(fieldname):
            _safe(f"Stock Entry.{fieldname}", lambda f=fieldname: _setter("Stock Entry", f, "hidden", "1", "Check"))
    for field in meta.fields:
        if field.fieldtype == "Section Break" and (field.label or "") in BOM_SECTION_LABELS:
            _safe(f"Stock Entry section {field.fieldname}",
                  lambda f=field.fieldname: _setter("Stock Entry", f, "hidden", "1", "Check"))
    frappe.clear_cache()
