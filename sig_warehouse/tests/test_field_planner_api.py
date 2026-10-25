import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


class Row(dict):
    __getattr__ = dict.get


def load_api(roles, can_read=True, setup_json="{}", visits=()):
    calls = []
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda *args, **kwargs: (lambda function: function)
    frappe.session = SimpleNamespace(user="pm@example.com")
    frappe.PermissionError = PermissionError
    frappe.get_roles = lambda user: roles
    frappe.has_permission = lambda doctype, ptype: can_read

    def throw(message, exc=None):
        raise (exc or RuntimeError)(message)

    frappe.throw = throw
    frappe.utils = SimpleNamespace(nowdate=lambda: "2026-10-24", getdate=lambda v: v if isinstance(v, date) else date.fromisoformat(str(v)[:10]),
                                   add_days=lambda d, n: d + __import__("datetime").timedelta(days=n))
    frappe.DoesNotExistError = LookupError
    frappe.db = SimpleNamespace(get_single_value=lambda doctype, field: setup_json)

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
             "SIG Field Visit": [Row(v) for v in visits]}

    def get_list(doctype, **kwargs):
        calls.append(("get_list", doctype, tuple(kwargs.get("fields", ()))))
        if doctype == "SIG Site":
            return [Row(name="Z1", site_latitude=24.7, site_longitude=46.7)]
        return store.get(doctype, [])

    def get_all(doctype, **kwargs):
        calls.append(("get_all", doctype, tuple(kwargs.get("fields", ()))))
        return [Row(name="Z1", site_latitude=24.7, site_longitude=46.7)]

    frappe.get_list, frappe.get_all = get_list, get_all
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
        self.assertFalse([c for c in calls if c[0] == "get_all"])

    def test_setup_teams_set_the_team_count_names_and_starting_positions(self):
        import json
        setup = json.dumps({"teams": [
            {"id": "t1", "leader": "E1", "team": "Waqas", "phone": "1", "enabled": True},
            {"id": "t2", "leader": "E2", "team": "Asif", "phone": "2", "enabled": True},
            {"id": "t3", "leader": "E3", "team": "Off", "phone": "3", "enabled": False}]})
        visits = [dict(employee="E1", site="Z1", start_at="2026-10-23 08:00:00", end_at="2026-10-23 09:00:00", status="COMPLETED", cycle=None)]
        api, _ = load_api(["SIG Field Ops"], setup_json=setup, visits=visits)
        result = api.get_field_plan(week_start="2026-10-25")
        self.assertEqual(2, result["summary"]["teams"])
        states = {p["team"]: p["state"] for p in result["team_positions"]}
        self.assertEqual({"Waqas": "Current", "Asif": "Unknown"}, states)
        self.assertEqual({"Waqas", "Asif"}, {t["leader"] for t in result["teams"]} | {"Waqas", "Asif"})

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
        # the only write is the logged PM decision; it must be the sole insert and set_value in the module
        for forbidden in (".save(", "db.sql", "delete_doc", "ignore_permissions"):
            self.assertNotIn(forbidden, source)
        self.assertEqual(1, source.count(".insert("))
        self.assertEqual(1, source.count("set_value("))


if __name__ == "__main__":
    unittest.main()
