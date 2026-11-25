"""PM notices: only Operations Setup Hub PMs, one per PM, bounded text, stable once-per-day key. No Frappe needed."""
import sys
import types

import pytest

sys.modules.setdefault("frappe", types.ModuleType("frappe"))
sys.modules["frappe"]._ = lambda value: value
sys.modules["frappe"].whitelist = lambda *a, **k: (lambda fn: fn)
hr = types.ModuleType("sig_warehouse.sig_hr.email_request")
hr._mask, hr._send_text = (lambda phone: "***"), (lambda *a: "")
sys.modules.setdefault("sig_warehouse.sig_hr.email_request", hr)

from sig_warehouse.sig_operations.pm_notice import MAX_TEXT, notice_key, validate_notices  # noqa: E402

PMS = {"HR-EMP-00009", "HR-EMP-00011", "HR-EMP-00034"}


def test_only_project_managers_receive_a_notice():
    clean = validate_notices([{"employee": "HR-EMP-00011", "text": " Hello "}], PMS)
    assert clean == [{"employee": "HR-EMP-00011", "text": "Hello"}]
    with pytest.raises(ValueError, match="not an enabled project manager"):
        validate_notices([{"employee": "HR-EMP-00035", "text": "Hello"}], PMS)


def test_one_notice_per_pm_and_text_is_bounded():
    with pytest.raises(ValueError, match="more than once"):
        validate_notices([{"employee": "HR-EMP-00009", "text": "a"}, {"employee": "HR-EMP-00009", "text": "b"}], PMS)
    with pytest.raises(ValueError, match="between 1 and"):
        validate_notices([{"employee": "HR-EMP-00009", "text": "x" * (MAX_TEXT + 1)}], PMS)
    with pytest.raises(ValueError, match="between 1 and"):
        validate_notices([{"employee": "HR-EMP-00009", "text": "  "}], PMS)
    with pytest.raises(ValueError, match="Send between"):
        validate_notices([], PMS)


def test_the_same_notice_has_a_stable_key_and_a_changed_text_does_not():
    assert notice_key("HR-EMP-00009", "Hello") == notice_key("HR-EMP-00009", "Hello")
    assert notice_key("HR-EMP-00009", "Hello") != notice_key("HR-EMP-00009", "Hello!")
    assert notice_key("HR-EMP-00009", "Hello") != notice_key("HR-EMP-00011", "Hello")
