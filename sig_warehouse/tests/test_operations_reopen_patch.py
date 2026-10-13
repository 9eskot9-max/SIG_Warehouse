"""The migration must change only the known evidence cycle-routing block."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _rewrite():
    sys.modules["frappe"] = ModuleType("frappe")
    source = (Path(__file__).resolve().parents[1] / "sig_warehouse" / "patches" / "v1_0"
              / "start_new_cycle_after_close.py")
    spec = importlib.util.spec_from_file_location("start_new_cycle_after_close_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.rewrite


OLD_SELECTION = """    FIELD_DELIVERY = ('FIELD_VISIT_COMPLETED', 'TCN_GENERATED', 'MIR_CONFIRMED')

    cyc = None
    resolution = ''
    if wo:
        rows = frappe.get_all('SIG Site Cycle', filters={'wo': wo, 'site_key': sk},
                              fields=['name', 'terminal'], order_by='modified desc', limit_page_length=1)
        if rows:
            if (not rows[0].terminal) or (event_code not in FIELD_DELIVERY):
                cyc = rows[0].name
        if cyc is None:
            pass
    else:
        if po:
            rows = frappe.get_all('SIG Site Cycle', filters={'po': po, 'site_key': sk},
                                  fields=['name', 'terminal'], order_by='modified desc', limit_page_length=1)
            if rows:
                if (not rows[0].terminal) or (event_code not in FIELD_DELIVERY):
                    cyc = rows[0].name
        if cyc is None:
            pass
"""


def test_new_event_after_closure_uses_new_cycle_route():
    result = _rewrite()(OLD_SELECTION)
    assert result.count("closed_exact_scope = bool(frappe.db.exists") == 2
    assert result.count("if cyc is None and not closed_exact_scope:") == 2
    assert result.count("'terminal': 0") == 2
    assert "event_code not in FIELD_DELIVERY" not in result
    compile("def handle_evidence():\n" + result, "route", "exec")


def test_unknown_live_script_shape_fails_closed():
    try:
        _rewrite()(OLD_SELECTION.replace("if wo:", "if work_order:"))
    except ValueError as error:
        assert "scope selection changed" in str(error)
    else:
        raise AssertionError("Unknown evidence intake shape was silently modified")
