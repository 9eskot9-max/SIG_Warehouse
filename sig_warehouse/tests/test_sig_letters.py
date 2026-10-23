import importlib.util
import json
import re
from pathlib import Path

import pytest

from sig_warehouse.sig_letters import blocks as B
from sig_warehouse.sig_letters import reference as R
from sig_warehouse.sig_letters import render as T

APP = Path(__file__).resolve().parents[1]
LETTERS = APP / "sig_letters"
ENOVA = APP.parents[1] / "outputs" / "letters" / "enova_technical_proposal_261021A.json"


# ---- reference (yymmddA) --------------------------------------------------------------------

def test_day_prefix_and_suffix_sequence():
    assert R.day_prefix("2026-10-22") == "261022"
    assert [R.suffix(i) for i in (0, 1, 25, 26, 27, 51, 52)] == ["A", "B", "Z", "AA", "AB", "AZ", "BA"]


def test_next_reference_takes_first_free_letter():
    assert R.next_reference("261022", []) == "261022A"
    assert R.next_reference("261022", ["261022A", "261022B"]) == "261022C"
    assert R.next_reference("261022", ["261022B"]) == "261022A"          # a deleted draft frees its letter
    assert R.next_reference("261023", ["261022A"]) == "261023A"          # a new day starts again at A


# ---- blocks ---------------------------------------------------------------------------------

SAMPLE = [
    {"type": "note", "text": "<b>Subject to survey.</b>"},
    {"type": "h", "text": "1. Design basis"},
    {"type": "p", "text": "A paragraph with <i>inline</i> tags."},
    {"type": "ul", "items": ["one", "two <b>bold</b>"]},
    {"type": "table", "head": ["Screen", "Route"], "rows": [["Screen-1", "~350 m"], ["Screen-2", "~100 m"]]},
]


def test_every_block_type_round_trips():
    for block in SAMPLE:
        assert B.row_to_block(B.block_to_row(block)) == block


def test_blocks_are_validated():
    bad = [
        {"type": "video", "text": "x"},
        {"type": "p", "text": "  "},
        {"type": "ul", "items": []},
        {"type": "ul", "items": ["ok", ""]},
        {"type": "table", "head": ["A", "B"], "rows": [["only one"]]},
        {"type": "p", "text": "<script>alert(1)</script>"},
        {"type": "p", "text": "<img src=x onerror=1>"},
    ]
    for block in bad:
        with pytest.raises(B.BlockError):
            B.block_to_row(block)


def test_heading_number_split():
    assert B.split_heading("3. Cables and routes") == ("3", "Cables and routes")
    assert B.split_heading("Limited Warranty conditions:") == (None, "Limited Warranty conditions:")


def test_payload_to_doc_minimal_and_errors():
    doc = B.payload_to_doc({"addressee": "Enova", "subject": "S", "blocks": [{"type": "p", "text": "Hi"}],
                            "letter_date": "2026-10-22", "related_doctype": "Quotation", "related_document": "QTN-26-061"})
    assert doc["doctype"] == "SIG Letter" and doc["language"] == "English"
    assert doc["blocks"] == [{"block_type": "Paragraph", "content": "Hi"}]
    assert doc["related_document"] == "QTN-26-061"
    for payload in ({}, {"addressee": "x", "subject": "y"}, {"addressee": "x", "subject": "y", "blocks": [{"type": "p", "text": "z"}], "language": "French"}):
        with pytest.raises(B.BlockError):
            B.payload_to_doc(payload)


def test_legacy_dates():
    assert B.legacy_date("22 / 10 / 2026") == "2026-10-22"
    assert B.legacy_date("2026-10-22") == "2026-10-22"
    with pytest.raises(B.BlockError):
        B.legacy_date("yesterday")


@pytest.mark.skipif(not ENOVA.exists(), reason="Enova letter JSON not present")
def test_existing_enova_letter_converts_unchanged_in_content():
    legacy = json.loads(ENOVA.read_text(encoding="utf-8-sig"))
    doc = B.legacy_payload_to_doc(legacy)
    assert doc["addressee"] == legacy["to"] and doc["letter_date"] == "2026-10-22"
    assert len(doc["blocks"]) == len(legacy["blocks"])
    assert [B.row_to_block(r) for r in doc["blocks"]] == legacy["blocks"]


# ---- render helpers -------------------------------------------------------------------------

def test_render_helpers():
    assert T.table_data('{"head": ["A"], "rows": [["1"]]}') == {"head": ["A"], "rows": [["1"]]}
    assert T.table_data("not json") == {"head": [], "rows": []} and T.table_data(None) == {"head": [], "rows": []}
    assert T.items_list("a\n\n b \n") == ["a", "b"]
    assert T.heading_parts("2. Source end") == ("2", "Source end")
    assert T.inline_html("<b>ok</b> <script>x</script> & <br>") == "<b>ok</b> &lt;script&gt;x&lt;/script&gt; &amp; <br>"


# ---- DocType definitions --------------------------------------------------------------------

KNOWN_FIELDTYPES = {"Data", "Select", "Link", "Dynamic Link", "Date", "Check", "Table", "Small Text", "Code",
                    "Section Break", "Column Break", "Text Editor"}
KNOWN_DOCTYPES = {"SIG Letter", "SIG Letter Block", "SIG Letter Template", "Company", "Project", "DocType", "User", "Print Format"}


def load_doctype(folder):
    return json.loads((LETTERS / "doctype" / folder / f"{folder}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("folder", ["sig_letter", "sig_letter_block", "sig_letter_template"])
def test_doctype_json_is_consistent(folder):
    dt = load_doctype(folder)
    names = [f["fieldname"] for f in dt["fields"]]
    assert len(names) == len(set(names)), "duplicate fieldname"
    assert dt["field_order"] == names
    assert dt["module"] == "SIG Letters"
    for f in dt["fields"]:
        assert f["fieldtype"] in KNOWN_FIELDTYPES, f
        if f["fieldtype"] in ("Link", "Table"):
            assert f["options"] in KNOWN_DOCTYPES, f
        if f["fieldtype"] == "Dynamic Link":
            assert f["options"] in names, f
    assert (folder == "sig_letter_block") == bool(dt.get("istable"))
    if folder != "sig_letter_block":
        assert any(p["role"] == "System Manager" for p in dt["permissions"])
    # python controller exists next to the json
    assert (LETTERS / "doctype" / folder / f"{folder}.py").exists()


def test_sig_letter_is_submittable_named_by_controller_and_carries_the_verify_token():
    dt = load_doctype("sig_letter")
    assert dt["is_submittable"] == 1 and dt["track_changes"] == 1
    assert dt["autoname"] == "" and "naming_rule" not in dt           # name comes from SIGLetter.autoname (yymmddA)
    token = next(f for f in dt["fields"] if f["fieldname"] == "custom_verify_token")
    assert token["hidden"] == token["read_only"] == token["no_copy"] == token["allow_on_submit"] == token["print_hide"] == 1
    reg = __import__("sig_warehouse.sig_verify.registry", fromlist=["x"])
    assert "SIG Letter" in reg.VERIFIABLE and reg.TOKEN_FIELD == "custom_verify_token"
    assert reg.VERIFIABLE["SIG Letter"]["date_field"] in names_of(dt)


def names_of(dt):
    return {f["fieldname"] for f in dt["fields"]}


def test_template_and_letter_share_the_block_child_table():
    for folder in ("sig_letter", "sig_letter_template"):
        blocks_field = next(f for f in load_doctype(folder)["fields"] if f["fieldname"] == "blocks")
        assert blocks_field["options"] == "SIG Letter Block"
    block = load_doctype("sig_letter_block")
    kinds = next(f for f in block["fields"] if f["fieldname"] == "block_type")["options"].split("\n")
    assert kinds == [B.TYPE_TO_LABEL[k] for k in ("p", "h", "ul", "table", "note")]


# ---- print format ---------------------------------------------------------------------------

PF = (LETTERS / "print_format" / "sig_letter.html").read_text(encoding="utf-8")


def test_print_format_parses_and_uses_only_registered_jinja_methods():
    jinja2 = pytest.importorskip("jinja2")
    jinja2.Environment().parse(PF)
    from sig_warehouse import hooks

    registered = {m.rsplit(".", 1)[1] for m in hooks.jinja["methods"]}
    called = set(re.findall(r"\b(table_data|items_list|heading_parts|inline_html)\(", PF))
    assert called and called <= registered


def test_print_format_is_wkhtmltopdf_safe():
    css = PF.split("<style>", 1)[1].split("</style>", 1)[0]
    for banned in ("display:flex", "display: flex", "display:grid", "display: grid", "var(--", "calc(", "gap:"):
        assert banned not in css, banned
    assert 'id="footer-html"' in PF and 'class="page"' in PF and 'class="topage"' in PF
    assert "{{ frappe.utils.get_url() }}/files/BoutrosMBCDinkum-Medium.ttf" in PF      # absolute font URL (not /files/..)
    assert "verify_qr_%" in PF                                                         # matches sig_verify.registry.QR_FILE_PREFIX


def test_print_format_palette_matches_the_design_tokens():
    tokens = json.loads((LETTERS / "design" / "tokens.json").read_text(encoding="utf-8"))["colors"]
    m = re.search(r'set _c = \{(.*?)\}', PF, re.S).group(1)
    palette = dict(re.findall(r'"(\w+)":\s*"(#[0-9A-Fa-f]{6})"', m))
    for key, token in (("navy", "navy"), ("blue", "blue"), ("cyan", "cyan"), ("slate", "slate"), ("pale", "pale_blue"),
                       ("border", "border"), ("muted", "text_muted")):
        assert palette[key].lower() == tokens[token].lower(), key


# ---- seeds ----------------------------------------------------------------------------------

SEEDS = sorted((LETTERS / "templates").glob("*.json"))


def test_seed_library_exists():
    assert {p.stem for p in SEEDS} >= {"warranty_limited_tawal", "technical_proposal_power_supply", "authorization_delegate_ar"}


@pytest.mark.parametrize("path", SEEDS, ids=lambda p: p.stem)
def test_seed_templates_are_valid_and_their_variables_are_declared(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["language"] in B.LANGUAGES and data["template_name"]
    rows = [B.block_to_row(b) for b in data["blocks"]]                 # raises on any invalid block
    declared = {v["key"] for v in data.get("variables", [])}
    text = json.dumps([data.get("subject"), data.get("greeting"), data.get("closing"), rows], ensure_ascii=False)
    used = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", text))
    assert used <= declared, f"undeclared variables: {used - declared}"
    assert declared <= used or not declared, f"declared but unused: {declared - used}"


def test_warranty_seed_keeps_the_word_template_wording_and_tokens():
    data = json.loads((LETTERS / "templates" / "warranty_limited_tawal.json").read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False)
    for phrase in ("Limited Warranty conditions:", "The Warranty does not cover:", "Warranty Replacements",
                   "This warranty only effective with respect to finalized agreement or PO for same subject project"):
        assert phrase in text
    # the old Word tokens now map to variables: xxxx prgg pddsc pddnm prrd mndt xxsn
    assert {v["key"] for v in data["variables"]} == {"site_id", "project", "product", "product_description",
                                                      "warranty_years", "manufacturing_date", "serial_number"}


# ---- wiring ---------------------------------------------------------------------------------

def test_module_patches_and_hooks_are_wired():
    assert "SIG Letters" in (APP / "modules.txt").read_text(encoding="utf-8").splitlines()
    text = (APP / "patches.txt").read_text(encoding="utf-8")
    pre, post = text.split("[post_model_sync]")
    assert "add_sig_letters_module" in pre.split("[pre_model_sync]")[1]       # Module Def must exist before the model sync
    assert "install_sig_letters" in post
    for name in ("add_sig_letters_module", "install_sig_letters"):
        assert importlib.util.find_spec(f"sig_warehouse.sig_warehouse.patches.v1_0.{name}") is not None
    from sig_warehouse import hooks

    for dotted in hooks.jinja["methods"]:
        assert importlib.util.find_spec(dotted.rsplit(".", 1)[0]) is not None
    assert "sig_warehouse.sig_verify.events.on_submit" in hooks.doc_events["SIG Letter"]["on_submit"]
