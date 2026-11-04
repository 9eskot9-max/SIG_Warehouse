"""Deterministic WhatsApp intake message parsing for SIG Candidate Intake.

No Frappe or network dependency: sheet rows are treated as untrusted input and
only allowlisted, non-sensitive values are returned for HR review.
"""
import json
import re
import unicodedata


FIELDS = (
    ("Case ID", "case_id", False),
    ("Full Legal Name (as on ID)", "legal_name", False),
    ("Preferred Name", "preferred_name", False),
    ("Official Mobile Number", "official_mobile", False),
    ("Email for ERP Contact/Login", "email", False),
    ("Date of Birth", "date_of_birth", True),
    ("Nationality", "nationality", True),
    ("National ID / Iqama Number", "identity_number", True),
    ("ID Expiry Date", "identity_expiry", True),
    ("Saudi IBAN (for payroll, if applicable)", "iban", True),
    ("Bank Account Holder Name", "bank_account_holder", True),
    ("Current Address (if required by HR)", "address", True),
    ("Emergency Contact Name / Phone / Relationship (if required by HR)", "emergency_contact", True),
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

    The payload must start with EMP-DATA and then contain label/value row pairs.
    Sensitive values are never returned; only USE_SECURE_FORM is accepted for
    fields marked sensitive in the template.
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
            if not sensitive:
                return {"ok": False, "error": "UNEXPECTED_SECURE_HANDOFF"}
            handoffs.append(key)
            continue
        if sensitive:
            return {"ok": False, "error": "SENSITIVE_VALUE_IN_CHAT"}
        if "\n" in value:
            return {"ok": False, "error": "MULTILINE_VALUE"}
        values[key] = value
    if not values.get("case_id"):
        return {"ok": False, "error": "MISSING_CASE_ID"}
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
    instructions = (
        "Please fill in the next message. Copy it, keep EMP-DATA and each field label on its own line, "
        "and put your answer on the line directly below that label. Use NOT_PROVIDED when a field does "
        "not apply or you do not know it. Keep USE_SECURE_FORM for secure fields; HR will send the separate "
        "secure form if those details are required. Do not send ID or bank details or document photos in "
        "WhatsApp. Reply STOP to end messages."
    )
    fields = [
        ("Case ID", case_id, False),
        ("Full Legal Name (as on ID)", "NOT_PROVIDED", False),
        ("Preferred Name", "NOT_PROVIDED", False),
        ("Official Mobile Number", "NOT_PROVIDED", False),
        ("Email for ERP Contact/Login", "NOT_PROVIDED", False),
        ("Date of Birth", "USE_SECURE_FORM", True),
        ("Nationality", "USE_SECURE_FORM", True),
        ("National ID / Iqama Number", "USE_SECURE_FORM", True),
        ("ID Expiry Date", "USE_SECURE_FORM", True),
        ("Saudi IBAN (for payroll, if applicable)", "USE_SECURE_FORM", True),
        ("Bank Account Holder Name", "USE_SECURE_FORM", True),
        ("Current Address (if required by HR)", "USE_SECURE_FORM", True),
        ("Emergency Contact Name / Phone / Relationship (if required by HR)", "USE_SECURE_FORM", True),
    ]
    template = ["EMP-DATA"]
    for label, value, _sensitive in fields:
        template.extend((label, value))
    explainer = (
        "Hello. SIG HR is starting your onboarding. If this is your number and you agree to continue here, reply YES. "
        "Reply STOP if this is the wrong number or you do not want messages. Do not send identity or bank details here.\n\n"
        "مرحباً، تبدأ الموارد البشرية في SIG إجراءات انضمامك. إذا كان هذا رقمك وتوافق على التواصل هنا، يرجى الرد YES. "
        "إذا كان الرقم غير صحيح أو لا ترغب بالرسائل، أرسل STOP. لا ترسل بيانات الهوية أو البنك هنا.\n\n"
        "سلام، SIG کی HR آپ کی آن بورڈنگ شروع کر رہی ہے۔ اگر یہ آپ کا نمبر ہے اور آپ یہاں رابطے سے اتفاق کرتے ہیں تو YES لکھیں۔ "
        "اگر نمبر غلط ہے یا آپ پیغامات نہیں چاہتے تو STOP لکھیں۔ شناختی یا بینک کی تفصیلات یہاں نہ بھیجیں۔"
    )
    return [explainer, instructions, "\n".join(template)]
