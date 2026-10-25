"""Show SIG Site in each document's own Connections panel (doc -> Site direction).

The form dashboard of Material Request etc. lists linked documents (Sales Order,
Project, Cost Center...) but has no entry for the custom Site field. Each hook
below adds one "Site" group using the field that holds the SIG Site link.
"""


def _add_site(data, fieldname):
    data.setdefault("internal_links", {})["SIG Site"] = fieldname
    if not any(g.get("label") == "Site" for g in data.get("transactions", [])):
        data.setdefault("transactions", []).append({"label": "Site", "items": ["SIG Site"]})
    return data


def _ensure_connection_group(data, label, items):
    """Keep required Site Cycle connections in the Field Ops group."""
    transactions = data.setdefault("transactions", [])
    group = next((g for g in transactions if g.get("label") == label), None)
    if group is None:
        group = {"label": label, "items": []}
        transactions.append(group)

    group_items = group.setdefault("items", [])
    for item in items:
        if item not in group_items:
            group_items.append(item)
    return data


def material_request(data):
    return _add_site(data, "custom_site")


def stock_entry(data):
    data = _add_site(data, "custom_site")
    # Native Stock Entry dashboard omits Material Request (it has one at the item-row level,
    # `items.material_request`) even though Material Request's own dashboard already shows
    # Stock Entry - so the link was only visible from one side. STE-2026-0902 (owner report,
    # 2026-09-22) had items.material_request set but no Connections entry pointing back to it.
    data.setdefault("internal_links", {})["Material Request"] = ["items", "material_request"]
    for group in data.get("transactions", []):
        if group.get("label") == "Reference":
            if "Material Request" not in group["items"]:
                group["items"].append("Material Request")
            break
    else:
        data.setdefault("transactions", []).append({"label": "Reference", "items": ["Material Request"]})
    return data


def delivery_note(data):
    return _add_site(data, "custom_site")


def purchase_receipt(data):
    return _add_site(data, "custom_site")


def sales_order(data):
    return _add_site(data, "custom_site")


def sales_invoice(data):
    # Historical Tawal invoices can reference several sites. The invoice's
    # read-only child table is the authoritative multi-site relationship, so
    # expose its Link field in the standard Connections panel.
    return _add_site(data, ["custom_tawal_site_cycle_links", "site"])


def purchase_order(data):
    return _add_site(data, "custom_site")


def purchase_invoice(data):
    return _add_site(data, "custom_site")


def payment_entry(data):
    return _add_site(data, "custom_site")


def journal_entry(data):
    return _add_site(data, "custom_site")


def asset(data):
    return _add_site(data, "custom_sig_site")


def site_cycle(data):
    # `site_id` is retained even on older Cycles whose optional Site Link is blank.
    # Frappe v15 skips dashboard overrides for custom DocTypes; the app-owned
    # client bridge also renders this relationship until the DocType is adopted.
    data.setdefault("internal_links", {})["SIG Site"] = "site_id"
    return _ensure_connection_group(data, "Field Ops", ["SIG Site"])


def project(data):
    """Show Site Cycles that explicitly link to this ERP Project."""
    # Project uses `project` for its native transactions. Site Cycles use the
    # explicit Project Link `project_ref`, so keep that non-standard reverse
    # link separate from the native ERPNext project transactions.
    data.setdefault("fieldname", "project")
    data.setdefault("non_standard_fieldnames", {})["SIG Site Cycle"] = "project_ref"
    return _ensure_connection_group(data, "Field Ops", ["SIG Site Cycle"])


def field_visit(data):
    return _add_site(data, "site")


def tawal_invoice_link(data):
    return _add_site(data, "site")


def evidence_event(data):
    return _add_site(data, "site")


def field_session(data):
    return _add_site(data, "site")


def asset_movement(data):
    # Two site fields exist (from/to); internal_links takes one, so show the destination.
    return _add_site(data, "custom_sig_site_to")
