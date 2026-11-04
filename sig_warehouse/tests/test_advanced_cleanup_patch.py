import ast
from pathlib import Path

PATCH = Path(__file__).resolve().parents[1] / "sig_warehouse" / "patches" / "v1_0" / "advanced_cleanup_v1.py"


def test_patch_parses_and_covers_the_agreed_fields():
    source = PATCH.read_text(encoding="utf-8")
    ast.parse(source)
    for needle in ['"Journal Entry": "custom_site"', '"Purchase Receipt": "custom_site"', '"disable_rounded_total"',
                   '"use_multi_level_bom"', '"BOM Info"', '"default", "1"']:
        assert needle in source, needle
