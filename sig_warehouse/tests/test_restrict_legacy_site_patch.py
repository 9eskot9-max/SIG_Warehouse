import ast
from pathlib import Path

PATCH = Path(__file__).resolve().parents[1] / "sig_warehouse" / "patches" / "v1_0" / "restrict_legacy_import_and_site_box.py"


def test_patch_parses_and_targets_the_two_fields():
    source = PATCH.read_text(encoding="utf-8")
    ast.parse(source)
    assert '"custom_is_legacy_import"' in source and '"custom_site"' in source
    assert "System Manager" in source and "Accounts Manager" in source
    assert "Tawal" in source  # the table is documented as kept
