"""Letter references: yymmdd + A, B, C ... per day (e.g. 261022A). Pure Python."""

import string

LETTERS = string.ascii_uppercase


def day_prefix(letter_date):
    """yymmdd for a date or ISO string (YYYY-MM-DD)."""
    if hasattr(letter_date, "strftime"):
        return letter_date.strftime("%y%m%d")
    y, m, d = str(letter_date)[:10].split("-")
    return f"{y[2:]}{m}{d}"


def suffix(index):
    """0 -> A ... 25 -> Z, 26 -> AA, 27 -> AB ..."""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = LETTERS[rem] + out
    return out


def next_reference(prefix, existing_names):
    """First unused reference for ``prefix`` given the names already taken."""
    taken = set(existing_names)
    i = 0
    while f"{prefix}{suffix(i)}" in taken:
        i += 1
    return f"{prefix}{suffix(i)}"
