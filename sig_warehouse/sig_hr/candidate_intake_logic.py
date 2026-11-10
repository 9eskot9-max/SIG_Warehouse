"""Deterministic WhatsApp intake parsing for HR review."""
import json
import re
import unicodedata


FIELDS = (
    ("Case ID", "case_id", False),
    ("Full Legal Name (as on ID)", "legal_name", False),
    ("Email for ERP account", "email", False),
    ("Saudi ID / Iqama Number", "identity_number", True),
    ("Saudi IBAN", "iban", True),
)
FIELD_BY_LABEL = {label.casefold(): (key, sensitive) for label, key, sensitive in FIELDS}
SENSITIVE_PATTERNS = (
    re.compile(r"\bSA[\s-]*\d(?:[\s-]*\d){21}\b", re.I),
    re.compile(r"\b(?:national id|iqama|passport)\b[^\n\r]{0,24}\d{10}\b", re.I),
    re.compile(r"\b(?:iban|bank account)\b\s*[:=]\s*[A-Z0-9\s-]{10,}", re.I),
)


def normalize_phone(value):
    value = "".join(str(unicodedata.digit(ch)) if ch.isdecimal() else ch for ch in str(value or ""))
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("966"):
        local = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        local = digits[1:]
    else:
        local = digits
    if len(local) == 9 and local.startswith("5"):
        return "966" + local
    if len(digits) >= 10:
        return digits
    return ""


def parse_emp_data(text):
    """Return safe allowlisted values and handoffs, or a stable parse error.

    The reply is parsed from the Maytapi Inbox and staged for HR review. Raw
    message bodies are never copied into ERP logs or intake audit rows.
    """
    lines = [line.strip() for line in str(text or "").replace("\r", "").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    if not lines or lines[0] != "EMP-DATA":
        return {"ok": False, "error": "NOT_EMP_DATA"}
    expected = [label for label, _key, _sensitive in FIELDS]
    supplied = lines[1::2]
    if supplied != expected:
        return {"ok": False, "error": "LABELS_MISSING_OR_OUT_OF_ORDER"}
    if (len(lines) - 1) % 2:
        return {"ok": False, "error": "ODD_LABEL_VALUE_ROWS"}
    values, handoffs, seen = {}, [], set()
    for i in range(1, len(lines), 2):
        label, value = lines[i], lines[i + 1]
        field = FIELD_BY_LABEL.get(label.casefold())
        if not field:
            return {"ok": False, "error": "UNKNOWN_LABEL"}
        key, sensitive = field
        if key in seen:
            return {"ok": False, "error": "DUPLICATE_LABEL"}
        seen.add(key)
        value = value.strip()
        if value.upper() == "NOT_PROVIDED":
            continue
        if value.upper() == "USE_SECURE_FORM":
            return {"ok": False, "error": "MISSING_REQUIRED_VALUE"}
        if "\n" in value:
            return {"ok": False, "error": "MULTILINE_VALUE"}
        values[key] = value
    if not values.get("case_id") or not values.get("legal_name") or not values.get("identity_number") or not values.get("email") or not values.get("iban"):
        return {"ok": False, "error": "MISSING_REQUIRED_VALUE"}
    identity = values["identity_number"].strip()
    if len(identity) != 10 or identity[0] not in "12":
        return {"ok": False, "error": "INVALID_ID_FORMAT"}
    if not re.fullmatch(r"[0-9]{10}", identity):
        return {"ok": False, "error": "INVALID_ID_FORMAT"}
    values["identity_number"] = identity
    iban = re.sub(r"\s+", "", values["iban"]).upper()
    if not re.fullmatch(r"SA\d{22}", iban):
        return {"ok": False, "error": "INVALID_IBAN_FORMAT"}
    check = "".join(str(ord(c) - 55) if c.isalpha() else c for c in iban[4:] + iban[:4])
    if int(check) % 97 != 1:
        return {"ok": False, "error": "INVALID_IBAN_CHECKSUM"}
    values["iban"] = iban
    return {"ok": True, "values": values, "secure_handoffs": handoffs}


def parse_inbox_payload(received_at, payload, message_id, conversation, message_type):
    """Decode one row from the Maytapi Inbox sheet; return only 1:1 inbound text."""
    if message_type != "text" or not str(conversation or "").endswith("@c.us"):
        return None
    try:
        data = json.loads(payload or "{}")
    except (TypeError, ValueError):
        return None
    message = data.get("message") or {}
    if message.get("fromMe") or message.get("type") != "text":
        return None
    user = data.get("user") or {}
    sender = user.get("phone") or user.get("id") or str(conversation).split("@", 1)[0]
    return {
        "received_at": str(received_at or ""),
        "message_id": str(message_id or ""),
        "phone": normalize_phone(sender),
        "text": str(message.get("text") or ""),
    }


def contains_sensitive_chat_data(text):
    """Conservative detector used to quarantine accidental ID/IBAN disclosure."""
    candidate = "".join(str(unicodedata.digit(ch)) if ch.isdecimal() else ch for ch in str(text or ""))
    compact = re.sub(r"[\s-]", "", candidate)
    digits = re.sub(r"\D", "", candidate)
    if len(digits) == 10 and len(compact) <= 14:
        return True  # an unstructured ten-digit value may be a national ID
    return any(pattern.search(candidate) for pattern in SENSITIVE_PATTERNS)


def onboarding_messages(case_id, legal_name=""):
    """Return the three outbound messages in the required send order."""
    instructions = "Please copy the next message and enter each answer on the separate line below its heading. HR will review your details. Reply STOP if you do not want to continue."
    fields = [
        ("Case ID", case_id, False),
        ("Full Legal Name (as on ID)", "NOT_PROVIDED", False),
        ("Email for ERP account", "NOT_PROVIDED", False),
        ("Saudi ID / Iqama Number", "NOT_PROVIDED", True),
        ("Saudi IBAN", "NOT_PROVIDED", True),
    ]
    template = ["EMP-DATA"]
    for label, value, _sensitive in fields:
        template.extend((label, value))
    explainer = (
        "Hello. SIG HR is starting your onboarding. Please complete the short information message we will send next. Reply STOP if you do not want to continue.\n\n"
        "مرحباً، تبدأ الموارد البشرية في SIG إجراءات انضمامك. يرجى تعبئة الرسالة التالية. لإيقاف الرسائل أرسل STOP.\n\n"
        "سلام، SIG کی HR آپ کی آن بورڈنگ شروع کر رہی ہے۔ براہ کرم اگلا پیغام پُر کریں۔ بند کرنے کے لیے STOP لکھیں۔"
    )
    return [explainer, instructions, "\n".join(template)]
