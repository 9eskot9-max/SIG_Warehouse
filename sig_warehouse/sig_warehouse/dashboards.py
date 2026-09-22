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
    return _add_site(data, "custom_site")


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
