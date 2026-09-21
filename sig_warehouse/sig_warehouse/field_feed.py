"""Field visit feed runner (gate F1: SHADOW). See docs/field_visit_feed_design.md.

Every 15 minutes: pull new Inbox rows from the Google sheet by row cursor, store the
relevant group messages (SIG Field Message), assemble sessions with field_sessions,
and upsert them into SIG Field Session. In Shadow mode nothing else is written: no
SIG Field Visit, no evidence event, no Site Cycle change. Live posting is gate F2.

Mode is set on SIG Field Ops Settings.feed_mode (Off / Shadow / Live). Live is not
implemented in this release; the runner treats it as Shadow.
"""
from datetime import datetime, timedelta, timezone

import frappe

from sig_warehouse.sig_warehouse import field_sessions as fs

BACKFILL_FROM = "2026-09-12"           # first run backfills from here (ERP visits end 2026-09-13 09:15)
ERP_LAST_VISIT = "2026-09-13 09:15:33"  # sessions starting at/before this already exist in ERP (E0 restore)
MAX_ROWS_PER_RUN = 1500                 # keeps one run well inside the scheduler timeout during backfill
WINDOW_HOURS = 72                       # re-assembly window; results are trusted from window start + 24 h
RIYADH = timezone(timedelta(hours=3))


def _now():
    return datetime.now(timezone.utc).astimezone(RIYADH).replace(tzinfo=None)


def _employee_by_phone():
    out = {}
    for e in frappe.get_all("Employee", fields=["name", "cell_number"]):
        digits = "".join(c for c in str(e.cell_number or "") if c.isdigit())[-9:]
        if digits:
            out[digits] = e.name
    return out


def _store_messages(rows):
    """Insert relevant messages not seen before; returns (stored, last message time)."""
    stored, last_at = 0, None
    for msg in rows:
        if frappe.db.exists("SIG Field Message", msg["msg_key"]):
            continue
        frappe.get_doc({
            "doctype": "SIG Field Message", "msg_key": msg["msg_key"], "stream": msg["stream"], "group": msg["group"],
            "occurred_at": fs.fmt(msg["at"]), "reporter": msg["reporter"], "reporter_name": msg["reporter_name"],
            "kind": msg["kind"], "site_key": msg["site"], "activity_code": msg["activity_code"],
            "activity_raw": msg["activity_raw"], "text": (msg["text"] or "")[:200],
        }).insert(ignore_permissions=True)
        stored += 1
        last_at = fs.fmt(msg["at"]) if last_at is None or fs.fmt(msg["at"]) > last_at else last_at
    return stored, last_at


def _load_window(since):
    out = []
    for r in frappe.get_all(
            "SIG Field Message", filters={"occurred_at": [">=", since], "kind": ["in", ["START", "END", "MEDIA"]]},
            fields=["msg_key", "stream", "group", "occurred_at", "reporter", "reporter_name", "kind", "site_key",
                    "activity_code", "activity_raw", "text"], limit_page_length=0):
        out.append({"msg_key": r.msg_key, "at": fs.parse_ts(str(r.occurred_at)), "stream": r.stream, "group": r.group,
                    "reporter": r.reporter or "", "reporter_name": r.reporter_name or r.reporter or "",
                    "kind": r.kind, "site": r.site_key, "activity_raw": r.activity_raw,
                    "activity_code": r.activity_code, "text": r.text or ""})
    return out


def _upsert_sessions(sessions, trusted_from, sites, emp_by_phone):
    n = 0
    for s in sessions:
        if fs.fmt(s["start_at"]) < trusted_from:
            continue
        diags = list(s["diagnostics"])
        emp = emp_by_phone.get(s["reporter"][-9:])
        if not emp:
            diags.append("NO_EMPLOYEE_FOR_PHONE")
        started = fs.fmt(s["start_at"])
        if started <= ERP_LAST_VISIT and s["status"] != "OPEN":
            disposition = "IN_ERP_WINDOW"
        elif "AMBIGUOUS_SESSION_OWNER" in diags or "END_REPORTER_DIFFERENT" in diags or "BARE_END_PROJECT_FALLBACK" in diags:
            disposition = "REVIEW"
        else:
            disposition = "PENDING"
        values = {
            "stream": s["stream"], "group": s["group"], "site_key": s["site"],
            "site": s["site"] if s["site"] in sites else None, "reporter": s["reporter"],
            "reporter_name": s["reporter_name"], "employee": emp, "start_at": started,
            "end_at": fs.fmt(s["end_at"]) if s["end_at"] else None, "status": s["status"], "hours": s["hours"],
            "activity_code": s["activity_code"], "photo_count": s["photos"], "diagnostics": ",".join(diags),
            "disposition": disposition, "start_msg": s["start_msg"], "end_msg": s["end_msg"],
        }
        if frappe.db.exists("SIG Field Session", s["session_key"]):
            if frappe.db.get_value("SIG Field Session", s["session_key"], "posted"):
                continue                                   # posted sessions are immutable (corrections are amendments)
            frappe.db.set_value("SIG Field Session", s["session_key"], values, update_modified=False)
        else:
            frappe.get_doc(dict(doctype="SIG Field Session", session_key=s["session_key"], **values)).insert(
                ignore_permissions=True)
        n += 1
    return n


def run_feed(rebuild=False):
    st = frappe.get_single("SIG Field Ops Settings")
    mode = st.get("feed_mode") or "Shadow"
    if mode == "Off":
        return {"result": "off"}
    now = _now()
    try:
        cursor = int(st.get("feed_cursor") or 0)
        if not cursor:
            cursor = fs.first_row_at_or_after(BACKFILL_FROM + " 00:00:00")
        rows, last_n, caught_up = [], cursor, True
        for n, row in fs.fetch_rows(cursor):
            last_n = n
            msg = fs.parse_row(row)
            if msg and msg["kind"] in ("START", "END", "MEDIA"):
                rows.append(msg)
            if n - cursor >= MAX_ROWS_PER_RUN:
                caught_up = False
                break
        stored, last_at = _store_messages(rows)

        # Full rebuild until the backfill has caught up once (or on demand); afterwards a 72 h window is enough
        # because no session lasts more than 24 h. While still catching up, time is measured from the newest
        # stored message so a half-loaded backlog is not expired by the real clock.
        full = rebuild or not caught_up or not st.get("feed_backfill_done")
        newest_now = frappe.db.sql("select max(occurred_at) from `tabSIG Field Message`")[0][0]
        ref = now if (caught_up or not newest_now) else fs.parse_ts(str(newest_now))
        window_start = "2000-01-01 00:00:00" if full else fs.fmt(ref - timedelta(hours=WINDOW_HOURS))
        trusted_from = "2000-01-01 00:00:00" if full else fs.fmt(ref - timedelta(hours=WINDOW_HOURS - 24))
        window = _load_window(window_start)
        sites = {r.name for r in frappe.get_all("SIG Site", pluck="name", limit_page_length=0)}
        sessions, exceptions = fs.assemble(window, ref, known_sites=sites)
        touched = _upsert_sessions(sessions, trusted_from, sites, _employee_by_phone())
        for e in exceptions:
            if e["at"] >= trusted_from and frappe.db.exists("SIG Field Message", e["msg_key"]):
                frappe.db.set_value("SIG Field Message", e["msg_key"], "diagnostic", e["code"], update_modified=False)

        newest = frappe.db.sql("select max(occurred_at) from `tabSIG Field Message`")[0][0]
        frappe.db.set_value("SIG Field Ops Settings", "SIG Field Ops Settings", {
            "feed_cursor": last_n, "feed_last_run": fs.fmt(now), "feed_last_message_at": newest,
            "feed_backfill_done": 1 if (caught_up or st.get("feed_backfill_done")) else 0,
            "feed_status": "OK (%s)%s: +%d messages, %d sessions" % (mode, "" if caught_up else " backfilling", stored, touched),
            "feed_error": None})
        frappe.db.commit()
        return {"result": "ok", "mode": mode, "cursor": last_n, "stored": stored, "sessions": touched,
                "exceptions": len(exceptions)}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title="SIG field feed run failed")
        frappe.db.set_value("SIG Field Ops Settings", "SIG Field Ops Settings", {
            "feed_last_run": fs.fmt(now), "feed_status": "ERROR", "feed_error": frappe.get_traceback()[-900:]})
        frappe.db.commit()
        return {"result": "error"}


@frappe.whitelist()
def sig_field_feed_run_now(rebuild=0):
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted", frappe.PermissionError)
    return run_feed(rebuild=bool(int(rebuild)))
