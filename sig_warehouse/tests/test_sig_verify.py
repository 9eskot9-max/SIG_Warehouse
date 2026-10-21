import importlib.util
import io
from pathlib import Path

import pytest

from sig_warehouse.sig_verify import registry, tokens


# ---- registry -------------------------------------------------------------------------------

def test_quotation_is_registered_and_fields_are_declared():
    assert "Quotation" in registry.VERIFIABLE
    assert registry.query_fields("Quotation") == [
        "name", "docstatus", "transaction_date", "valid_till", "company", "grand_total", "currency",
    ]


def test_state_words():
    assert registry.state_for(1) == "Valid"
    assert registry.state_for(2) == "Cancelled"
    assert registry.state_for(0) == "Draft"
    assert registry.state_for(None) == "Draft"


def test_summary_reveals_only_the_agreed_facts():
    row = {
        "name": "QTN-26-060", "docstatus": 1, "transaction_date": "2026-10-21", "valid_till": "2026-11-20",
        "company": "SIG", "grand_total": 243725.25, "currency": "SAR",
        "customer": "Secret Customer", "items": ["x"], "contact_email": "a@b.c",
    }
    out = registry.summary("Quotation", row)
    assert out == {
        "valid": 1, "doctype": "Quotation", "name": "QTN-26-060", "state": "Valid",
        "date": "2026-10-21", "valid_till": "2026-11-20", "company": "SIG",
        "total": 243725.25, "currency": "SAR",
    }
    assert "customer" not in out and "items" not in out and "contact_email" not in out


def test_summary_tolerates_a_doctype_with_few_fields(monkeypatch):
    monkeypatch.setitem(registry.VERIFIABLE, "SIG Letter", {"date_field": "date"})
    out = registry.summary("SIG Letter", {"name": "L-1", "docstatus": 1, "date": "2026-10-21"})
    assert out["name"] == "L-1" and out["date"] == "2026-10-21"
    assert out["total"] is None and out["valid_till"] == "" and out["company"] == ""
    assert registry.query_fields("SIG Letter") == ["name", "docstatus", "date"]


def test_token_field_is_hidden_no_copy_and_allowed_after_submit():
    spec = registry.token_field_spec("Quotation")
    assert spec["fieldname"] == registry.TOKEN_FIELD == "custom_verify_token"
    assert spec["hidden"] == spec["read_only"] == spec["no_copy"] == spec["allow_on_submit"] == spec["print_hide"] == 1
    assert spec["insert_after"] == "naming_series"


def test_qr_file_name_matches_the_print_format_lookup():
    assert registry.qr_file_name("QTN-26-060") == "verify_qr_QTN-26-060.png"
    template = Path(__file__).resolve().parents[3].parent / "print_formats" / "sig_quotation_infographic.html"
    if template.exists():  # the print format looks the file up by this prefix
        assert f'"{registry.QR_FILE_PREFIX}%"' in template.read_text(encoding="utf-8-sig")


# ---- tokens ---------------------------------------------------------------------------------

def test_new_tokens_are_long_unique_and_unambiguous():
    seen = {tokens.new_token() for _ in range(2000)}
    assert len(seen) == 2000
    for token in list(seen)[:50]:
        assert len(token) == tokens.TOKEN_LENGTH
        assert set(token) <= set(tokens.ALPHABET)
        assert not set(token) & set("0O1lI")


def test_plausible_token_shape():
    assert tokens.is_plausible_token(tokens.new_token())
    for bad in (None, "", "short", "x" * 65, "has space in it!!!!!!", tokens.new_token() + "0", 12345):
        assert not tokens.is_plausible_token(bad)


def test_verify_url():
    assert tokens.verify_url("https://neosys.frappe.cloud/", "TOK") == "https://neosys.frappe.cloud/verify?t=TOK"


# ---- QR image -------------------------------------------------------------------------------

def test_qr_renders_a_png_that_decodes_at_print_and_screen_sizes():
    pyzbar = pytest.importorskip("pyzbar.pyzbar")
    from PIL import Image

    from sig_warehouse.sig_verify.qr_style import render_png

    url = tokens.verify_url("https://neosys.frappe.cloud", tokens.new_token())
    png = render_png(url)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    image = Image.open(io.BytesIO(png))
    for px in (976, 600, 400, 300, 220):
        found = pyzbar.decode(image.resize((px, px), Image.Resampling.LANCZOS))
        assert found and found[0].data == url.encode(), f"did not decode at {px}px"


def test_qr_matrix_falls_back_to_pyqrcode_when_qrcode_is_absent(monkeypatch):
    pytest.importorskip("pyqrcode")
    import builtins

    real_import = builtins.__import__

    def no_qrcode(name, *args, **kwargs):
        if name == "qrcode":
            raise ImportError("simulated: qrcode not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_qrcode)
    from sig_warehouse.sig_verify.qr_style import QR_BORDER_MODULES, _matrix

    url = "https://example.com/verify?t=abcdefghijklmnopqrst"
    matrix = _matrix(url)
    n = len(matrix)
    assert all(len(row) == n for row in matrix)
    assert not any(matrix[r][c] for r in range(QR_BORDER_MODULES) for c in range(n))  # quiet zone is blank
    assert matrix[QR_BORDER_MODULES][QR_BORDER_MODULES]  # top-left finder starts dark

    # the styled image built from the fallback matrix must still scan (this is the path Frappe will take)
    pyzbar = pytest.importorskip("pyzbar.pyzbar")
    from PIL import Image

    from sig_warehouse.sig_verify.qr_style import render_png

    image = Image.open(io.BytesIO(render_png(url)))
    for px in (976, 400, 220):
        found = pyzbar.decode(image.resize((px, px), Image.Resampling.LANCZOS))
        assert found and found[0].data == url.encode(), f"fallback render did not decode at {px}px"


# ---- wiring ---------------------------------------------------------------------------------

def test_hooks_register_on_submit_without_dropping_existing_handlers():
    from sig_warehouse import hooks

    assert hooks.doc_events["Quotation"]["on_submit"] == ["sig_warehouse.sig_verify.events.on_submit"]
    assert hooks.doc_events["Stock Entry"]["on_submit"] == "sig_warehouse.sig_warehouse.rollup.on_stock_entry_submit"


def test_patches_are_listed_with_full_paths_and_importable():
    patches_txt = Path(__file__).resolve().parents[1] / "patches.txt"
    text = patches_txt.read_text(encoding="utf-8")
    assert "[pre_model_sync]" in text and "[post_model_sync]" in text
    post = text.split("[post_model_sync]", 1)[1]
    for name in ("add_verify_token_fields", "repoint_verify_page_to_app_method"):
        path = f"sig_warehouse.sig_warehouse.patches.v1_0.{name}"
        assert path in post
        assert importlib.util.find_spec(path) is not None
