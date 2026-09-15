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


def _submitted_sources(from_date=None, to_date=None):
    filters = {"docstatus": 1, "is_return": 0, "purpose": ["in", PURPOSES]}
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
        filters.setdefault("posting_date", ["<=", to_date])
    return frappe.get_all(
        "Stock Entry", filters=filters,
        fields=["name", "posting_date", "purpose"], limit_page_length=0,
    )


def _line_rows(sources, site=None, project=None):
    if not sources:
        return []
    filters = {"parent": ["in", [row.name for row in sources]], "parenttype": "Stock Entry"}
    if site:
        filters["custom_site"] = site
    if project:
        filters["project"] = project
    return frappe.get_all(
        "Stock Entry Detail", filters=filters,
        fields=[
            "name", "parent", "item_code", "qty", "uom", "custom_site", "project",
            "custom_row_key", "custom_qty_returned", "custom_qty_custody",
            "custom_return_disposition",
        ], limit_page_length=0,
    )


def _as_built_line(row, source_by_name):
    issued = float(row.qty or 0)
    returned = max(0.0, float(row.custom_qty_returned or 0))
    custody = max(0.0, float(row.custom_qty_custody or 0))
    # Do not let a bad historical row make the report claim negative
    # consumption. The exception remains visible to the caller.
    source = source_by_name[str(row.parent)]
    flags = []
    if returned + custody > issued + EPS:
        flags.append("ALLOCATION_EXCEEDS_ISSUED")
    if not row.custom_site:
        flags.append("MISSING_SITE")
    # A store-to-store transfer is not site consumption merely because it has
    # a Stock Entry Detail row.  Only a transfer explicitly tagged to a site
    # is included in the As-Built quantity; the untagged movement remains an
    # auditable exception rather than silently inflating project consumption.
    purpose = getattr(source, "purpose", None)
    if purpose == "Material Transfer" and not row.custom_site:
        flags.append("NON_SITE_TRANSFER")
        consumed = 0.0
    else:
        consumed = max(0.0, issued - returned - custody)
    return {
        "stock_entry": row.parent,
        "posting_date": str(source.posting_date),
        "purpose": purpose,
        "item_code": row.item_code,
        "uom": row.uom,
        "site": row.custom_site,
        "project": row.project,
        "row_key": row.custom_row_key,
        "issued_qty": issued,
        "returned_qty": returned,
        "custody_qty": custody,
        "as_built_qty": consumed,
        "disposition": row.custom_return_disposition,
        "exceptions": flags,
    }


def build_as_built_rows(sources, lines, site=None, project=None):
    """Pure row transformation, useful for a report and fixture tests."""
    source_by_name = {str(row.name): row for row in sources}
    return [_as_built_line(row, source_by_name) for row in lines]


def summarize_as_built(rows):
    aggregate = defaultdict(float)
    exceptions = []
    for row in rows:
        key = (row["site"], row["project"], row["item_code"], row["uom"])
        aggregate[key] += row["as_built_qty"]
        if row["exceptions"]:
            exceptions.append(row)
    return {
        "rows": [
            {"site": key[0], "project": key[1], "item_code": key[2], "uom": key[3], "as_built_qty": qty}
            for key, qty in sorted(aggregate.items(), key=lambda pair: tuple(str(x or "") for x in pair[0]))
        ],
        "exception_count": len(exceptions),
        "exceptions": exceptions,
    }


@frappe.whitelist()
def sig_get_as_built(site=None, project=None, from_date=None, to_date=None):
    """Return ERP-derived As-Built quantities; no document is mutated."""
    sources = _submitted_sources(from_date, to_date)
    lines = _line_rows(sources, site=site, project=project)
    rows = build_as_built_rows(sources, lines, site=site, project=project)
    result = summarize_as_built(rows)
    result.update({"result": "ok", "source_documents": len(sources), "source_lines": len(rows)})
    return result
