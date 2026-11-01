"""Form layout tidy-up for v16 (data only, no imports). Applied by patches/v1_0/tidy_form_layouts.py.

CF = custom field changes: (doctype, fieldname, {property: value}); PS = property setters on standard or
custom-doctype fields: (doctype, fieldname, property, value, type).
"""
PC = "eval:doc.custom_pc_clearance"

CF = [
    # Journal Entry: one petty-cash trigger in the header, the rest only when it is a clearance.
    ("Journal Entry", "custom_entry_type", {"label": "Entry Category"}),
    ("Journal Entry", "custom_pc_clearance_category", {"depends_on": PC}),
    ("Journal Entry", "custom_pc_clearance_source", {"depends_on": PC}),
    ("Journal Entry", "custom_pc_receipt", {"depends_on": "eval:doc.custom_pc_clearance || doc.custom_pc_receipt"}),
    ("Journal Entry", "custom_pc_funding_section", {"label": "Petty Cash", "collapsible": 1,
                                                    "collapsible_depends_on": "eval:doc.custom_pc_top_up"}),
    ("Journal Entry", "custom_site", {"insert_after": "user_remark"}),
    # Payment Entry
    ("Payment Entry", "custom_pc_purchase_invoice", {"depends_on": PC}),
    ("Payment Entry", "custom_pc_source", {"depends_on": PC}),
    ("Payment Entry", "custom_linkage_agent", {"read_only": 1, "depends_on": "eval:doc.custom_linkage_agent"}),
    ("Payment Entry", "custom_snb_idempotency_key", {"read_only": 1, "depends_on": "eval:doc.custom_snb_idempotency_key"}),
    # Sales Invoice
    ("Sales Invoice", "custom_is_legacy_import", {"insert_after": "custom_legacy_import_details",
                                                  "description": "Historical imports only."}),
    ("Sales Invoice", "custom_bank_account", {"insert_after": "custom_payment_means", "description": "Blank = default account."}),
    ("Sales Invoice", "custom_section_break_pz7hw", {"collapsible": 1,
                                                     "collapsible_depends_on": "eval:doc.custom_retention_percentage"}),
    # Material Request
    ("Material Request", "custom_sig_source_info_section", {"collapsible": 1,
                                                            "collapsible_depends_on": "eval:doc.custom_source_confirmed_by"}),
    ("Material Request", "custom_source_confirmed_by", {"read_only": 1}),
    ("Material Request", "custom_source_confirmed_at", {"read_only": 1}),
]

# Employee: Saudi compliance dates leave the top of the form and follow the passport/iqama block.
_emp = ["custom_iqama_expiry_date", "custom_passport_expiry_date", "custom_work_permit_expiry", "custom_border_number",
        "custom_gosi_number", "custom_gosi_registration_date", "custom_muqeem_report_date",
        "custom_sadad_pay_iqama_duration", "custom_sponsor_id", "custom_hr_remarks"]
_prev = "custom_iqama_status"
for _f in _emp:
    CF.append(("Employee", _f, {"insert_after": _prev}))
    _prev = _f

# Supplier: verification metadata moves under the supplier type.
_prev = "supplier_type"
for _f in ["custom_legal_name", "custom_provisional", "custom_provisional_verified", "custom_verified_by", "custom_supplier_doc_ref"]:
    CF.append(("Supplier", _f, {"insert_after": _prev}))
    _prev = _f

PS = [
    # SIG Site Cycle: system-computed blocks collapsed by default.
    ("SIG Site Cycle", "slots_section", "collapsible", "1", "Check"),
    ("SIG Site Cycle", "visits_section", "collapsible", "1", "Check"),
    ("SIG Site Cycle", "plan_section", "collapsible", "1", "Check"),
]
