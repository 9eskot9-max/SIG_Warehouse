"""SNB statement adapter: one statement line in, routing signals out. No Frappe calls.

Narratives differ by transfer format, so the format decides which identifiers exist. The SAR 20,000 amount
never decides a format. Another bank gets its own adapter that returns the same shape.
"""
import re

from ..sadad_billers import biller_name
from ..text import DEFAULT_COMPANY_SCOPES, hint_key, is_company_number, normalize_text

FEE_FAMILIES = ("BANK_FEE", "FEE_VAT")
TAWAL_PATTERN = re.compile(r"\bTAWAL\b|TELECOMMUNICATIONS?\s+TOWERS", re.I)
# Texts that are bank adjustments, not counterparties.
ADJUSTMENT_PATTERN = re.compile(r"FEES?\s+REVERSAL|VAT\s+REBATE|LG\s*-\s*OUTWARD", re.I)
MIN_LENGTH = {"NAME": 4, "ACCOUNT": 8, "IBAN": 20, "BEN_ID": 3, "DEP_ID": 5}
NOT_BANK_CODES = {"SAUDIA", "SAUDIS"}


def narrative(source):
    parts = ("transaction_description", "detail_description", "extra_description", "remarks")
    return " ".join(str(source.get(key) or "") for key in parts)


def detail_text(source):
    return " ".join(str(source.get(key) or "") for key in ("detail_description", "extra_description", "remarks"))


def statement_format(source):
    """INTERNAL_SNB, IPS_LOCAL, LARGE_LOCAL, or '' when the line is none of the three transfer formats."""
    parser = str(source.get("parser_family") or "").upper()
    description = str(source.get("transaction_description") or "").upper()
    detail = detail_text(source).upper()
    if re.search(r"\b(?:INCOMING\s+)?(?:INTERNAL|SNB|WITHIN\s+BANK)\s+TRANSFER\b", description + " " + detail):
        return "INTERNAL_SNB"
    if parser == "IPS_LOCAL" or "SAUDI ARABIA" in detail:
        return "IPS_LOCAL"
    if parser == "INTERNAL_BEN_ID" or "BEN ID:" in detail:
        return "INTERNAL_SNB"
    if parser in ("LOCAL_OTBANK", "INCOMING_LOCAL") or "INCOMING LOCAL" in description:
        return "LARGE_LOCAL"
    return ""


def clean_ips_name(text):
    """The payer or payee name after 'SAUDI ARABIA': drop a leading bank code and stop at the first long number."""
    text = str(text or "").strip()
    match = re.match(r"^(SA[A-Z]{4})\s+(?=\S)", text)
    if match and match.group(1) not in NOT_BANK_CODES:
        text = text[match.end():]
    digits = re.search(r"\d{8,}", text)
    if digits:
        text = text[:digits.start()]
    return text.strip()


def parse(source, scopes=DEFAULT_COMPANY_SCOPES):
    """Signals for one SNB statement line.

    Returns format, identifiers [(kind, value)], display_name, own_account, tawal, adjustment, reference.
    `own_account` means the other side of the line is one of our accounts: no payer or payee to remember.
    """
    fmt = statement_format(source)
    text = narrative(source)
    detail = detail_text(source)
    out = {"format": fmt, "identifiers": [], "display_name": "", "own_account": False,
           "tawal": bool(TAWAL_PATTERN.search(text)), "adjustment": bool(ADJUSTMENT_PATTERN.search(text)),
           "reference": str(source.get("reference") or "").strip()}
    if str(source.get("parser_family") or "").upper() == "SADAD":
        # Real statement text: "SADAD Payment 165-2001003327019603 <our account> <reference>": the number before the dash
        # is the biller and the rest is the bill account. The older "BILLER 123" wording is still accepted.
        biller = re.search(r"\b(?:BILLER(?:\s*(?:ID|CODE))?)\s*[:#-]?\s*(\d{2,8})\b", text, re.I)
        bill = re.search(r"(?<!\d)(\d{2,4})-(\d{6,20})(?!\d)", detail) or re.search(r"(?<!\d)(\d{2,4})-(\d{6,20})(?!\d)", text)
        if bill:
            out["biller_code"], out["bill_account"] = bill.group(1), bill.group(2)
            out["biller_name"] = biller_name(bill.group(1))
            # A bill (for example one worker's iqama renewal) repeats: it is remembered once Finance has routed it.
            out["identifiers"].append(("SADAD_CODE", f"{bill.group(1)}-{bill.group(2)}"))
        elif biller:
            out["biller_code"] = biller.group(1)
            out["biller_name"] = biller_name(biller.group(1))
    if not fmt:
        return out
    party_id = re.search(r"(?P<label>BEN|DEP)\s*ID\s*:\s*(?P<value>\d+)", detail, re.I)
    account = re.search(r"(\d{10,24})\s+(?:BEN|DEP)\s*ID\s*:", detail, re.I)
    otbank = re.search(r"OTBANK\s*:\s*[A-Z]{4}(.+)$", detail, re.I)
    ips = re.search(r"SAUDI\s+ARABIA\s+(.+)$", detail, re.I)
    iban = re.search(r"(?<![A-Z0-9])(SA\d{22})(?!\d)", detail, re.I)
    found = []
    if fmt == "INTERNAL_SNB" and party_id:
        if account and is_company_number(account.group(1), scopes):
            out["own_account"] = True
            return out
        found.append(("BEN_ID" if party_id.group("label").upper() == "BEN" else "DEP_ID", party_id.group("value")))
        if account:
            found.append(("ACCOUNT", account.group(1)))
    elif fmt == "IPS_LOCAL" and ips:
        name = clean_ips_name(ips.group(1))
        if name:
            found.append(("NAME", name))
            out["display_name"] = name
    elif fmt == "LARGE_LOCAL":
        # Incoming local statements can carry an eight/eleven character BIC,
        # a truncated payer name, and an EXTN reference rather than OTBANK.
        incoming_name = re.search(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\s+(.+?)\s+EXTN[A-Z0-9]+\b", detail, re.I)
        if not otbank and incoming_name and str(source.get("direction") or "").upper() == "CREDIT":
            name = incoming_name.group(1).strip()
            found.append(("NAME", name))
            out["display_name"] = name
        if otbank:
            name = otbank.group(1).strip()
            found.append(("NAME", name))
            out["display_name"] = name
        if iban:
            if is_company_number(iban.group(1), scopes):
                out["own_account"] = True
                return out
            found.append(("IBAN", iban.group(1).upper()))
    out["identifiers"] = [(kind, value.strip()) for kind, value in found
                          if value and len(hint_key(kind, value)) >= MIN_LENGTH[kind]]
    return out


def has_text(source, fragment):
    """Exact normalised phrase test, used for a hand-chosen stable name hint."""
    return f" {normalize_text(fragment)} " in f" {normalize_text(narrative(source))} "
