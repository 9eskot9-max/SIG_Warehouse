from types import SimpleNamespace

from sig_warehouse.sig_warehouse.stage5_as_built import build_as_built_rows, summarize_as_built


def test_as_built_uses_stage3_return_and_custody_allocations():
    sources = [SimpleNamespace(name="SE-1", posting_date="2026-09-15")]
    lines = [SimpleNamespace(
        name="SED-1", parent="SE-1", item_code="ITEM-1", qty=10, uom="Nos",
        custom_site="SITE-1", project="PROJ-1", custom_row_key="ROW-1",
        custom_qty_returned=2, custom_qty_custody=3,
        custom_return_disposition="PARTIAL",
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
        custom_return_disposition=None,
    )]
    row = build_as_built_rows(sources, lines)[0]
    assert row["as_built_qty"] == 0
    assert row["exceptions"] == ["MISSING_SITE", "NON_SITE_TRANSFER"]
