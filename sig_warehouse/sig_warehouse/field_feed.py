"""Field visit feed runner (gate F1: SHADOW). See docs/field_visit_feed_design.md.

Every 15 minutes: pull new Inbox rows from the Google sheet by row cursor, store the
relevant group messages (SIG Field Message), assemble sessions with field_sessions,
and upsert them into SIG Field Session. In Shadow mode nothing else is written: no
SIG Field Visit, no evidence event, no Site Cycle change. Live posting is gate F2.

Mode is set on SIG Field Ops Settings.feed_mode (Off / Shadow / Live). In Live mode (gate
F2) each COMPLETED, PENDING session is posted as a FIELD_VISIT_COMPLETED event through the
existing register_evidence_event endpoint (one code path to SIG Field Visit / Site Cycle),
its SIG Site is created and linked when missing, and a stale feed raises a ToDo.
"""
import hashlib
from datetime import datetime, timedelta, timezone

import frappe

from sig_warehouse.sig_warehouse import field_sessions as fs

BACKFILL_FROM = "2026-09-12"           # first run backfills from here (ERP visits end 2026-09-13 09:15)
ERP_LAST_VISIT = "2026-09-13 09:15:33"  # sessions starting at/before this already exist in ERP (E0 restore)
MAX_ROWS_PER_RUN = 1500                 # keeps one run well inside the scheduler timeout during backfill
WINDOW_HOURS = 72                       # re-assembly window; results are trusted from window start + 24 h
RIYADH = timezone(timedelta(hours=3))
POST_BATCH = 25                          # sessions posted per run
STALE_HOURS = 24                         # no Inbox row at all for this long raises an alert
DEFAULT_WH = "\u0645\u0633\u062a\u0648\u062f\u0639 \u0627\u0644\u0645\u0632\u0627\u062d\u0645\u064a\u0629 - SIG"
# group stream -> the project label the RV80 evidence events used on Site Cycles (5g / Capex-9 / incident)
STREAM_PROJECT = {"ti5g": "5g", "ticpx": "Capex-9", "tiinc": "incident"}


def _now():
    return datetime.now(timezone.utc).astimezone(RIYADH).replace(tzinfo=None)


def _employee_by_phone():
    out = {}
    for e in frappe.get_all("Employee", fields=["name", "cell_number"]):
        digits = "".join(c for c in str(e.cell_number or "") if c.isdigit())[-9:]
        if digits:
            out[digits] = e.name
    # Manual overrides (site_visits.assign_person) take precedence over the automatic match -
    # a PM's correction must stick even if the number never gets added to the Employee record.
    for m in frappe.get_all("SIG Field Reporter Map", fields=["reporter_phone", "employee"]):
        digits = "".join(c for c in str(m.reporter_phone or "") if c.isdigit())[-9:]
        if digits:
            out[digits] = m.employee
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
            "end_at": fs.fmt(s["end_at"]) if s["end_at"] else None, "status": s["status"],
            "hours": s["hours"] if s["hours"] is not None else 0,
            "activity_code": s["activity_code"], "photo_count": s["photos"], "diagnostics": ",".join(diags),
            "disposition": disposition, "start_msg": s["start_msg"], "end_msg": s["end_msg"],
        }
        if frappe.db.exists("SIG Field Session", s["session_key"]):
            existing = frappe.db.get_value("SIG Field Session", s["session_key"], ["posted", "corrected_by"], as_dict=True)
            if existing.posted or existing.corrected_by:
                continue  # posted or PM-corrected (site_visits.py) sessions are immutable here;
                          # a re-run from raw messages must not silently undo a human fix
            frappe.db.set_value("SIG Field Session", s["session_key"], values, update_modified=False)
        else:
            frappe.get_doc(dict(doctype="SIG Field Session", session_key=s["session_key"], **values)).insert(
                ignore_permissions=True)
        n += 1
    return n


# ------------------------------------------------------------------ F2: posting
def _batch_id(session_key):
    return "FEED-" + hashlib.sha1(session_key.encode("utf-8")).hexdigest()[:20]


def _call_evidence(payload):
    """Run the register_evidence_event API Server Script in-process with these params."""
    old = frappe.local.form_dict
    frappe.local.form_dict = frappe._dict(payload)
    try:
        frappe.response.pop("message", None)
        frappe.get_doc("Server Script", "register_evidence_event").execute_method()
        return frappe.response.get("message") or {}
    finally:
        frappe.local.form_dict = old


def _ensure_site(site):
    if frappe.db.exists("SIG Site", site):
        return False
    frappe.get_doc({"doctype": "SIG Site", "site_id": site, "site_name": site,
                    "default_warehouse": DEFAULT_WH}).insert(ignore_permissions=True)
    return True


def post_session(name):
    """Post one PENDING/COMPLETED SIG Field Session. Returns a small result dict."""
    s = frappe.get_doc("SIG Field Session", name)
    if s.posted:
        return {"result": "already_posted"}
    if s.status != "COMPLETED" or s.disposition != "PENDING":
        return {"result": "not_eligible", "status": s.status, "disposition": s.disposition}
    created_site = _ensure_site(s.site_key)
    who = frappe.db.get_value("Employee", s.employee, "employee_name") if s.employee else None
    now = fs.fmt(_now())
    event_id = _batch_id(s.name) + "-000001"
    payload = {
        "event_code": "FIELD_VISIT_COMPLETED", "site_id": s.site_key, "site_key": s.site_key,
        "occurred_at": str(s.end_at)[:19], "recorded_at": now, "project": STREAM_PROJECT.get(s.stream, s.stream),
        "artifact_ref": s.name, "batch_id": _batch_id(s.name), "seq": 1, "source_sub": "WA-FEED",
        "source_workbook": "sig_warehouse.field_feed", "operator": "field_feed", "machine": "erpnext",
        "core_version": "F2", "session_key": s.name, "status": "COMPLETED", "start_at": str(s.start_at)[:19],
        "end_at": str(s.end_at)[:19], "duration_hours": s.hours or 0, "reporter": s.reporter,
        "reporter_name": who or s.reporter_name, "activity_code": s.activity_code or "UNSPECIFIED",
        "photo_count": s.photo_count or 0, "visit_ordinal": 0, "diagnostic": s.diagnostics or "",
    }
    res = _call_evidence(payload)
    ok = res.get("result") in ("created", "duplicate") or bool(
        frappe.db.exists("SIG Evidence Event", event_id) and frappe.db.exists("SIG Field Visit", s.name))
    if not ok:
        note = "POST_FAILED:" + str(res.get("reason") or res)[:80]
        frappe.db.set_value("SIG Field Session", s.name, "diagnostics",
                            ((s.diagnostics or "") + "," + note).strip(","), update_modified=False)
        return {"result": "failed", "detail": res}
    cycle = res.get("cycle") or frappe.db.get_value("SIG Evidence Event", event_id, "cycle")
    for dt, dn in (("SIG Field Visit", s.name), ("SIG Evidence Event", event_id), ("SIG Site Cycle", cycle)):
        if dn and frappe.db.exists(dt, dn):
            frappe.db.set_value(dt, dn, "site", s.site_key, update_modified=False)
    frappe.db.set_value("SIG Field Session", s.name, {
        "posted": 1, "disposition": "POSTED",
        "visit": s.name if frappe.db.exists("SIG Field Visit", s.name) else None}, update_modified=False)
    frappe.db.commit()
    return {"result": res.get("result") or "created", "site_created": created_site, "cycle": cycle}


def _post_pending(limit=POST_BATCH):
    names = frappe.get_all("SIG Field Session", filters={"disposition": "PENDING", "status": "COMPLETED", "posted": 0},
                           order_by="start_at asc", pluck="name", limit_page_length=limit)
    done = failed = new_sites = 0
    for name in names:
        try:
            r = post_session(name)
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title="SIG field feed post failed: " + name)
            failed += 1
            continue
        if r.get("result") in ("created", "duplicate"):
            done += 1
            new_sites += 1 if r.get("site_created") else 0
        else:
            failed += 1
    return {"posted": done, "failed": failed, "sites_created": new_sites}


# ------------------------------------------------------------------ health
def _alert_user(st):
    user = st.get("feed_alert_user")
    if user:
        return user
    for u in frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"):
        if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled"):
            return u
    return "Administrator"


def _alert(st, key, text):
    """One open ToDo per alert key (deduplicated)."""
    if frappe.db.exists("ToDo", {"reference_type": "SIG Field Ops Settings",
                                 "description": ["like", "[%s]%%" % key], "status": "Open"}):
        return
    frappe.get_doc({"doctype": "ToDo", "allocated_to": _alert_user(st), "status": "Open", "priority": "High",
                    "reference_type": "SIG Field Ops Settings", "reference_name": "SIG Field Ops Settings",
                    "description": "[%s] %s" % (key, text)}).insert(ignore_permissions=True)


def _close_alert(key):
    for n in frappe.get_all("ToDo", filters={"description": ["like", "[%s]%%" % key], "status": "Open"}, pluck="name"):
        frappe.db.set_value("ToDo", n, "status", "Closed")


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
        rows, last_n, caught_up, last_row_at = [], cursor, True, None
        for n, row in fs.fetch_rows(cursor):
            last_n = n
            last_row_at = row[0]
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
        sites = set(frappe.get_all("SIG Site", pluck="name", limit_page_length=0))
        sessions, exceptions = fs.assemble(window, ref, known_sites=sites)
        touched = _upsert_sessions(sessions, trusted_from, sites, _employee_by_phone())
        for e in exceptions:
            if e["at"] >= trusted_from and frappe.db.exists("SIG Field Message", e["msg_key"]):
                frappe.db.set_value("SIG Field Message", e["msg_key"], "diagnostic", e["code"], update_modified=False)

        posted = {"posted": 0, "failed": 0, "sites_created": 0}
        if mode == "Live" and caught_up:
            frappe.db.commit()
            posted = _post_pending()

        newest = frappe.db.sql("select max(occurred_at) from `tabSIG Field Message`")[0][0]
        inbox_at = last_row_at or st.get("feed_last_inbox_at")
        stale_h = (now - fs.parse_ts(str(inbox_at))).total_seconds() / 3600.0 if inbox_at else 0
        status = "OK (%s)%s: +%d messages, %d sessions" % (mode, "" if caught_up else " backfilling", stored, touched)
        if mode == "Live":
            status += ", posted %d (%d failed, %d sites created)" % (
                posted["posted"], posted["failed"], posted["sites_created"])
        if stale_h > STALE_HOURS:
            status = "STALE: no Inbox rows for %d h" % stale_h
            _alert(st, "SIG-FEED-STALE", "The WhatsApp group feed has had no new sheet rows for %d hours (last row %s). "
                   "Check the Maytapi automation and the Google sheet 'Whatsapp to sheet Automation'." % (stale_h, inbox_at))
        else:
            _close_alert("SIG-FEED-STALE")
        _close_alert("SIG-FEED-ERROR")
        frappe.db.set_value("SIG Field Ops Settings", "SIG Field Ops Settings", {
            "feed_cursor": last_n, "feed_last_run": fs.fmt(now), "feed_last_message_at": newest,
            "feed_last_inbox_at": str(inbox_at)[:19] if inbox_at else None,
            "feed_backfill_done": 1 if (caught_up or st.get("feed_backfill_done")) else 0,
            "feed_status": status, "feed_error": None})
        frappe.db.commit()
        return {"result": "ok", "mode": mode, "cursor": last_n, "stored": stored, "sessions": touched,
                "exceptions": len(exceptions), **posted}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title="SIG field feed run failed")
        frappe.db.set_value("SIG Field Ops Settings", "SIG Field Ops Settings", {
            "feed_last_run": fs.fmt(now), "feed_status": "ERROR", "feed_error": frappe.get_traceback()[-900:]})
        frappe.db.commit()
        _alert(st, "SIG-FEED-ERROR", "The field visit feed run failed; see SIG Field Ops Settings > Last Error and the Error Log.")
        frappe.db.commit()
        return {"result": "error"}


@frappe.whitelist()
def sig_field_feed_run_now(rebuild=0):
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted", frappe.PermissionError)
    return run_feed(rebuild=bool(int(rebuild)))


@frappe.whitelist()
def sig_field_feed_post_one(session_key):
    """Pilot: post exactly one PENDING/COMPLETED session, whatever the feed mode."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted", frappe.PermissionError)
    return post_session(session_key)


@frappe.whitelist()
def sig_field_backfill_historical(payload):
    """One-off import of pre-feed (2026-07-28..09-10) sessions computed by the legacy Excel
    pipeline (SIG Documentation - Task Checklist 2.02.xlsm, Field Sessions sheet); those visits
    already exist in ERP only as a thin site+timestamp ledger (SIG Field Visit 'EV1|...' records,
    source FieldOps_SyncAll), never as SIG Field Session rows, so the Site Visits PM page never
    showed them. Each row here is inserted as-is (already resolved client-side against Employee/
    SIG Site/SIG Field Reporter Map/the EV1 ledger) - no evidence event or new SIG Field Visit is
    created, so Site Cycle rollups are untouched. Idempotent: existing session_keys are skipped.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted", frappe.PermissionError)
    rows = frappe.parse_json(payload) if isinstance(payload, str) else payload
    inserted = skipped = 0
    for r in rows:
        if frappe.db.exists("SIG Field Session", r["session_key"]):
            skipped += 1
            continue
        frappe.get_doc(dict(doctype="SIG Field Session", **r)).insert(ignore_permissions=True)
        inserted += 1
    frappe.db.commit()
    return {"inserted": inserted, "skipped": skipped}
