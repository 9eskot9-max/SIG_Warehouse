"""Limited public lookup for the field visit portal."""
import math
import frappe
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=3600)
def nearby_sites(latitude=None, longitude=None):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        frappe.throw("Valid coordinates are required.")
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        frappe.throw("Valid coordinates are required.")
    radius = 200
    dy = radius / 111320
    dx = radius / (111320 * max(0.01, math.cos(math.radians(lat))))
    filters = [["site_latitude", ">=", lat-dy], ["site_latitude", "<=", lat+dy],
               ["site_longitude", ">=", lon-dx], ["site_longitude", "<=", lon+dx]]
    sites, offset = [], 0
    while True:
        rows = frappe.get_all("SIG Site", filters=filters,
            fields=["site_id", "site_name", "site_latitude", "site_longitude"],
            order_by="name asc", limit_start=offset, limit_page_length=500)
        for row in rows:
            if row.site_latitude is None or row.site_longitude is None or not row.site_id:
                continue
            slat, slon = float(row.site_latitude), float(row.site_longitude)
            a = (math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) *
                 math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2)
            meters = 12742000 * math.asin(min(1, math.sqrt(a)))
            if meters <= radius:
                sites.append({"id": row.site_id, "name": row.site_name or row.site_id, "meters": round(meters)})
        if len(rows) < 500:
            break
        offset += len(rows)
    sites.sort(key=lambda site: (site["meters"], site["id"]))
    return {"radius": radius, "sites": sites[:10]}
