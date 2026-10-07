"""Pure logic for the HR email request (no Frappe import, unit-tested in tests/test_hr_email_request_logic.py).

Owner decision 2026-10-07: ``@sigtele.local`` logins are a dead end. Employees whose login is ``.local`` (or missing)
and who have no official ``@sigtele.com`` email on file are asked over WhatsApp to reply with their official email;
replies are collected from the WhatsApp Inbox sheet and proposed to HR - nothing is applied automatically.
"""
import json
import re

OFFICIAL_DOMAIN = "@sigtele.com"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")

REQUEST_TEXT = (
    "SIG HR: please reply to this message with your official company email (name@sigtele.com) "
    "so we can set up your ERP account. If you have no company email, reply with the email you use. "
    "Reply with the email only.\n\n"
    "الموارد البشرية - SIG: يرجى الرد على هذه الرسالة ببريدك الإلكتروني الرسمي للشركة لإعداد حسابك في النظام. "
    "إن لم يكن لديك بريد للشركة فأرسل بريدك المعتاد. أرسل البريد فقط."
)


def phone_key(value):
    """Last 9 digits - the matching rule already used for WhatsApp attendance (Employee.cell_number)."""
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return digits[-9:] if len(digits) >= 9 else ""


def is_local_login(user_id):
    return not user_id or str(user_id).strip().lower().endswith(".local")


def needs_email_request(row):
    """row: dict with employee_name, user_id, company_email, personal_email, cell_number."""
    name = str(row.get("employee_name") or "")
    if name.startswith("WhatsApp Sender"):
        return False  # unidentified placeholder numbers - separate owner decision
    if not is_local_login(row.get("user_id")):
        return False
    on_file = str(row.get("company_email") or row.get("personal_email") or "").strip().lower()
    if on_file.endswith(OFFICIAL_DOMAIN):
        return False  # official email already known: switch the login, no message needed
    return bool(phone_key(row.get("cell_number")))


def extract_email(text):
    """First plausible email in a reply; prefers an official @sigtele.com address when several are given."""
    found = [m.group(0).strip(".,;:") for m in EMAIL_RE.finditer(str(text or ""))]
    if not found:
        return ""
    for email in found:
        if email.lower().endswith(OFFICIAL_DOMAIN):
            return email.lower()
    return found[0].lower()


def parse_inbox_row(received_at, payload, conversation):
    """WhatsApp Inbox row -> (received_at, phone_key, text) for an incoming 1:1 text, else None."""
    if not str(conversation or "").endswith("@c.us"):
        return None
    try:
        data = json.loads(payload or "{}")
    except (TypeError, ValueError):
        return None
    message = data.get("message") or {}
    if message.get("fromMe"):
        return None
    if message.get("type") != "text":
        return None
    key = phone_key(str(conversation).split("@", 1)[0])
    if not key:
        return None
    return str(received_at or ""), key, str(message.get("text") or "")


def match_replies(requests, inbox_rows):
    """requests: {phone_key: sent_at 'YYYY-MM-DD HH:MM:SS'}; inbox_rows: iterable of parse_inbox_row results.
    Returns {phone_key: (received_at, email)} using the first reply carrying an email after the request."""
    out = {}
    for row in sorted((r for r in inbox_rows if r), key=lambda r: r[0]):
        received_at, key, text = row
        sent_at = requests.get(key)
        if not sent_at or key in out or received_at < sent_at:
            continue
        email = extract_email(text)
        if email:
            out[key] = (received_at, email)
    return out
