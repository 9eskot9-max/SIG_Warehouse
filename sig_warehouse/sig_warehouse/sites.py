"""Controlled, idempotent creation of operational SIG Site records from RV80.

RV80 remains the source for SitesDB additions. This endpoint only creates site
records that do not already exist by site_id; it never edits existing sites.
"""
import frappe


MAX_BATCH = 200


def _require_site_master_access():
    if not ({"System Manager", "Warehouse Manager"} & set(frappe.get_roles())):
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
    if not frappe.has_permission("SIG Site", "create"):
        frappe.throw(frappe._("You need SIG Site create permission to add sites."), frappe.PermissionError)


def _text(value):
    if value is None:
        return ""
    return str(value).replace("\u00a0", " ").strip()


@frappe.whitelist(methods=["POST"])
def ensure_sites_from_rv80(sites=None):
    """Create missing SIG Sites from ``[{site_id, site_name}]`` in small batches.

    Repeated submissions are safe: existing records are returned as existing,
    and only new site IDs are inserted. The caller must be a System Manager or
    Warehouse Manager with normal SIG Site create permission.
    """
    _require_site_master_access()
    if isinstance(sites, str):
        sites = frappe.parse_json(sites)
    if not isinstance(sites, (list, tuple)):
        frappe.throw(frappe._("sites must be a JSON list."))
    if not sites or len(sites) > MAX_BATCH:
        frappe.throw(frappe._("Submit between 1 and {0} sites per batch.").format(MAX_BATCH))

    unique = {}
    for row in sites:
        if not isinstance(row, dict):
            frappe.throw(frappe._("Each site must contain site_id and site_name."))
        site_id = _text(row.get("site_id")).upper()
        site_name = _text(row.get("site_name")) or site_id
        if not site_id:
            frappe.throw(frappe._("A site_id is required for every site."))
        if len(site_id) > 140 or len(site_name) > 140:
            frappe.throw(frappe._("Site ID and name must be 140 characters or fewer."))
        unique.setdefault(site_id, site_name)

    ids = list(unique)
    existing_rows = frappe.get_all(
        "SIG Site", filters={"site_id": ["in", ids]}, fields=["name", "site_id"]
    )
    existing = {str(row.site_id).upper(): row.name for row in existing_rows}
    created = []
    for site_id, site_name in unique.items():
        if site_id in existing:
            continue
        doc = frappe.get_doc({
            "doctype": "SIG Site",
            "site_id": site_id,
            "site_name": site_name,
        })
        doc.insert()
        created.append(site_id)

    readback = frappe.get_all("SIG Site", filters={"site_id": ["in", ids]}, fields=["site_id"])
    verified = {str(row.site_id).upper() for row in readback}
    missing = [site_id for site_id in ids if site_id not in verified]
    if missing:
        frappe.throw(frappe._("SIG Site read-back missed: {0}").format(", ".join(missing[:10])))

    return {
        "result": "ok",
        "requested": len(ids),
        "created": len(created),
        "existing": len(ids) - len(created),
        "readback_ok": True,
    }
