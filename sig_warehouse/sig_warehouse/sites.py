"""Controlled synchronization of SIG Sites from RV80's Tawal import."""
import math
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
    """Ensure site IDs exist and optionally update their source coordinates and region.

    Coordinates must be supplied as a valid pair; absent values never erase data.
    The caller must have normal create and, for edits, write permissions.
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
        region = _text(row.get("region"))
        lat, lon = row.get("latitude"), row.get("longitude")
        if (lat is None or lat == "") != (lon is None or lon == ""):
            frappe.throw(frappe._("Latitude and longitude must be supplied together."))
        point = None
        if lat not in (None, ""):
            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                frappe.throw(frappe._("Invalid coordinates for {0}.").format(site_id))
            if not (math.isfinite(lat) and math.isfinite(lon) and 15 <= lat <= 33 and 34 <= lon <= 56):
                frappe.throw(frappe._("Invalid Saudi coordinates for {0}.").format(site_id))
            point = (lat, lon)
        if len(region) > 140:
            frappe.throw(frappe._("Region must be 140 characters or fewer."))
        candidate = {"site_name": site_name, "region": region, "point": point}
        if site_id in unique and unique[site_id] != candidate:
            frappe.throw(frappe._("Conflicting values for site {0}.").format(site_id))
        unique[site_id] = candidate

    ids = list(unique)
    existing_rows = frappe.get_all(
        "SIG Site", filters={"site_id": ["in", ids]}, fields=["name", "site_id"], limit_page_length=0
    )
    existing = {str(row.site_id).upper(): row.name for row in existing_rows}
    created, updated = [], []
    for site_id, values in unique.items():
        is_new = site_id not in existing
        doc = (frappe.get_doc({"doctype": "SIG Site", "site_id": site_id, "site_name": values["site_name"]})
               if is_new else frappe.get_doc("SIG Site", existing[site_id]))
        changes = {}
        if values["region"] and doc.get("region") != values["region"]:
            changes["region"] = values["region"]
        if values["point"]:
            lat, lon = values["point"]
            if (abs(float(doc.get("site_latitude") or 0) - lat) > 0.000001 or
                    abs(float(doc.get("site_longitude") or 0) - lon) > 0.000001):
                changes.update(site_latitude=lat, site_longitude=lon, geo_source="Tawal export")
        if changes:
            doc.update(changes)
        if is_new:
            doc.insert()
            created.append(site_id)
        elif changes:
            doc.save()
            updated.append(site_id)

    readback = frappe.get_all("SIG Site", filters={"site_id": ["in", ids]},
                              fields=["site_id", "region", "site_latitude", "site_longitude"], limit_page_length=0)
    verified = {str(row.site_id).upper(): row for row in readback}
    missing = [site_id for site_id in ids if site_id not in verified]
    if missing:
        frappe.throw(frappe._("SIG Site read-back missed: {0}").format(", ".join(missing[:10])))
    for site_id, values in unique.items():
        actual = verified[site_id]
        if values["region"] and actual.region != values["region"]:
            frappe.throw(frappe._("SIG Site region read-back failed for {0}.").format(site_id))
        if values["point"]:
            lat, lon = values["point"]
            if (abs(float(actual.site_latitude or 0) - lat) > 0.000001 or
                    abs(float(actual.site_longitude or 0) - lon) > 0.000001):
                frappe.throw(frappe._("SIG Site coordinate read-back failed for {0}.").format(site_id))

    return {
        "result": "ok",
        "sync_version": 2,
        "requested": len(ids),
        "created": len(created),
        "existing": len(ids) - len(created),
        "updated": len(updated),
        "readback_ok": True,
    }


@frappe.whitelist(methods=["POST"])
def sync_sites_from_rv80_v2(sites=None):
    """Versioned route prevents a newer RV80 client from writing through an old server."""
    return ensure_sites_from_rv80(sites)
