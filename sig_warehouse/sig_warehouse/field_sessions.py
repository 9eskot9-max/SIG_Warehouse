"""Field visit sessions from WhatsApp group messages (design: docs/field_visit_feed_design.md).

Pure Python, no frappe import: classifier + session assembler + Inbox fetch, so it
is unit-testable and the same code drives the read-only preview (gate F0), the
shadow run (F1) and the scheduler (F2). Rules follow the RV80 FieldOps design
(session-pipeline-design.md sections 4.4, 8, 10): deterministic pairing, no
guessing, 6 h inactivity grace, 24 h hard cap, every fallback recorded.
"""
import csv
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

SHEET_ID = "1wgxHyL5IFxaCIgaS0TBelzGQVXuvgrFnHibIpc3IoFo"
GRACE_HOURS = 6
CAP_HOURS = 24
DUP_START_MIN = 10          # same reporter + same site Start within this is a duplicate
DUP_END_MIN = 10            # repeated End for the session that just closed
MAX_TEXT = 80               # a Start/End command is short; longer text is conversation

# group conversation id -> project stream (the three Sync_Index streams)
STREAM_BY_GROUP = {
    "120363147758691305@g.us": "ti5g",      # SIG_5G_Collocation
    "966550946813-1635410699@g.us": "ticpx",  # Capex-DG/DC/HVAC Update
    "120363027593567578@g.us": "tiinc",     # Incident Recovery
}
ACTIVITIES = {"SURVEY", "INSTALL", "HANDOVER", "WARRANTY", "DISMANTLE", "SNAG"}
ACTIVITY_ALIAS = {"HO": "HANDOVER", "INSTALLATION": "INSTALL", "IMPLEMENT": "INSTALL"}

_SITE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{1,4}\d{3,5}[A-Za-z]?|\d{3}-\d{2}-\d{3})(?![A-Za-z0-9])")
_CMD = re.compile(r"(?<![A-Za-z])(start|end)(?![A-Za-z])", re.I)


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_ts(s):
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- classify
def classify_text(text):
    """-> (kind, site, activity_raw, activity_code); kind is START | END | OTHER."""
    t = (text or "").strip()
    if not t or len(t) > MAX_TEXT:
        return "OTHER", None, None, None
    m = _CMD.search(t)
    if not m:
        return "OTHER", None, None, None
    kind = m.group(1).upper()
    rest = t[:m.start()] + " " + t[m.end():]
    sm = _SITE.search(rest)
    site = sm.group(1).upper() if sm else None
    if site is None and len(re.findall(r"\w+", t)) > 3:
        return "OTHER", None, None, None      # "Please start the activity" is conversation, not a command
    act_raw = act_code = None
    if kind == "START":
        after = t[m.end():]
        if ";" in after:
            act_raw = after.split(";", 1)[1].strip(" .!‏")
            key = act_raw.upper()
            key = ACTIVITY_ALIAS.get(key, key)
            act_code = key if key in ACTIVITIES else "UNRESOLVED"
        else:
            act_code = "UNSPECIFIED"
    return kind, site, act_raw, act_code


def parse_row(row):
    """Inbox row (ReceivedAt, Payload, MsgId, Conversation, MsgType) -> message dict or None."""
    received, payload, msgid, conv, mtype = row
    stream = STREAM_BY_GROUP.get(conv)
    if not stream or mtype not in ("text", "image"):
        return None
    try:
        p = json.loads(payload)
        m = p.get("message") or {}
        user = p.get("user") or {}
    except (ValueError, AttributeError):
        return None
    text = (m.get("text") or m.get("caption") or "") if mtype == "text" else ""
    kind, site, act_raw, act_code = classify_text(text) if mtype == "text" else ("MEDIA", None, None, None)
    phone = str(user.get("phone") or re.sub(r"\D", "", str(user.get("id") or "")) or "")
    return {
        "msg_key": msgid, "at": parse_ts(received), "stream": stream, "group": conv,
        "reporter": phone, "reporter_name": user.get("name") or phone, "kind": kind,
        "site": site, "activity_raw": act_raw, "activity_code": act_code, "text": text,
    }


# ---------------------------------------------------------------- assemble
def assemble(messages, now, known_sites=None):
    """Messages -> (sessions, exceptions). Sessions: COMPLETED / AUTO_CLOSED / OPEN."""
    sessions, exceptions = [], []
    open_by_stream = {}       # stream -> list of open sessions
    last_closed = {}          # (stream, reporter, site) -> session
    seen = set()

    def new_exc(msg, code, note=""):
        exceptions.append({"code": code, "at": fmt(msg["at"]), "stream": msg["stream"], "site": msg["site"],
                           "reporter": msg["reporter_name"], "text": msg["text"], "note": note})

    def close(s, at, status, diag=None):
        s["end_at"], s["status"] = at, status
        s["hours"] = round((at - s["start_at"]).total_seconds() / 3600.0, 2)
        if diag:
            s["diagnostics"].append(diag)
        open_by_stream[s["stream"]].remove(s)
        last_closed[(s["stream"], s["reporter"], s["site"])] = s

    def expire(stream, at):
        for s in list(open_by_stream.get(stream, [])):
            if at - s["start_at"] > timedelta(hours=CAP_HOURS):
                close(s, s["start_at"] + timedelta(hours=CAP_HOURS), "AUTO_CLOSED", "HARD_CAP_24H")
            elif at - s["last_activity"] > timedelta(hours=GRACE_HOURS):
                close(s, s["last_activity"], "AUTO_CLOSED", "START_WITHOUT_END")

    for msg in sorted(messages, key=lambda m: (m["at"], m["msg_key"])):
        if msg["msg_key"] in seen:
            continue
        seen.add(msg["msg_key"])
        st = msg["stream"]
        opens = open_by_stream.setdefault(st, [])
        expire(st, msg["at"])

        for s in opens:                      # activity keeps a session alive; media counts as photos
            if s["reporter"] == msg["reporter"]:
                s["last_activity"] = msg["at"]
                if msg["kind"] == "MEDIA":
                    s["photos"] += 1

        if msg["kind"] == "START":
            if not msg["site"]:
                new_exc(msg, "START_UNRESOLVED_SITE", "Start with no site code")
                continue
            dup = next((s for s in opens if s["reporter"] == msg["reporter"] and s["site"] == msg["site"]
                        and msg["at"] - s["start_at"] <= timedelta(minutes=DUP_START_MIN)), None)
            if dup:
                continue
            for s in [x for x in opens if x["reporter"] == msg["reporter"]]:
                close(s, msg["at"], "AUTO_CLOSED", "START_WHILE_REPORTER_OPEN")
            s = {"session_key": "%s|%s|%s|%s" % (msg["stream"], msg["group"], msg["msg_key"], msg["site"]),
                 "stream": st, "group": msg["group"], "site": msg["site"], "reporter": msg["reporter"],
                 "reporter_name": msg["reporter_name"], "start_at": msg["at"], "end_at": None,
                 "last_activity": msg["at"], "activity_code": msg["activity_code"],
                 "activity_raw": msg["activity_raw"], "photos": 0, "status": "OPEN", "hours": None,
                 "diagnostics": [], "start_msg": msg["msg_key"], "end_msg": None}
            if msg["activity_code"] == "UNRESOLVED":
                s["diagnostics"].append("UNKNOWN_ACTIVITY")
            opens.append(s)
            sessions.append(s)
        elif msg["kind"] == "END":
            target, diag = None, None
            if msg["site"]:
                same = [s for s in opens if s["site"] == msg["site"]]
                mine = [s for s in same if s["reporter"] == msg["reporter"]]
                if len(mine) == 1:
                    target = mine[0]
                elif len(same) == 1 and not mine:
                    target, diag = same[0], "END_REPORTER_DIFFERENT"
                elif len(same) > 1:
                    new_exc(msg, "AMBIGUOUS_END_TARGET", "several open sessions at this site")
                    continue
            else:
                mine = [s for s in opens if s["reporter"] == msg["reporter"]]
                if len(mine) == 1:
                    target = mine[0]
                elif len(mine) > 1:
                    new_exc(msg, "AMBIGUOUS_END_TARGET", "bare End, reporter has several open sessions")
                    continue
                elif len(opens) == 1:
                    target, diag = opens[0], "BARE_END_PROJECT_FALLBACK"
                elif len(opens) > 1:
                    new_exc(msg, "AMBIGUOUS_END_TARGET", "bare End, several open sessions in the stream")
                    continue
            if target is None:
                lc = last_closed.get((st, msg["reporter"], msg["site"]))
                if lc and lc["end_at"] and msg["at"] - lc["end_at"] <= timedelta(minutes=DUP_END_MIN):
                    continue                      # repeated End for the session that just closed
                new_exc(msg, "END_WITHOUT_START", "no open session to close")
                continue
            if msg["at"] - target["start_at"] > timedelta(hours=CAP_HOURS):
                close(target, target["start_at"] + timedelta(hours=CAP_HOURS), "AUTO_CLOSED", "HARD_CAP_24H")
            else:
                target["end_msg"] = msg["msg_key"]
                close(target, msg["at"], "COMPLETED", diag)

    for st in list(open_by_stream):
        expire(st, now)
    for s in sessions:
        if known_sites is not None and s["site"] not in known_sites:
            s["diagnostics"].append("UNRESOLVED_SITE")
    return sessions, exceptions


# ---------------------------------------------------------------- fetch
def _gviz(query, timeout=90):
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq?" % SHEET_ID) + urllib.parse.urlencode(
        {"tqx": "out:csv", "sheet": "Inbox", "tq": query})
    raw = urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8")
    if raw.startswith("{"):
        raise RuntimeError("gviz error: " + raw[:300])
    return list(csv.reader(io.StringIO(raw)))[1:]


def first_row_at_or_after(since):
    """Row ordinal (0-based) of the first Inbox row received at/after ``since`` (append-only sheet)."""
    col = _gviz("select A")
    for i, r in enumerate(col):
        if r and r[0] >= since:
            return i
    return len(col)


def fetch_rows(cursor, chunk=400):
    """Yield (ordinal, row) for Inbox rows after ``cursor``; row = (ReceivedAt, Payload, MsgId, Conversation, MsgType)."""
    n = cursor
    while True:
        rows = _gviz("select A,C,D,E,F limit %d offset %d" % (chunk, n))
        if not rows:
            return
        for r in rows:
            n += 1
            if len(r) >= 5:
                yield n, (r[0], r[1], r[2], r[3], r[4])
        if len(rows) < chunk:
            return
