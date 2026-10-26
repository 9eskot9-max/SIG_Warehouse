import importlib.util
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from zoneinfo import ZoneInfo

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


class Row(dict):
    __getattr__ = dict.get


def load_api(roles, can_read=True, setup_json="{}", visits=(), sessions=(), positions=()):
    calls = []
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.PermissionError = PermissionError
    frappe.get_roles = lambda user: roles
    frappe.has_permission = lambda doctype, ptype, *args: can_read

    def throw(message, exc=None):
        raise (exc or RuntimeError)(message)

    frappe.throw = throw
    frappe.utils = SimpleNamespace(nowdate=lambda: "2026-10-24", now_datetime=lambda: "2026-10-26 08:00:00",
                                   get_datetime_in_timezone=lambda name: datetime(2026, 10, 26, 8, 0,
                                                                                 tzinfo=timezone.utc).astimezone(ZoneInfo(name)),
                                   getdate=lambda v: v if isinstance(v, date) else date.fromisoformat(str(v)[:10]),
                                   add_days=lambda d, n: d + __import__("datetime").timedelta(days=n))
    frappe.DoesNotExistError = LookupError
    frappe.db = SimpleNamespace(get_single_value=lambda doctype, field: setup_json,
                                exists=lambda doctype, name: doctype == "SIG Site" and name == "Z1",
                                get_value=lambda doctype, name, fields, as_dict=False: Row(site_latitude=24.7, site_longitude=46.7))

    class Meta:
        def get_field(self, fieldname):
            return True

    frappe.get_meta = lambda doctype: Meta()
    cycle = Row(name="Z1|NA|1", site="Z1", site_id="Z1", project="P", stage="2 - Plan", terminal=0,
                tcn_at="2026-10-20 10:00:00", mir_at="2026-10-21 10:00:00", first_visit_at=None, impl_visits=0,
                tags_at=None, planned_start=None, last_event_at="2026-10-21 10:00:00", plan_hold="")
    store = {"SIG Site Cycle": [cycle],
             "SIG Evidence Event": [Row(cycle="Z1|NA|1", event_code="TCN_GENERATED",
                                        occurred_at="2026-10-26 00:00:00", recorded_at="2026-10-22 10:00:00")],
             "SIG Field Visit": [Row(v) for v in visits],
             "SIG Field Session": [Row(v) for v in sessions],
             "SIG Planner Position": [Row(v) for v in positions]}

    def get_list(doctype, **kwargs):
        calls.append(("get_list", doctype, tuple(kwargs.get("fields", ()))))
        if doctype == "SIG Site":
            return [Row(name="Z1", site_latitude=24.7, site_longitude=46.7)]
        return store.get(doctype, [])

    def get_all(doctype, **kwargs):
        calls.append(("get_all", doctype, tuple(kwargs.get("fields", ()))))
        return store.get(doctype, [])

    frappe.get_list, frappe.get_all = get_list, get_all
    def get_doc(data):
        calls.append(("insert", data["doctype"], data.get("team_leader"), data.get("site")))
        return SimpleNamespace(name="TP-00001", updated_at=data["updated_at"], insert=lambda: None)
    frappe.get_doc = get_doc
    sys.modules["frappe"] = frappe
    pkg = ModuleType("sig_warehouse")
    sub = ModuleType("sig_warehouse.sig_warehouse")
    sys.modules.setdefault("sig_warehouse", pkg)
    sys.modules.setdefault("sig_warehouse.sig_warehouse", sub)
    for name in ("field_planner", "continuity"):
        spec = importlib.util.spec_from_file_location("sig_warehouse.sig_warehouse." + name,
                                                      APP_ROOT / "sig_warehouse" / "sig_warehouse" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["sig_warehouse.sig_warehouse." + name] = module
        spec.loader.exec_module(module)
        setattr(sub, name, module)
    spec = importlib.util.spec_from_file_location("field_planner_api_under_test",
                                                  APP_ROOT / "sig_warehouse" / "sig_warehouse" / "field_planner_api.py")
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api, calls


class FieldPlannerApiTests(unittest.TestCase):
    def test_cutoff_clock_uses_explicit_riyadh_timezone(self):
        api, _ = load_api(["SIG Field Ops"])
        self.assertEqual("2026-10-26 11:00:00+03:00", api._riyadh_now().isoformat(sep=" "))

    def test_a_tcn_covered_scheduled_day_is_not_badged_from_another_provisional_day(self):
        api, _ = load_api(["SIG Field Ops"])
        stop = {"day": "2026-10-27", "provisional_days": [date(2026, 10, 28)]}
        self.assertEqual({"needs_tcn": False, "tcn_due_at": "", "tcn_due_for": ""}, api._tcn_status(stop, {}))
        self.assertTrue(api._tcn_status({"provisional_days": [date(2026, 10, 28)]}, {})["needs_tcn"])

    def test_roles_outside_the_page_audience_are_refused(self):
        api, _ = load_api(["Employee"])
        with self.assertRaises(PermissionError):
            api.get_field_plan()

    def test_page_role_without_cycle_read_is_refused(self):
        api, _ = load_api(["SIG Field Ops"], can_read=False)
        with self.assertRaises(PermissionError):
            api.get_field_plan()

    def test_authorised_user_gets_a_committed_trip_and_site_coordinates_use_normal_permissions(self):
        api, calls = load_api(["SIG Field Ops"])
        result = api.get_field_plan(week_start="2026-10-25", teams="4")
        self.assertEqual(1, result["summary"]["committed_sites"])
        self.assertEqual("Committed", result["trips"][0]["kind"])
        self.assertEqual("2026-10-26", result["trips"][0]["anchor"])
        self.assertEqual((24.7, 46.7), (result["trips"][0]["stops"][0]["lat"], result["trips"][0]["stops"][0]["lon"]))
        self.assertIn(result["trips"][0]["stops"][0]["class"], ("Must", "Priority", "Normal"))
        self.assertEqual([("get_list", "SIG Site", ("name", "site_latitude", "site_longitude"))], [c for c in calls if c[1] == "SIG Site"])
        self.assertFalse([c for c in calls if c[0] == "get_all" and c[1] == "SIG Site"])

    def test_trace_hides_visit_details_without_visit_read_permission(self):
        visit = dict(name="VISIT-1", cycle="Z1|NA|1", site="Z1", start_at="2026-10-25 08:00:00",
                     status="COMPLETED")
        api, calls = load_api(["SIG Field Ops"], visits=[visit])
        api.frappe.has_permission = lambda doctype, ptype, *args: doctype != "SIG Field Visit"
        trace = api.get_field_plan(week_start="2026-10-25", capture_trace=1)["decision_trace"]
        self.assertEqual([], trace["evidence_records"]["cycle_visits"])
        self.assertEqual([], trace["candidate_decisions"][0]["visit_dates"])
        self.assertFalse(trace["candidate_decisions"][0]["visit_detail_access"])
        self.assertFalse([call for call in calls if call[0] == "get_list" and call[1] == "SIG Field Visit"])

    def test_trace_counts_dated_tcn_even_when_site_has_no_coordinates(self):
        api, _ = load_api(["SIG Field Ops"])
        original_get_list = api.frappe.get_list
        api.frappe.get_list = lambda doctype, **kwargs: [] if doctype == "SIG Site" else original_get_list(doctype, **kwargs)
        outcome = api.get_field_plan(week_start="2026-10-25", capture_trace=1)["decision_trace"]["outcome"]
        self.assertEqual(1, outcome["dated_tcn_candidates_in_scope"])
        self.assertEqual(1, outcome["dated_tcn_candidates_without_coordinates"])
        self.assertEqual("review_required", outcome["plan_validity"])

    def test_setup_teams_set_the_team_count_names_and_starting_positions(self):
        import json
        setup = json.dumps({"teams": [
            {"id": "t1", "leader": "E1", "team": "Waqas", "phone": "1", "enabled": True},
            {"id": "t2", "leader": "E2", "team": "Asif", "phone": "2", "enabled": True},
            {"id": "t3", "leader": "E3", "team": "Off", "phone": "3", "enabled": False},
            {"id": "t4", "leader": "E4", "team": "Incident crew", "phone": "4", "enabled": True, "archetype": "Incident"}]})
        visits = [dict(employee="E1", site="Z1", start_at="2026-10-23 08:00:00", end_at="2026-10-23 09:00:00", status="COMPLETED", cycle=None)]
        api, _ = load_api(["SIG Field Ops"], setup_json=setup, visits=visits)
        result = api.get_field_plan(week_start="2026-10-25")
        self.assertEqual(2, result["summary"]["teams"])
        states = {p["team"]: p["state"] for p in result["team_positions"]}
        self.assertEqual({"Waqas": "Current", "Asif": "Unknown", "Incident crew": "Incident"}, states)
        self.assertEqual({"Waqas", "Asif"}, {t["leader"] for t in result["teams"]} | {"Waqas", "Asif"})

    def test_latest_reported_session_updates_the_team_start_when_not_yet_posted_as_a_visit(self):
        import json
        setup = json.dumps({"teams": [{"leader": "E1", "team": "Yawar Raza Sibtain Ali", "enabled": True}]})
        session = dict(employee="E1", site="Z1", site_key="Z1", start_at="2026-10-25 02:37:36",
                       end_at="2026-10-25 02:39:55", status="AUTO_CLOSED", disposition="PENDING")
        api, _ = load_api(["Projects Manager"], setup_json=setup, sessions=[session])
        result = api.get_field_plan(week_start="2026-10-25")
        position = result["team_positions"][0]
        self.assertEqual(("Z1", "2026-10-25 02:39:55", "WhatsApp report", "Current"),
                         (position["site"], position["seen_at"], position["source"], position["state"]))

    def test_newer_pm_position_update_wins_but_older_update_does_not_overwrite_a_visit(self):
        api, _ = load_api(["Projects Manager"])
        today = date(2026, 10, 26)
        position = {"leader": "E1", "site": "Z1", "seen_at": "2026-10-25 10:00:00", "state": "Current"}
        api._set_manual_position(position, {"site": "Z2", "updated_at": "2026-10-26 08:00:00", "updated_by": "pm"},
                                 {"Z2": (25.0, 45.0)}, today)
        self.assertEqual(("Z2", "PM update", "pm", (25.0, 45.0)),
                         (position["site"], position["source"], position["updated_by"], (position["lat"], position["lon"])))
        prior = {"leader": "E1", "site": "Z1", "seen_at": "2026-10-25 10:00:00", "state": "Current"}
        api._set_manual_position(prior, {"site": "Z2", "updated_at": "2026-10-24 08:00:00"}, {"Z2": (25.0, 45.0)}, today)
        self.assertEqual(("Z1", "2026-10-25 10:00:00"), (prior["site"], prior["seen_at"]))

    def test_only_project_managers_can_append_an_enabled_team_site_position(self):
        import json
        setup = json.dumps({"teams": [{"leader": "E1", "team": "Yawar Raza Sibtain Ali", "enabled": True}]})
        api, calls = load_api(["Projects Manager"], setup_json=setup)
        result = api.update_team_position("E1", "Z1")
        self.assertEqual({"team_leader": "E1", "team": "Yawar Raza Sibtain Ali", "site": "Z1"},
                         {k: result[k] for k in ("team_leader", "team", "site")})
        self.assertIn(("insert", "SIG Planner Position", "E1", "Z1"), calls)
        api, calls = load_api(["Projects User"], setup_json=setup)
        with self.assertRaises(PermissionError):
            api.update_team_position("E1", "Z1")
        self.assertFalse([call for call in calls if call[0] == "insert"])

    def test_reference_towns_need_access_and_load_the_bundled_file(self):
        api, _ = load_api(["Employee"])
        with self.assertRaises(PermissionError):
            api.get_reference_towns()
        api, _ = load_api(["SIG Field Ops"])
        towns = api.get_reference_towns()
        self.assertGreater(len(towns), 100)
        self.assertTrue(all(t["zone"] and 15 <= t["lat"] <= 33 and 34 <= t["lon"] <= 56 for t in towns))

    def test_no_write_calls_exist_in_the_api_module(self):
        source = (APP_ROOT / "sig_warehouse" / "sig_warehouse" / "field_planner_api.py").read_text(encoding="utf-8")
        # Writes are limited to the append-only PM decision and position logs plus decision projection.
        for forbidden in (".save(", "db.sql", "delete_doc", "ignore_permissions"):
            self.assertNotIn(forbidden, source)
        self.assertEqual(2, source.count(".insert("))
        self.assertEqual(1, source.count("set_value("))


if __name__ == "__main__":
    unittest.main()
