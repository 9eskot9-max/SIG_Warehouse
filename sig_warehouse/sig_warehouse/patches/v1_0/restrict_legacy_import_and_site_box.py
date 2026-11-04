"""v16: UI-only tidy-up of Sales Invoice (no data changes, nothing blocked on save).

1. Legacy Import (ZATCA Exempt) is shown only to System Manager and Accounts Manager. New invoices are never
   legacy imports (7 of 39 invoices created since 1 October 2026 were ticked; this stops that).
2. The single Site box on Sales Invoice is hidden. Nothing on invoices reads it. The Tawal Site & Cycle Links
   table stays, because that table is used.
"""
import frappe

LEGACY_FIELD = "custom_is_legacy_import"
LEGACY_DEPENDS = ("eval:frappe.user_roles.includes('System Manager') || "
                  "frappe.user_roles.includes('Accounts Manager')")
SITE_FIELD = "custom_site"


def _custom_field(dt, fieldname):
    return frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")


def _restrict_legacy_flag():
    name = _custom_field("Sales Invoice", LEGACY_FIELD)
    if not name:
        print("restrict: legacy import field not found")
        return
    doc = frappe.get_doc("Custom Field", name)
    if doc.get("depends_on") != LEGACY_DEPENDS:
        doc.depends_on = LEGACY_DEPENDS
        doc.flags.ignore_permissions = True
        doc.save()


def _hide_property(doc_type, fieldname, prop, value, ptype):
    if frappe.db.exists("Property Setter", {"doc_type": doc_type, "field_name": fieldname, "property": prop}):
        return
    frappe.get_doc({"doctype": "Property Setter", "doctype_or_field": "DocField", "doc_type": doc_type,
                    "field_name": fieldname, "property": prop, "property_type": ptype, "value": value}
                   ).insert(ignore_permissions=True)


def execute():
    frappe.db.savepoint("restrict_legacy_site")
    try:
        _restrict_legacy_flag()
        _hide_property("Sales Invoice", SITE_FIELD, "hidden", "1", "Check")
    except Exception as exc:
        frappe.db.rollback(save_point="restrict_legacy_site")
        print(f"restrict: skipped: {exc!r}"[:300])
        return
    frappe.clear_cache(doctype="Sales Invoice")
