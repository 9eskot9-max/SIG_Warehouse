"""Visit-first posting: every closed session with a registered site becomes a visit."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1] / "sig_warehouse"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Doc(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def feed_with(session, sites=("ZRW957",), writer=None, visits=None, tcns=()):
    fake = ModuleType("frappe")
    fake.whitelist = lambda: lambda fn: fn
    fake.get_all = lambda doctype, **kwargs: [Doc(**t) for t in tcns] if doctype == "SIG Evidence Event" else []
    sys.modules["frappe"] = fake
    feed = load("feed_visit_first", ROOT / "field_feed.py")
    visits = {} if visits is None else visits
    writes, inserted, calls = [], [], []

    def exists(doctype, name):
        if doctype == "SIG Site":
            return name in sites
        if doctype == "SIG Field Visit":
            return name in visits
        return False

    def get_value(doctype, name, field):
        if doctype == "SIG Field Visit":
            return (visits.get(name) or {}).get(field)
        return None

    def set_value(doctype, name, values, *args, **kwargs):
        writes.append((doctype, name, values))
        if doctype == "SIG Field Session" and isinstance(values, dict):
            for k, v in values.items():
                setattr(session, k, v)

    class NewDoc(Doc):
        def insert(self, ignore_permissions=False):
            self.name = self.session_key
            visits[self.name] = dict(vars(self))
            inserted.append(self)
            return self

    fake.get_doc = lambda arg, name=None: session if arg == "SIG Field Session" else NewDoc(**arg)
    fake.db = SimpleNamespace(exists=exists, get_value=get_value, set_value=set_value, commit=lambda: None)
    feed._now = lambda: __import__("datetime").datetime(2026, 11, 15, 12, 0)

    def call(payload):
        calls.append(payload)
        return (writer or (lambda p: {"result": "created", "cycle": "CYC-1"}))(payload)

    feed._call_evidence = call
    return feed, writes, inserted, calls, visits


def session(**kw):
    base = dict(name="ti5g|g|m1|ZRW957", posted=0, visit=None, site_key="ZRW957", status="COMPLETED",
                disposition="PENDING", diagnostics="", stream="ti5g", employee=None, reporter="9665",
                reporter_name="Reporter", start_at="2026-11-11 19:30:47", end_at="2026-11-11 19:33:54",
                hours=0.05, activity_code="UNSPECIFIED", photo_count=0, scope="")
    base.update(kw)
    return Doc(**base)


NO_CYCLE = lambda p: {"result": "exception",
                      "reason": "CYCLE_ATTRIBUTION:no compatible open site cycle; review the completed visit in Site Visits"}


def test_auto_closed_session_is_posted_as_auto_closed_visit():
    s = session(status="AUTO_CLOSED", diagnostics="START_WITHOUT_END", end_at="2026-11-11 19:30:47", hours=0)
    feed, writes, _inserted, calls, _visits = feed_with(s)
    assert feed.post_session(s.name)["result"] == "created"
    assert calls[0]["status"] == "AUTO_CLOSED" and "START_WITHOUT_END" in calls[0]["diagnostic"]
    assert s.posted == 1 and s.disposition == "POSTED"


def test_untyped_visit_takes_the_tcn_type_and_a_typed_one_keeps_its_own():
    pat = {"planned_activity": "PAT", "occurred_at": "2026-11-11 00:00:00", "tcn_window_start": None, "tcn_window_end": None}
    s = session()
    feed, _writes, _inserted, calls, _visits = feed_with(s, tcns=[pat])
    feed.post_session(s.name)
    assert calls[0]["activity_code"] == "PAT" and calls[0]["scope"] == "PAT" and s.activity_code == "PAT"
    typed = session(activity_code="HANDOVER")
    feed, _writes, _inserted, calls, _visits = feed_with(typed, tcns=[pat])
    feed.post_session(typed.name)
    assert calls[0]["activity_code"] == "HANDOVER"


def test_open_session_is_not_posted():
    s = session(status="OPEN", end_at=None)
    feed, _writes, _inserted, calls, _visits = feed_with(s)
    assert feed.post_session(s.name)["result"] == "not_eligible" and not calls


def test_code_missing_from_site_master_is_not_created_as_a_site():
    s = session(site_key="ZJD0881")
    feed, _writes, inserted, calls, _visits = feed_with(s)
    result = feed.post_session(s.name)
    assert result == {"result": "not_eligible", "reason": "SITE_NOT_IN_MASTER"} and not calls and not inserted


def test_visit_without_a_cycle_is_recorded_unallocated():
    s = session()
    feed, _writes, inserted, calls, visits = feed_with(s, writer=NO_CYCLE)
    result = feed.post_session(s.name)
    assert result["result"] == "unallocated"
    assert len(inserted) == 1 and inserted[0].cycle is None and inserted[0].site_key == "ZRW957"
    assert s.posted == 1 and s.disposition == "POSTED" and s.visit == s.name
    assert "UNALLOCATED" in s.diagnostics and "CYCLE_ATTRIBUTION_EXCEPTION" not in s.diagnostics
    assert "no compatible open site cycle" in s.diagnostics


def test_unallocated_visit_is_allocated_later_through_the_writer():
    s = session()
    visits = {}
    feed, _writes, _inserted, _calls, visits = feed_with(s, writer=NO_CYCLE, visits=visits)
    feed.post_session(s.name)
    assert feed.post_session(s.name)["result"] == "already_posted"      # no hint: nothing to do
    feed2, _w, inserted2, calls2, _v = feed_with(s, visits=visits)
    result = feed2.post_session(s.name, cycle_hint="ZRW957|NA|20261115")
    assert result["result"] == "created" and not inserted2
    assert calls2[0]["cycle_hint"] == "ZRW957|NA|20261115"
    assert "UNALLOCATED" not in calls2[0]["diagnostic"] and "UNALLOCATED" not in s.diagnostics


def test_allocated_visit_is_not_posted_again():
    s = session(posted=1, visit="ti5g|g|m1|ZRW957", disposition="POSTED")
    feed, _w, _i, calls, _v = feed_with(s, visits={"ti5g|g|m1|ZRW957": {"cycle": "CYC-1"}})
    assert feed.post_session(s.name, cycle_hint="CYC-2")["result"] == "already_posted" and not calls


def test_post_pending_counts_unallocated_and_skipped():
    feed, *_ = feed_with(session())
    feed.frappe.get_all = lambda *a, **k: ["a", "b", "c"]
    results = {"a": {"result": "created"}, "b": {"result": "unallocated"},
               "c": {"result": "not_eligible", "reason": "SITE_NOT_IN_MASTER"}}
    feed.post_session = lambda name: results[name]
    assert feed._post_pending() == {"posted": 1, "failed": 0, "sites_created": 0, "unallocated": 1, "skipped": 1}


def test_record_visit_without_cycle_patch_reverses_the_temporary_cycle_branch():
    sys.modules["frappe"] = ModuleType("frappe")
    old = load("allow_visit_new_cycle_t", ROOT / "patches/v1_0/allow_visit_new_cycle.py")
    new = load("record_visit_without_cycle_t", ROOT / "patches/v1_0/record_visit_without_cycle.py")
    source = "head\n" + old.OLD + " tail"
    assert new.rewrite(old.rewrite(source)) == source
    assert new.rewrite(source) == source       # repeatable
    try:
        new.rewrite("unexpected writer")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown writer must stop the migration")


def _site_visits(sessions, cycles, post):
    """site_visits with a fake frappe/field_feed, enough to exercise allocate_unallocated."""
    fake = ModuleType("frappe")
    fake.whitelist = lambda: lambda fn: fn
    comments, errors = [], []

    def get_all(doctype, filters=None, **kwargs):
        if doctype == "SIG Field Session":
            cursor = (filters.get("name") or [None, ""])[1]
            return sorted((s for s in sessions if s.name > cursor), key=lambda s: s.name)[:kwargs.get("limit_page_length", 100)]
        return [c for c in cycles if c.site_key == filters["site_key"]][:kwargs.get("limit_page_length", 100)]

    fake.get_all = get_all
    cache_values = {}
    fake.cache = lambda: SimpleNamespace(get_value=lambda k: cache_values.get(k),
        set_value=lambda k, v: cache_values.__setitem__(k, v),
        delete_value=lambda k: cache_values.pop(k, None))
    fake.get_doc = lambda arg: SimpleNamespace(insert=lambda ignore_permissions=False: comments.append(arg))
    fake.log_error = lambda **kw: errors.append(kw)
    fake.get_traceback = lambda: "trace"
    fake.db = SimpleNamespace(rollback=lambda: None)
    from datetime import datetime, timedelta
    fake.utils = SimpleNamespace(get_datetime=lambda v: v if isinstance(v, datetime) else datetime.fromisoformat(str(v)),
                                 add_days=lambda d, n: d + timedelta(days=n))
    sys.modules["frappe"] = fake
    package = ModuleType("sig_warehouse")
    inner = ModuleType("sig_warehouse.sig_warehouse")
    feed = SimpleNamespace(STREAM_PROJECT={"ti5g": "5g", "ticpx": "Capex-9", "tiinc": "incident"}, post_session=post)
    family = load("project_family_t", ROOT / "project_family.py")
    sessions_mod = load("field_sessions_t", ROOT / "field_sessions.py")
    inner.field_feed, inner.field_sessions = feed, sessions_mod
    package.sig_warehouse = inner
    sys.modules.update({"sig_warehouse": package, "sig_warehouse.sig_warehouse": inner,
                        "sig_warehouse.sig_warehouse.field_feed": feed,
                        "sig_warehouse.sig_warehouse.field_sessions": sessions_mod,
                        "sig_warehouse.sig_warehouse.project_family": family})
    return load("site_visits_t", ROOT / "site_visits.py"), comments, errors


def _cycle(name, project="5g", site="ZRW957", created="2026-11-14 10:00:00"):
    from datetime import datetime
    return SimpleNamespace(name=name, site_key=site, project=project, erp_project=None,
                           creation=datetime.fromisoformat(created))


def _unallocated(start="2026-11-11 19:30:47", stream="ti5g"):
    from datetime import datetime
    return SimpleNamespace(name="S1", site_key="ZRW957", stream=stream, start_at=datetime.fromisoformat(start))


def test_one_compatible_open_cycle_allocates_the_visit_and_notes_it():
    posts = []
    sv, comments, _ = _site_visits([_unallocated()], [_cycle("C1")],
                                   lambda name, cycle_hint=None: posts.append((name, cycle_hint)) or {"result": "created"})
    assert sv.allocate_unallocated() == 1 and posts == [("S1", "C1")]
    assert "allocated automatically: C1" in comments[0]["content"]


def test_several_open_cycles_or_family_mismatch_stay_unallocated():
    posts = []
    post = lambda name, cycle_hint=None: posts.append(name) or {"result": "created"}
    sv, _c, _e = _site_visits([_unallocated()], [_cycle("C1"), _cycle("C2")], post)
    assert sv.allocate_unallocated() == 0
    sv, _c, _e = _site_visits([_unallocated()], [_cycle("C1", project="incident")], post)
    assert sv.allocate_unallocated() == 0 and not posts


def test_visit_long_before_the_new_cycle_is_a_different_episode():
    posts = []
    sv, _c, _e = _site_visits([_unallocated(start="2026-08-01 09:00:00")], [_cycle("C1")],
                              lambda name, cycle_hint=None: posts.append(name) or {"result": "created"})
    assert sv.allocate_unallocated() == 0 and not posts


def test_allocation_failure_is_logged_and_does_not_stop_the_rest():
    def post(name, cycle_hint=None):
        raise RuntimeError("writer down")
    sv, _c, errors = _site_visits([_unallocated()], [_cycle("C1")], post)
    assert sv.allocate_unallocated() == 0 and errors and errors[0]["title"] == "SIG visit allocation failed"


def test_ineligible_early_pages_do_not_starve_later_eligible_visit():
    from datetime import datetime
    sessions = [SimpleNamespace(name=f"S{i:03d}", site_key="OTHER", stream="ti5g",
                                start_at=datetime(2026, 11, 15)) for i in range(51)]
    sessions.append(SimpleNamespace(name="S999", site_key="ZRW957", stream="ti5g",
                                    start_at=datetime(2026, 11, 15)))
    posts = []
    sv, _comments, _errors = _site_visits(sessions, [_cycle("C1")],
        lambda name, cycle_hint=None: posts.append(name) or {"result": "created"})
    assert sv.allocate_unallocated() == 0
    assert sv.allocate_unallocated() == 1
    assert posts == ["S999"]


def test_scan_cursor_wraps_after_last_page_to_recheck_older_rows():
    old = _unallocated()
    sv, _comments, _errors = _site_visits([old], [_cycle("C1")], lambda *a, **k: {"result": "created"})
    assert sv.allocate_unallocated(limit=1) == 1
    assert sv.allocate_unallocated(limit=1) == 0
    assert sv.allocate_unallocated(limit=1) == 1


def test_backlog_alert_raises_and_clears():
    from datetime import datetime
    s = session()
    feed, *_ = feed_with(s)
    counts = {"review": 2, "unalloc": 0}
    feed.frappe.db.count = lambda doctype, filters: counts["review" if filters.get("disposition") == "REVIEW" else "unalloc"]
    raised, cleared = [], []
    feed._alert = lambda st, key, text: raised.append((key, text))
    feed._close_alert = lambda key: cleared.append(key)
    assert feed._backlog_alert({}, datetime(2026, 11, 15, 12, 0)) == (2, 0)
    assert raised[0][0] == "SIG-FEED-BACKLOG" and "2 field session" in raised[0][1] and not cleared
    counts["review"] = 0
    assert feed._backlog_alert({}, datetime(2026, 11, 15, 12, 0)) == (0, 0)
    assert cleared == ["SIG-FEED-BACKLOG"]


def test_late_end_updates_the_existing_visit_and_cycle_once():
    posted = session(posted=1, status="AUTO_CLOSED", visit="VISIT-1", corrected_by=None,
                     diagnostics="START_WITHOUT_END")
    feed, _writes, _inserted, event_calls, _visits = feed_with(posted)
    visit = Doc(name="VISIT-1", cycle="C-1", status="AUTO_CLOSED", site_key=posted.site_key,
                start_at=posted.start_at, diagnostic="START_WITHOUT_END")
    cycle = Doc(name="C-1", sessions_completed=0, sessions_auto_closed=1, on_site_hours=0,
                first_visit_at=None, last_visit_at=None, mir_at="2026-11-10", first_impl_visit_at=None)
    docs = {"SIG Field Session": posted, "SIG Field Visit": visit, "SIG Site Cycle": cycle}
    feed.frappe.get_doc = lambda doctype, name, for_update: docs[doctype]
    feed.frappe.get_all = lambda *args, **kwargs: [posted.start_at]
    feed.frappe.db.exists = lambda doctype, name: docs[doctype].name == name
    feed.frappe.db.set_value = lambda doctype, name, values: vars(docs[doctype]).update(values)
    late_end = dict(start_at=posted.start_at, end_at="2026-11-11 20:30:47", end_msg="M2",
                    reporter=posted.reporter, site_key=posted.site_key)
    assert feed._correct_estimated_visit(posted.name, late_end)
    assert not feed._correct_estimated_visit(posted.name, late_end)
    assert posted.status == visit.status == "COMPLETED"
    assert posted.end_msg == "M2" and visit.duration_hours == 1.0
    assert visit.diagnostic == posted.diagnostics == "LATE_END"
    assert cycle.sessions_auto_closed == 0 and cycle.sessions_completed == cycle.visit_days == cycle.impl_visits == 1
    assert cycle.first_impl_visit_at == posted.start_at
    assert not event_calls
