"""Pure-logic tests for sig_hr.email_request_logic (no Frappe needed): run with
    python -m unittest sig_warehouse.tests.test_hr_email_request_logic
from the SIG_Warehouse repo root."""
import json
import unittest

from sig_warehouse.sig_hr.email_request_logic import (
    extract_email, match_replies, needs_email_request, parse_inbox_row, phone_key,
)


def row(**kw):
    base = {"employee_name": "Ali Test", "user_id": "ali.test@sigtele.local", "company_email": "", "personal_email": "", "cell_number": "+966550946813"}
    base.update(kw)
    return base


class Recipients(unittest.TestCase):
    def test_local_login_without_email_is_asked(self):
        self.assertTrue(needs_email_request(row()))

    def test_personal_email_on_file_is_still_asked_for_official(self):
        self.assertTrue(needs_email_request(row(company_email="ali@gmail.com")))

    def test_official_email_on_file_is_not_asked(self):
        self.assertFalse(needs_email_request(row(company_email="Ali@SIGtele.com")))

    def test_real_login_is_not_asked(self):
        self.assertFalse(needs_email_request(row(user_id="ali@sigtele.com")))

    def test_missing_user_is_asked(self):
        self.assertTrue(needs_email_request(row(user_id="")))

    def test_no_phone_cannot_be_asked(self):
        self.assertFalse(needs_email_request(row(cell_number="")))

    def test_whatsapp_sender_placeholder_is_excluded(self):
        self.assertFalse(needs_email_request(row(employee_name="WhatsApp Sender 966536139137", user_id="")))


class Extraction(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(extract_email("ali.test@gmail.com"), "ali.test@gmail.com")

    def test_in_sentence_with_trailing_dot(self):
        self.assertEqual(extract_email("my email is Ali.Test@SIGtele.com."), "ali.test@sigtele.com")

    def test_prefers_official(self):
        self.assertEqual(extract_email("a@gmail.com or b@sigtele.com"), "b@sigtele.com")

    def test_none(self):
        self.assertEqual(extract_email("ok thanks"), "")

    def test_arabic_text_around(self):
        self.assertEqual(extract_email("بريدي هو ali@hotmail.com شكرا"), "ali@hotmail.com")


class Inbox(unittest.TestCase):
    def payload(self, text, from_me=False, mtype="text"):
        return json.dumps({"message": {"type": mtype, "text": text, "fromMe": from_me}})

    def test_phone_key_last_nine(self):
        self.assertEqual(phone_key("+966 55 094 6813"), "550946813")
        self.assertEqual(phone_key("0550946813"), "550946813")

    def test_parse_incoming_text(self):
        r = parse_inbox_row("2026-10-08 09:00:00", self.payload("x@y.com"), "966550946813@c.us")
        self.assertEqual(r, ("2026-10-08 09:00:00", "550946813", "x@y.com"))

    def test_ignores_group_own_and_media(self):
        self.assertIsNone(parse_inbox_row("t", self.payload("x@y.com"), "1203@g.us"))
        self.assertIsNone(parse_inbox_row("t", self.payload("x@y.com", from_me=True), "966550946813@c.us"))
        self.assertIsNone(parse_inbox_row("t", self.payload("x@y.com", mtype="image"), "966550946813@c.us"))
        self.assertIsNone(parse_inbox_row("t", "not json", "966550946813@c.us"))

    def test_match_only_after_request_first_email_wins(self):
        rows = [
            ("2026-10-07 10:00:00", "550946813", "old@x.com"),      # before the request
            ("2026-10-08 09:00:00", "550946813", "hello"),          # no email
            ("2026-10-08 09:05:00", "550946813", "new@sigtele.com"),
            ("2026-10-08 09:10:00", "550946813", "later@x.com"),
            ("2026-10-08 09:00:00", "500000000", "stranger@x.com"),  # not asked
        ]
        got = match_replies({"550946813": "2026-10-07 16:00:00"}, rows)
        self.assertEqual(got, {"550946813": ("2026-10-08 09:05:00", "new@sigtele.com")})


if __name__ == "__main__":
    unittest.main()
