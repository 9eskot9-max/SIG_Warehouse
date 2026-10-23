"""Block model and API payload for SIG Letters. Pure Python (no frappe import).

A letter body is a list of typed blocks. The API / templates / local builder all speak this one shape:

    {"type": "p",     "text": "Plain paragraph. <b>Inline bold</b> allowed."}
    {"type": "h",     "text": "1. Design basis"}              # a leading "N. " becomes the numbered marker
    {"type": "ul",    "items": ["first", "second"]}
    {"type": "table", "head": ["Screen", "Route"], "rows": [["Screen-1", "~350 m"]]}
    {"type": "note",  "text": "Callout, e.g. Subject to site survey."}

``payload_to_doc`` builds the SIG Letter dict for ``POST /api/resource/SIG Letter``;
``legacy_payload_to_doc`` accepts the existing local-builder JSON (to / date "dd / mm / yyyy" / ref ...).
"""

import json
import re

TYPE_TO_LABEL = {"p": "Paragraph", "h": "Heading", "ul": "Bullets", "table": "Table", "note": "Note"}
LABEL_TO_TYPE = {v: k for k, v in TYPE_TO_LABEL.items()}
LANGUAGES = ("English", "Arabic", "Bilingual")
ALLOWED_INLINE_TAGS = ("b", "i", "u", "br")


class BlockError(ValueError):
    pass


def block_to_row(block):
    """Typed block -> SIG Letter Block child row."""
    kind = block.get("type")
    if kind not in TYPE_TO_LABEL:
        raise BlockError(f"unknown block type {kind!r}; use one of {sorted(TYPE_TO_LABEL)}")
    row = {"block_type": TYPE_TO_LABEL[kind]}
    if kind in ("p", "h", "note"):
        text = block.get("text")
        if not isinstance(text, str) or not text.strip():
            raise BlockError(f"{kind} block needs non-empty text")
        _check_inline(text)
        row["content"] = text
    elif kind == "ul":
        items = block.get("items")
        if not isinstance(items, list) or not items or not all(isinstance(i, str) and i.strip() for i in items):
            raise BlockError("ul block needs a non-empty list of strings")
        for item in items:
            _check_inline(item)
        if any("\n" in item for item in items):
            raise BlockError("a bullet cannot contain a line break")
        row["bullets"] = "\n".join(items)
    else:  # table
        head, rows = block.get("head"), block.get("rows")
        if not isinstance(head, list) or not head or not isinstance(rows, list):
            raise BlockError("table block needs head (list) and rows (list of lists)")
        if any(not isinstance(r, list) or len(r) != len(head) for r in rows):
            raise BlockError("every table row must have as many cells as the head")
        for cell in [*head, *[c for r in rows for c in r]]:
            _check_inline(str(cell))
        row["table_json"] = json.dumps({"head": head, "rows": rows}, ensure_ascii=False)
    return row


def row_to_block(row):
    """Child row -> typed block (inverse of block_to_row)."""
    kind = LABEL_TO_TYPE[row["block_type"]]
    if kind in ("p", "h", "note"):
        return {"type": kind, "text": row.get("content") or ""}
    if kind == "ul":
        return {"type": "ul", "items": [i for i in (row.get("bullets") or "").split("\n") if i.strip()]}
    data = json.loads(row.get("table_json") or "{}")
    return {"type": "table", "head": data.get("head", []), "rows": data.get("rows", [])}


def split_heading(text):
    """'3. Cables and routes' -> ('3', 'Cables and routes'); no number -> (None, text)."""
    m = re.match(r"^\s*(\d+)\.\s+(.*)$", text or "")
    return (m.group(1), m.group(2)) if m else (None, text)


def payload_to_doc(payload):
    """API payload -> SIG Letter document dict (for POST /api/resource/SIG Letter)."""
    missing = [k for k in ("addressee", "subject", "blocks") if not payload.get(k)]
    if missing:
        raise BlockError(f"payload is missing: {', '.join(missing)}")
    language = payload.get("language", "English")
    if language not in LANGUAGES:
        raise BlockError(f"language must be one of {LANGUAGES}")
    doc = {
        "doctype": "SIG Letter",
        "language": language,
        "addressee": payload["addressee"],
        "subject": payload["subject"],
        "blocks": [block_to_row(b) for b in payload["blocks"]],
    }
    for key in ("template", "letter_date", "company", "party_type", "party", "attn", "greeting", "closing",
                "project", "related_doctype", "related_document", "signer", "signer_title"):
        if payload.get(key):
            doc[key] = payload[key]
    return doc


def legacy_date(value):
    """'22 / 10 / 2026' -> '2026-10-22' (ISO strings pass through)."""
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})$", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    raise BlockError(f"unrecognised date {value!r}")


def legacy_payload_to_doc(legacy):
    """Existing local-builder JSON (to, attn, date, subject, greeting, blocks, closing) -> SIG Letter dict."""
    payload = {
        "addressee": legacy.get("to"),
        "attn": legacy.get("attn"),
        "subject": legacy.get("subject"),
        "greeting": legacy.get("greeting"),
        "blocks": legacy.get("blocks"),
        "closing": legacy.get("closing"),
    }
    if legacy.get("date"):
        payload["letter_date"] = legacy_date(legacy["date"])
    return payload_to_doc(payload)


def _check_inline(text):
    """Only plain text and a few inline tags: no scripts, no arbitrary HTML from an API payload."""
    for tag in re.findall(r"</?\s*([a-zA-Z0-9]+)", text):
        if tag.lower() not in ALLOWED_INLINE_TAGS:
            raise BlockError(f"tag <{tag}> is not allowed in letter text (allowed: {', '.join(ALLOWED_INLINE_TAGS)})")
