from types import SimpleNamespace

from sig_warehouse.sig_warehouse.site_material_issue import single_line_site


def test_single_line_site_ignores_blank_rows_and_duplicates():
    assert single_line_site([
        SimpleNamespace(custom_site="Z95004"), SimpleNamespace(custom_site=""),
        SimpleNamespace(custom_site="Z95004"),
    ]) == "Z95004"


def test_single_line_site_refuses_to_summarize_multi_site_movement():
    assert single_line_site([
        SimpleNamespace(custom_site="Z95004"), SimpleNamespace(custom_site="Z95005"),
    ]) is None
