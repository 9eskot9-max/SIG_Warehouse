from sig_warehouse.sig_warehouse.reconciliation import compare, summary


def test_compare_aggregates_duplicate_item_rows():
    rows = compare(
        [{"item_code": "A", "warehouse": "Main - SIG", "qty": "1"},
         {"item_code": "A", "warehouse": "Main - SIG", "qty": "2"}],
        [{"item_code": "A", "warehouse": "Main - SIG", "qty": "3"}],
    )
    assert rows[0]["match"] is True
    assert summary(rows)["mismatch_line_count"] == 0


def test_compare_reports_missing_erp_item():
    rows = compare(
        [{"item_code": "A", "warehouse": "Main - SIG", "qty": "1"}],
        [],
    )
    assert rows[0]["difference"] == "-1"
    assert summary(rows)["mismatch_line_count"] == 1
