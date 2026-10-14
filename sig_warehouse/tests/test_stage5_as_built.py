from types import SimpleNamespace

from sig_warehouse.sig_warehouse import stage5_as_built
from sig_warehouse.sig_warehouse.stage5_as_built import build_as_built_rows, summarize_as_built


def test_as_built_uses_stage3_return_and_custody_allocations():
    sources = [SimpleNamespace(name="SE-1", posting_date="2026-09-15")]
    lines = [SimpleNamespace(
        name="SED-1", parent="SE-1", item_code="ITEM-1", qty=10, uom="Nos",
        custom_site="SITE-1", project="PROJ-1", custom_row_key="ROW-1",
        custom_qty_returned=2, custom_qty_custody=3,
        custom_return_disposition="PARTIAL", custom_return_closed=0,
    )]
    rows = build_as_built_rows(sources, lines)
    assert rows[0]["as_built_qty"] == 5
    assert summarize_as_built(rows)["exception_count"] == 0


def test_as_built_surfaces_over_allocation():
    sources = [SimpleNamespace(name="SE-1", posting_date="2026-09-15")]
    lines = [SimpleNamespace(
        name="SED-1", parent="SE-1", item_code="ITEM-1", qty=10, uom="Nos",
        custom_site="SITE-1", project=None, custom_row_key=None,
        custom_qty_returned=8, custom_qty_custody=4,
        custom_return_disposition="PARTIAL",
    )]
    rows = build_as_built_rows(sources, lines)
    assert rows[0]["as_built_qty"] == 0
    assert rows[0]["exceptions"] == ["ALLOCATION_EXCEEDS_ISSUED"]


def test_untagged_transfer_is_not_site_consumption():
    sources = [SimpleNamespace(name="SE-2", posting_date="2026-09-15", purpose="Material Transfer")]
    lines = [SimpleNamespace(
        name="SED-2", parent="SE-2", item_code="ITEM-2", qty=4, uom="Nos",
        custom_site=None, project=None, custom_row_key="ROW-2",
        custom_qty_returned=0, custom_qty_custody=0,
        custom_return_disposition=None, custom_return_closed=0,
    )]
    row = build_as_built_rows(sources, lines)[0]
    assert row["as_built_qty"] == 0
    assert row["exceptions"] == ["MISSING_SITE", "NON_SITE_TRANSFER"]


def test_explicit_dn_return_closure_is_exposed_separately_from_as_built_qty():
    sources = [SimpleNamespace(name="SE-3", posting_date="2026-09-15", purpose="Material Issue")]
    lines = [SimpleNamespace(
        name="SED-3", parent="SE-3", item_code="ITEM-3", qty=10, uom="Nos",
        custom_site="SITE-3", project="PROJ-3", custom_row_key="ROW-3",
        custom_qty_returned=0, custom_qty_custody=0,
        custom_return_disposition="OPEN", custom_return_closed=1,
    )]
    rows = build_as_built_rows(sources, lines)
    summary = summarize_as_built(rows)
    assert rows[0]["as_built_qty"] == 10
    assert rows[0]["operational_closed"] is True
    assert summary["rows"][0]["operational_closed"] is True
    assert summary["operational_closed_lines"] == 1


def test_zero_return_quantity_is_not_operational_closure():
    sources = [SimpleNamespace(name="SE-4", posting_date="2026-09-15", purpose="Material Issue")]
    lines = [SimpleNamespace(
        name="SED-4", parent="SE-4", item_code="ITEM-4", qty=10, uom="Nos",
        custom_site="SITE-4", project="PROJ-4", custom_row_key="ROW-4",
        custom_qty_returned=0, custom_qty_custody=0,
        custom_return_disposition="OPEN", custom_return_closed=0,
    )]
    row = build_as_built_rows(sources, lines)[0]
    assert row["operational_closed"] is False


def test_return_closed_field_read_uses_its_permlevel_not_only_doctype_read(monkeypatch):
    frappe = stage5_as_built.frappe
    detail_meta = SimpleNamespace(get_field=lambda _field: SimpleNamespace(permlevel=1))
    stock_meta = SimpleNamespace(permissions=[
        SimpleNamespace(role="SIG Stock Viewer", permlevel=0, read=1),
        SimpleNamespace(role="SIG Stock Viewer", permlevel=1, read="0"),
        SimpleNamespace(role="Stock Manager", permlevel=1, read=1),
    ])
    monkeypatch.setattr(frappe, "has_permission", lambda *_args, **_kwargs: True, raising=False)
    monkeypatch.setattr(frappe, "get_meta", lambda doctype: detail_meta if doctype == "Stock Entry Detail" else stock_meta, raising=False)
    monkeypatch.setattr(frappe, "get_roles", lambda _user: ["SIG Stock Viewer"], raising=False)
    monkeypatch.setattr(frappe, "session", SimpleNamespace(user="viewer@example.com"), raising=False)
    assert stage5_as_built._return_closed_is_readable() is False
    monkeypatch.setattr(frappe, "get_roles", lambda _user: ["Stock Manager"], raising=False)
    assert stage5_as_built._return_closed_is_readable() is True


def test_erp_abdraft_export_contains_po_provenance_and_marks_pending_groups(monkeypatch):
    frappe = stage5_as_built.frappe
    monkeypatch.setattr(frappe, "has_permission", lambda *_args, **_kwargs: True, raising=False)
    monkeypatch.setattr(
        frappe,
        "get_meta",
        lambda _doctype: SimpleNamespace(
            get_field=lambda _field: SimpleNamespace(permlevel=0), permissions=[]
        ),
        raising=False,
    )
    monkeypatch.setattr(frappe, "get_roles", lambda _user: ["Stock Manager"], raising=False)
    monkeypatch.setattr(frappe, "session", SimpleNamespace(user="warehouse@example.com"), raising=False)

    source = SimpleNamespace(
        name="DN-1", posting_date="2026-10-01", purpose="Material Issue"
    )
    line = SimpleNamespace(
        name="DN-1-ROW-1", parent="DN-1", item_code="ITEM-1", qty=10, uom="Nos",
        custom_site="SITE-1", project="PROJ-1", material_request="MR-1",
        custom_row_key="ROW-1", custom_qty_returned=2, custom_qty_custody=1,
        custom_return_disposition="PARTIAL", custom_return_closed=0,
    )
    monkeypatch.setattr(stage5_as_built, "_submitted_sources", lambda: [source])
    monkeypatch.setattr(stage5_as_built, "_line_rows", lambda *_args, **_kwargs: [line])
    monkeypatch.setattr(
        frappe,
        "get_list",
        lambda _doctype, **_kwargs: [SimpleNamespace(name="MR-1", custom_po_number="PO-7")],
        raising=False,
    )

    result = stage5_as_built.sig_get_as_built_for_abdraft()

    assert result["contract"] == "sigpc_abdraft_v1"
    assert result["complete"] is True
    assert result["pending_groups"] == [{"site": "SITE-1", "po_number": "PO-7"}]
    assert result["rows"][0]["source_dn"] == "DN-1"
    assert result["rows"][0]["po_number"] == "PO-7"
    assert result["rows"][0]["as_built_qty"] == 7
    assert result["rows"][0]["return_pending"] is True


def test_erp_abdraft_export_with_no_lines_is_incomplete_and_safe_to_preserve(monkeypatch):
    frappe = stage5_as_built.frappe
    monkeypatch.setattr(frappe, "has_permission", lambda *_args, **_kwargs: True, raising=False)
    monkeypatch.setattr(
        frappe,
        "get_meta",
        lambda _doctype: SimpleNamespace(
            get_field=lambda _field: SimpleNamespace(permlevel=0), permissions=[]
        ),
        raising=False,
    )
    monkeypatch.setattr(frappe, "get_roles", lambda _user: ["Stock Manager"], raising=False)
    monkeypatch.setattr(frappe, "session", SimpleNamespace(user="warehouse@example.com"), raising=False)
    monkeypatch.setattr(stage5_as_built, "_submitted_sources", lambda: [])
    monkeypatch.setattr(stage5_as_built, "_line_rows", lambda *_args, **_kwargs: [])

    result = stage5_as_built.sig_get_as_built_for_abdraft()

    assert result["complete"] is False
    assert result["rows"] == []
    assert result["integrity_errors"]
