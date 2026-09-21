import importlib.util
import os
from datetime import datetime

_spec = importlib.util.spec_from_file_location(
    "field_sessions", os.path.join(os.path.dirname(__file__), "..", "sig_warehouse", "field_sessions.py"))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

G = "120363027593567578@g.us"   # Incident Recovery -> tiinc


def m(i, at, text, who="A", kind=None, site=None, group=G):
    k, s, ar, ac = fs.classify_text(text) if kind is None else (kind, site, None, None)
    return {"msg_key": "m%s" % i, "at": datetime.strptime(at, "%Y-%m-%d %H:%M"), "stream": fs.STREAM_BY_GROUP[group],
            "group": group, "reporter": who, "reporter_name": who, "kind": k, "site": s if kind is None else site,
            "activity_raw": ar, "activity_code": ac, "text": text}


NOW = datetime(2026, 9, 22, 12, 0)


def test_grammar_seen_live():
    assert fs.classify_text("ZDU004. Start")[:2] == ("START", "ZDU004")
    assert fs.classify_text("ZUZ964 start")[:2] == ("START", "ZUZ964")
    assert fs.classify_text("ZUZ964 End \U0001F446")[:2] == ("END", "ZUZ964")
    assert fs.classify_text("Start ZMK293")[:2] == ("START", "ZMK293")
    assert fs.classify_text("End")[:2] == ("END", None)
    assert fs.classify_text("@13305959706664 MDT Opened Please start the Activity")[0] == "OTHER"
    assert fs.classify_text("Please follow up with MSP for JV Tomorrow / ZBR085")[0] == "OTHER"
    assert fs.classify_text("Z95003 TMS SUBMITTED")[0] == "OTHER"
    assert fs.classify_text("Please close the ticket at the end of the week when you are back on site again ok")[0] == "OTHER"


def test_activity_optional_and_alias():
    assert fs.classify_text("ZAB123 Start ; HO")[3] == "HANDOVER"
    assert fs.classify_text("ZAB123 Start ; Survey")[3] == "SURVEY"
    assert fs.classify_text("ZAB123 Start ; foo")[3] == "UNRESOLVED"
    assert fs.classify_text("ZAB123 Start")[3] == "UNSPECIFIED"


def test_simple_completed_visit():
    s, e = fs.assemble([m(1, "2026-09-21 08:59", "ZDU004. Start"), m(2, "2026-09-21 12:55", "ZDU004. End")], NOW)
    assert len(s) == 1 and s[0]["status"] == "COMPLETED" and s[0]["hours"] == 3.93 and not e


def test_duplicate_start_and_duplicate_end_ignored():
    s, e = fs.assemble([m(1, "2026-09-21 15:39", "ZUZ964 start"), m(2, "2026-09-21 15:41", "ZUZ964 start"),
                        m(3, "2026-09-21 15:42", "ZUZ964 End"), m(4, "2026-09-21 15:43", "ZUZ964 End")], NOW)
    assert len(s) == 1 and s[0]["status"] == "COMPLETED" and not e


def test_missing_end_auto_closed_after_grace():
    s, e = fs.assemble([m(1, "2026-09-22 04:00", "ZDU004 Start")], NOW)
    assert s[0]["status"] == "AUTO_CLOSED" and "START_WITHOUT_END" in s[0]["diagnostics"]


def test_over_24h_silent_session_hits_cap():
    s, _ = fs.assemble([m(1, "2026-09-21 08:00", "ZDU004 Start")], NOW)
    assert s[0]["status"] == "AUTO_CLOSED" and "HARD_CAP_24H" in s[0]["diagnostics"]


def test_recent_open_stays_open():
    s, _ = fs.assemble([m(1, "2026-09-22 10:00", "ZDU004 Start")], NOW)
    assert s[0]["status"] == "OPEN"


def test_new_start_closes_reporters_earlier_session():
    s, _ = fs.assemble([m(1, "2026-09-21 08:00", "ZAA111 Start"), m(2, "2026-09-21 10:00", "ZBB222 Start"),
                        m(3, "2026-09-21 11:00", "ZBB222 End")], NOW)
    assert s[0]["status"] == "AUTO_CLOSED" and "START_WHILE_REPORTER_OPEN" in s[0]["diagnostics"]
    assert s[1]["status"] == "COMPLETED"


def test_late_end_after_24h_cap_not_completed():
    s, _ = fs.assemble([m(1, "2026-09-19 08:00", "ZAA111 Start"), m(2, "2026-09-21 08:00", "ZAA111 End")], NOW)
    assert s[0]["status"] == "AUTO_CLOSED"


def test_bare_end_and_ambiguity():
    s, e = fs.assemble([m(1, "2026-09-21 08:00", "ZAA111 Start", "A"), m(2, "2026-09-21 09:00", "End", "A")], NOW)
    assert s[0]["status"] == "COMPLETED" and not e
    s, e = fs.assemble([m(1, "2026-09-21 08:00", "ZAA111 Start", "A"), m(2, "2026-09-21 08:05", "ZBB222 Start", "B"),
                        m(3, "2026-09-21 09:00", "End", "C")], NOW)
    assert e and e[0]["code"] == "AMBIGUOUS_END_TARGET"


def test_end_without_start_is_exception():
    _, e = fs.assemble([m(1, "2026-09-21 09:00", "ZAA111 End")], NOW)
    assert e[0]["code"] == "END_WITHOUT_START"


def test_photo_count_between_start_and_end():
    msgs = [m(1, "2026-09-21 08:00", "ZAA111 Start"), m(2, "2026-09-21 08:10", "", kind="MEDIA"),
            m(3, "2026-09-21 08:20", "", kind="MEDIA"), m(4, "2026-09-21 09:00", "ZAA111 End"),
            m(5, "2026-09-21 09:05", "", kind="MEDIA")]
    s, _ = fs.assemble(msgs, NOW)
    assert s[0]["photos"] == 2


def test_same_message_key_processed_once():
    a = m(1, "2026-09-21 08:00", "ZAA111 Start")
    s, _ = fs.assemble([a, dict(a)], NOW)
    assert len(s) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
