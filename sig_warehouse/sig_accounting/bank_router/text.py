"""Text and number normalisation shared by every routing stage. No Frappe calls."""
import hashlib
import re
import unicodedata

# SHA-256 of each of our own bank accounts, zero-padded to 14 digits. Never the account number itself.
# Settings supplies the live set; this default mirrors the two SNB accounts the importer already maps.
DEFAULT_COMPANY_SCOPES = frozenset({
    "f98451763299c21a58d649ad9118abe9fca723cfd0a2ca00fe65238d98bbe3fb",  # GL 13121
    "370b2d40789076a4688a328253800d1574bcb2ebbab14add0c1acb0d7dfe1b9e",  # GL 13123
    "d05ef5eb6ab4b65a664cc9393796f78593acaa14d4de72f75a41faeddaf0275b",  # third own account the resolver already knows
})


def normalize_text(value):
    """Case, diacritic and Arabic-letter normalisation: the same text always compares equal."""
    value = unicodedata.normalize("NFKD", str(value or "")).strip().casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.replace("ـ", "")
    value = re.sub(r"[أإآ]", "ا", value)
    value = value.replace("ة", "ه").replace("ى", "ي")
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def hint_key(kind, value):
    """Comparison form of an identifier. Digit-only values ignore leading zeros (Sheets drops them)."""
    text = normalize_text(value)
    if kind == "NAME" or str(kind).startswith("NAME_"):
        return text
    compact = text.replace(" ", "")
    return compact.lstrip("0") if compact.isdigit() else compact


def account_scope(number):
    """Fingerprint of a bank account number as it appears on statements."""
    digits = re.sub(r"\D", "", str(number or ""))
    if not digits:
        return ""
    return hashlib.sha256(digits[-14:].zfill(14).encode("utf-8")).hexdigest()


def is_company_number(value, scopes=DEFAULT_COMPANY_SCOPES):
    """True when a long number (account or IBAN) is one of our own accounts."""
    digits = re.sub(r"\D", "", str(value or ""))
    return len(digits) >= 10 and account_scope(digits) in scopes
