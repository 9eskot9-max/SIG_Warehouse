"""Every string the Bank Router shows through __() / _() has an Arabic entry in ar.csv (the Workbench is used in Arabic)."""
import csv
import re
from pathlib import Path

APP = Path(__file__).parents[1]
JS_PATTERNS = [r"__\(\s*'((?:[^'\\]|\\.)*)'", r'__\(\s*"((?:[^"\\]|\\.)*)"', r"__\(\s*`((?:[^`\\]|\\.)*)`"]
PY_PATTERNS = [r'\b_\(\s*"((?:[^"\\]|\\.)*)"', r"\b_\(\s*'((?:[^'\\]|\\.)*)'"]


def router_strings():
    js = (APP / "sig_accounting/page/snb_movement_router/snb_movement_router.js").read_text(encoding="utf-8")
    py = (APP / "sig_accounting/snb_movement_router.py").read_text(encoding="utf-8")
    found = set()
    for pattern in JS_PATTERNS:
        found |= {m.group(1).replace("\\'", "'") for m in re.finditer(pattern, js)}
    for pattern in PY_PATTERNS:
        found |= {m.group(1).replace('\\"', '"').replace("\\'", "'") for m in re.finditer(pattern, py)}
    return found


def arabic():
    with open(APP / "translations/ar.csv", encoding="utf-8", newline="") as handle:
        return {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}


def test_every_router_string_has_an_arabic_translation():
    have = arabic()
    missing = sorted(s for s in router_strings() if not have.get(s, "").strip())
    assert not missing, f"{len(missing)} router strings lack Arabic, for example: {missing[:5]}"


def test_translations_keep_their_placeholders_and_are_arabic():
    have = arabic()
    for source in router_strings():
        target = have[source]
        for placeholder in ("{0}", "{1}"):
            assert (placeholder in source) == (placeholder in target), source
        if len(source) > 12 and source.isascii():
            assert re.search(r"[؀-ۿ]", target), f"not Arabic: {source}"
