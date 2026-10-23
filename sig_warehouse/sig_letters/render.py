"""Helpers the SIG Letter print format calls (registered as jinja methods). Pure Python."""

import json

from .blocks import split_heading


def table_data(table_json):
    """Parse a Table block's JSON into {'head': [...], 'rows': [[...]]} (empty on bad input)."""
    try:
        data = json.loads(table_json or "{}")
    except ValueError:
        return {"head": [], "rows": []}
    return {"head": data.get("head", []), "rows": data.get("rows", [])}


def items_list(items):
    """A Bullets block's text -> list of non-empty lines."""
    return [line.strip() for line in (items or "").split("\n") if line.strip()]


def heading_parts(text):
    """('3', 'Cables and routes') for '3. Cables and routes'; (None, text) otherwise."""
    return split_heading(text)


ALLOWED = ("b", "i", "u", "br")


def inline_html(text):
    """Escape everything, then restore only <b> <i> <u> <br> (and their closers). Safe for print output."""
    import html
    import re

    out = html.escape(text or "", quote=False)
    for tag in ALLOWED:
        out = re.sub(rf"&lt;(/?){tag}\s*/?&gt;", lambda m, t=tag: f"<{m.group(1)}{t}>" if t != "br" else "<br>", out, flags=re.I)
    return out
