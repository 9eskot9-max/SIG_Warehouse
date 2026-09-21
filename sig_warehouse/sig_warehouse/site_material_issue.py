"""Site-aware Material Issue indexing and lookup.

``SIG Site.site_id`` is the business site identifier.  Material Issue rows
store a Link to that document in ``Stock Entry Detail.custom_site``.  The
header ``Stock Entry.custom_site`` is deliberately a summary/index only: it
is populated when every tagged line belongs to one site, but is left empty
for a genuinely multi-site movement so it never asserts a false allocation.
"""
from collections import defaultdict

try:  # Keep the pure site-summary rule importable in local/offline tests.
    import frappe
    from frappe.utils import cint
except ImportError:  # pragma: no cover - only used outside a Frappe site
    def cint(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    class _FrappeStub:
        @staticmethod
        def whitelist(fn=None, **_kwargs):
            if fn is not None and callable(fn):
                return fn
            return lambda wrapped: wrapped

    frappe = _FrappeStub()


def _text(value):
    return str(value or "").strip()


def single_line_site(items):
    """Return the one tagged site on *items*, otherwise ``None``.

    Keeping this pure makes the no-false-summary rule testable without a
    Frappe site.
    """
    sites = set()
    for item in items or []:
        if isinstance(item, dict):
            value = item.get("custom_site")
        else:
            value = getattr(item, "custom_site", None)
        value = _text(value)
        if value:
            sites.add(value)
    return next(iter(sites)) if len(sites) == 1 else None


def sync_stock_entry_site_summary(doc, method=None):
    """Index a single-site Stock Entry at its header during insertion."""
    if not frappe.get_meta("Stock Entry").has_field("custom_site"):
        return
    site = single_line_site(getattr(doc, "items", None))
    header_site = canonical_sig_site_name(site)
    if header_site:
        # The child rows are the authoritative allocation.  Their sole site
        # is safe to mirror at the header for Frappe's list/global search.
        # The header is a Link, so it must contain the SIG Site document name,
        # not merely its human-facing Site ID.
        doc.custom_site = header_site


def canonical_sig_site_name(site):
    """Return the SIG Site document name for a Link-field header.

    Stock Entry Detail historically stores the business site ID (for example
    ``Z95004``), while Stock Entry.custom_site is a Link and stores the SIG
    Site document name (for example ``1``).  Keeping that conversion here
    prevents a valid line allocation from becoming an invalid header Link.
    """
    query = _text(site)
    if not query:
        return None
    if frappe.db.exists("SIG Site", query):
        return query
    return _text(frappe.db.get_value("SIG Site", {"site_id": query}, "name")) or None


def resolve_site_references(site):
    """Accept a SIG Site document name or its business ``site_id``."""
    query = _text(site)
    if not query:
        return []
    names = {query}  # supports historical rows whose Link stores the raw ID
    canonical_name = canonical_sig_site_name(query)
    if canonical_name:
        names.add(canonical_name)
    names.update(
        _text(row.name)
        for row in frappe.get_all("SIG Site", filters={"site_id": query}, fields=["name"])
        if _text(row.name)
    )
    return sorted(names)


def _issue_filters(docstatuses, from_date=None, to_date=None):
    filters = {"purpose": "Material Issue", "docstatus": ["in", docstatuses]}
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    elif to_date:
        filters["posting_date"] = ["<=", to_date]
    return filters


@frappe.whitelist()
def sig_find_material_issues_by_site(site, from_date=None, to_date=None, include_drafts=0):
    """Return Material Issues matching a site ID or a ``custom_site`` Link.

    The result unions the header index with the authoritative child-line
    allocation, so older entries with a blank header and multi-site entries
    are still discoverable.
    """
    if not frappe.has_permission("Stock Entry", "read"):
        frappe.throw("Not permitted to read Stock Entry", frappe.PermissionError)
    references = resolve_site_references(site)
    if not references:
        return {"result": "ok", "site_input": _text(site), "site_references": [], "count": 0,
                "material_issues": []}

    docstatuses = [0, 1] if cint(include_drafts) else [1]
    filters = _issue_filters(docstatuses, from_date, to_date)
    header_rows = frappe.get_all(
        "Stock Entry", filters={**filters, "custom_site": ["in", references]}, fields=["name"],
        limit_page_length=0,
    )
    line_rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"parenttype": "Stock Entry", "custom_site": ["in", references]},
        fields=["parent"], limit_page_length=0,
    )
    names = {str(row.name) for row in header_rows}
    candidate_names = {str(row.parent) for row in line_rows if row.parent}
    if candidate_names:
        matched_rows = frappe.get_all(
            "Stock Entry", filters={**filters, "name": ["in", sorted(candidate_names)]}, fields=["name"],
            limit_page_length=0,
        )
        names.update(str(row.name) for row in matched_rows)

    rows = frappe.get_all(
        "Stock Entry", filters={"name": ["in", sorted(names)]} if names else {"name": ["in", []]},
        fields=["name", "posting_date", "docstatus", "custom_site", "custom_source_id", "remarks"],
        order_by="posting_date desc, name desc", limit_page_length=0,
    ) if names else []
    return {
        "result": "ok", "site_input": _text(site), "site_references": references,
        "count": len(rows), "material_issues": [row.as_dict() for row in rows],
    }


@frappe.whitelist()
def sig_backfill_material_issue_site_summaries(apply=0, limit=5000):
    """Fill blank headers only when child rows prove a single site.

    Multi-site and untagged records are reported but never guessed.  The
    default is a dry run; applying requires a System Manager session.
    """
    apply = cint(apply)
    if apply:
        frappe.only_for("System Manager")
    headers = frappe.get_all(
        "Stock Entry", filters={"purpose": "Material Issue", "docstatus": ["in", [0, 1]]},
        fields=["name", "custom_site"], order_by="posting_date asc, name asc",
        limit_page_length=max(1, min(cint(limit) or 5000, 10000)),
    )
    blank_names = [row.name for row in headers if not _text(row.custom_site)]
    detail_by_parent = defaultdict(list)
    if blank_names:
        for row in frappe.get_all(
            "Stock Entry Detail",
            filters={"parent": ["in", blank_names], "parenttype": "Stock Entry"},
            fields=["parent", "custom_site"], limit_page_length=0,
        ):
            detail_by_parent[str(row.parent)].append(row)

    filled, multi_site, untagged, unresolved = [], [], [], []
    for name in blank_names:
        site = single_line_site(detail_by_parent.get(str(name), []))
        tagged = {_text(row.custom_site) for row in detail_by_parent.get(str(name), []) if _text(row.custom_site)}
        header_site = canonical_sig_site_name(site)
        if header_site:
            filled.append({"stock_entry": name, "site_id": site, "site": header_site})
            if apply:
                frappe.db.set_value("Stock Entry", name, "custom_site", header_site, update_modified=False)
                frappe.clear_document_cache("Stock Entry", name)
        elif site:
            unresolved.append({"stock_entry": name, "site_id": site})
        elif tagged:
            multi_site.append(name)
        else:
            untagged.append(name)
    if apply and filled:
        frappe.db.commit()
    return {
        "result": "applied" if apply else "dry_run", "considered": len(blank_names),
        "fillable": len(filled), "filled": filled, "multi_site": multi_site,
        "untagged": untagged, "unresolved_site_ids": unresolved,
    }
