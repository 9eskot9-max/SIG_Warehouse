from sig_warehouse.sig_warehouse.asset_ops import validate_dispatch


def test_employee_needs_employee():
    assert validate_dispatch("Employee", None, None, "In Store")
    assert validate_dispatch("Employee", "E1", None, "In Store") is None


def test_site_needs_location():
    assert validate_dispatch("Site", None, None, "In Store")
    assert validate_dispatch("Site", None, "Site A", None) is None


def test_issued_asset_cannot_be_redispatched():
    assert "not in store" in validate_dispatch("Employee", "E1", None, "Issued - Employee")


def test_bad_dest():
    assert validate_dispatch("Moon", "E1", "X", None)
