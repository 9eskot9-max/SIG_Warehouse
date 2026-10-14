"""Stage 5 As-Built read model.

This is intentionally read-only and has no hooks. It consumes the Stage 3
return/custody fields on Stock Entry Detail and therefore can be deployed only
after that contract is migrated. It never writes stock, MR status, custody,
or dashboard fields.
"""
from collections import defaultdict

try:  # Keep pure report transforms importable in local/offline tests.
    import frappe
except ImportError:  # pragma: no cover - only used outside a Frappe site
    class _FrappeStub:
        @staticmethod
        def whitelist(fn=None, **_kwargs):
            if fn is not None and callable(fn):
                return fn
            return lambda wrapped: wrapped

    frappe = _FrappeStub()

EPS = 1e-6
PURPOSES = ("Material Issue", "Material Transfer")


def _is_closed(value):
    return value in (1, True, "1", "Yes", "yes")


def _return_closed_is_readable():
    if not frappe.has_permission("Stock Entry", "read"):
        return False
    field = frappe.get_meta("Stock Entry Detail").get_field("custom_return_closed")
    if not field:
        return False
    permlevel = int(getattr(field, "permlevel", 0) or 0)
    if not permlevel:
        return True
    roles = set(frappe.get_roles(frappe.session.user)) | {"All"}
    return any(
        str(getattr(permission, "role", "")) in roles
        and int(getattr(permission, "permlevel", 0) or 0) == permlevel
        and getattr(permission, "read", 0) in (1, True, "1", "Yes", "yes")
        for permission in frappe.get_meta("Stock Entry").permissions
    )


def _field_is_readable(doctype, fieldname):
    """Check the field's permission level against this user's effective roles."""
    permission_doctype = "Stock Entry" if doctype == "Stock Entry Detail" else doctype
    if not frappe.has_permission(permission_doctype, "read"):
        return False
    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field:
        return False
    permlevel = int(getattr(field, "permlevel", 0) or 0)
    if not permlevel:
        return True
    roles = set(frappe.get_roles(frappe.session.user)) | {"All"}
    return any(
        str(getattr(permission, "role", "")) in roles
        and int(getattr(permission, "permlevel", 0) or 0) == permlevel
        and getattr(permission, "read", 0) in (1, True, "1", "Yes", "yes")
        for permission in frappe.get_meta(permission_doctype).permissions
    )


def _submitted_sources(from_date=None, to_date=None):
    if not frappe.has_permission("Stock Entry", "read"):
        frappe.throw("Not permitted to read Stock Entry", frappe.PermissionError)
    filters = {"docstatus": 1, "is_return": 0, "purpose": ["in", PURPOSES]}
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
        filters.setdefault("posting_date", ["<=", to_date])
    rows, start = [], 0
    while True:
        batch = frappe.get_list(
            "Stock Entry", filters=filters,
            fields=["name", "posting_date", "purpose"],
            order_by="posting_date asc, name asc", start=start, page_length=500,
        )
        rows.extend(batch)
        if len(batch) < 500:
            return rows
        start += len(batch)


def _line_rows(sources, site=None, project=None, include_return_closed=True):
    if not sources:
        return []
    filters = {"parent": ["in", [row.name for row in sources]], "parenttype": "Stock Entry"}
    if site:
        filters["custom_site"] = site
    if project:
        filters["project"] = project
    fields = [
        "name", "parent", "item_code", "qty", "uom", "custom_site", "project",
        "material_request",
        "custom_row_key", "custom_qty_returned", "custom_qty_custody",
        "custom_return_disposition",
    ]
    if include_return_closed:
        fields.append("custom_return_closed")
    return frappe.get_all(
        "Stock Entry Detail", filters=filters,
        fields=fields, limit_page_length=0,
    )


def _as_built_line(row, source_by_name):
    issued = float(getattr(row, "qty", 0) or 0)
    returned = max(0.0, float(getattr(row, "custom_qty_returned", 0) or 0))
    custody = max(0.0, float(getattr(row, "custom_qty_custody", 0) or 0))
    # Do not let a bad historical row make the report claim negative
    # consumption. The exception remains visible to the caller.
    source = source_by_name[str(row.parent)]
    flags = []
    if returned + custody > issued + EPS:
        flags.append("ALLOCATION_EXCEEDS_ISSUED")
    site = getattr(row, "custom_site", None)
    if not site:
        flags.append("MISSING_SITE")
    # A store-to-store transfer is not site consumption merely because it has
    # a Stock Entry Detail row.  Only a transfer explicitly tagged to a site
    # is included in the As-Built quantity; the untagged movement remains an
    # auditable exception rather than silently inflating project consumption.
    purpose = getattr(source, "purpose", None)
    if purpose == "Material Transfer" and not site:
        flags.append("NON_SITE_TRANSFER")
        consumed = 0.0
    else:
        consumed = max(0.0, issued - returned - custody)
    return {
        "stock_entry": row.parent,
        "posting_date": str(source.posting_date),
        "purpose": purpose,
        "item_code": getattr(row, "item_code", None),
        "uom": getattr(row, "uom", None),
        "site": site,
        "project": getattr(row, "project", None),
        "row_key": getattr(row, "custom_row_key", None),
        "issued_qty": issued,
        "returned_qty": returned,
        "custody_qty": custody,
        "as_built_qty": consumed,
        "operational_closed": (
            _is_closed(getattr(row, "custom_return_closed", 0))
            if hasattr(row, "custom_return_closed") else None
        ),
        "disposition": getattr(row, "custom_return_disposition", None),
        "exceptions": flags,
    }


def build_as_built_rows(sources, lines, site=None, project=None):
    """Pure row transformation, useful for a report and fixture tests."""
    source_by_name = {str(row.name): row for row in sources}
    return [_as_built_line(row, source_by_name) for row in lines]


def summarize_as_built(rows):
    aggregate = defaultdict(float)
    operational_closed = {}
    exceptions = []
    for row in rows:
        key = (row["site"], row["project"], row["item_code"], row["uom"])
        aggregate[key] += row["as_built_qty"]
        if row["operational_closed"] is True:
            operational_closed[key] = True
        elif key not in operational_closed and row["operational_closed"] is False:
            operational_closed[key] = False
        if row["exceptions"]:
            exceptions.append(row)
    return {
        "rows": [
            {"site": key[0], "project": key[1], "item_code": key[2], "uom": key[3],
             "as_built_qty": qty, "operational_closed": operational_closed.get(key)}
            for key, qty in sorted(aggregate.items(), key=lambda pair: tuple(str(x or "") for x in pair[0]))
        ],
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "operational_closed_lines": (
            sum(1 for row in rows if row["operational_closed"] is True)
            if any(row["operational_closed"] is not None for row in rows) else None
        ),
    }


@frappe.whitelist()
def sig_get_as_built(site=None, project=None, from_date=None, to_date=None):
    """Return ERP-derived As-Built quantities; no document is mutated."""
    sources = _submitted_sources(from_date, to_date)
    return_closed_visible = _return_closed_is_readable()
    lines = _line_rows(sources, site=site, project=project, include_return_closed=return_closed_visible)
    rows = build_as_built_rows(sources, lines, site=site, project=project)
    result = summarize_as_built(rows)
    result.update({"result": "ok", "source_documents": len(sources), "source_lines": len(rows),
                   "operational_closure_access": "available" if return_closed_visible else "restricted"})
    return result


@frappe.whitelist()
def sig_get_as_built_for_abdraft():
    """Read-only, line-level ERP source contract for SIGPC's ABDraft rebuild.

    The caller must be able to read Stock Entry, Material Request and the return
    allocation fields. This method does not bypass the caller's document or
    field permissions and never writes Mapping AB or ERP stock data.
    """
    if not frappe.has_permission("Stock Entry", "read"):
        frappe.throw("Not permitted to read Stock Entry for As-Built import", frappe.PermissionError)
    if not frappe.has_permission("Material Request", "read"):
        frappe.throw("Not permitted to read Material Request for As-Built import", frappe.PermissionError)
    for fieldname in ("custom_qty_returned", "custom_qty_custody", "custom_return_closed", "custom_return_disposition"):
        if not _field_is_readable("Stock Entry Detail", fieldname):
            frappe.throw(f"Not permitted to read Stock Entry Detail.{fieldname}", frappe.PermissionError)
    if not _field_is_readable("Material Request", "custom_po_number"):
        frappe.throw("Not permitted to read Material Request.custom_po_number", frappe.PermissionError)

    sources = _submitted_sources()
    lines = _line_rows(sources, include_return_closed=True)
    if not lines:
        return {
            "result": "ok", "contract": "sigpc_abdraft_v1", "complete": False,
            "source_documents": len(sources), "source_lines": 0,
            "integrity_errors": ["ERP returned no submitted outbound DN lines; existing ABDraft must be preserved."],
            "pending_groups": [], "rows": [],
        }

    mr_names = sorted({str(row.material_request) for row in lines if row.material_request})
    mr_by_name = {}
    if mr_names:
        start = 0
        while True:
            batch = frappe.get_list(
                "Material Request",
                filters={"name": ["in", mr_names]},
                fields=["name", "custom_po_number"],
                order_by="name asc", start=start, page_length=500,
            )
            mr_by_name.update({str(row.name): row for row in batch})
            if len(batch) < 500:
                break
            start += len(batch)

    source_by_name = {str(row.name): row for row in sources}
    derived = build_as_built_rows(sources, lines)
    output_rows = []
    pending_groups = {}
    integrity_errors = []
    for line, calculated in zip(lines, derived):
        mr_name = str(line.material_request or "")
        mr = mr_by_name.get(mr_name)
        po_number = str(getattr(mr, "custom_po_number", "") or "").strip() if mr else ""
        site = str(line.custom_site or "").strip()
        disposition = str(line.custom_return_disposition or "").strip().upper()
        returned = float(line.custom_qty_returned or 0)
        custody = float(line.custom_qty_custody or 0)
        issued = float(line.qty or 0)
        operational_closed = bool(line.custom_return_closed)
        resolved = (
            operational_closed
            or returned + custody + EPS >= issued
            or disposition in ("RETURNED", "IN_HAND", "CONSUMED_CLOSED")
        )
        return_pending = not resolved

        if not mr_name or not mr:
            integrity_errors.append(f"{line.parent}/{line.name}: linked Material Request is missing or unreadable")
        if not po_number:
            integrity_errors.append(f"{line.parent}/{line.name}: Material Request has no PO/BA")
        if not site:
            integrity_errors.append(f"{line.parent}/{line.name}: site is missing")
        if calculated["exceptions"]:
            integrity_errors.append(
                f"{line.parent}/{line.name}: " + ", ".join(calculated["exceptions"])
            )
        if return_pending and site and po_number:
            pending_groups[(site, po_number)] = True

        output_rows.append({
            "source_dn": str(line.parent),
            "source_dn_line": str(line.name),
            "posting_date": str(source_by_name[str(line.parent)].posting_date),
            "material_request": mr_name,
            "site": site,
            "po_number": po_number,
            "item_code": str(line.item_code or ""),
            "uom": str(line.uom or ""),
            "row_key": str(line.custom_row_key or ""),
            "issued_qty": issued,
            "returned_qty": returned,
            "custody_qty": custody,
            "as_built_qty": calculated["as_built_qty"],
            "operational_closed": operational_closed,
            "disposition": disposition,
            "return_pending": return_pending,
            "exceptions": calculated["exceptions"],
        })

    return {
        "result": "ok",
        "contract": "sigpc_abdraft_v1",
        "complete": not integrity_errors,
        "source_documents": len(sources),
        "source_lines": len(lines),
        "integrity_errors": integrity_errors,
        "pending_groups": [
            {"site": site, "po_number": po_number}
            for site, po_number in sorted(pending_groups)
        ],
        "rows": output_rows,
    }
