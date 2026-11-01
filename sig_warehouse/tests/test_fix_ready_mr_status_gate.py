import importlib.util
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[1] / 'sig_warehouse/patches/v1_0/fix_ready_mr_status_gate.py'
spec = importlib.util.spec_from_file_location('ready_mr_patch', path)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


def test_rewrite_changes_only_the_two_gates_and_is_repeatable():
    source = 'filters={"custom_sent_to_wh": 0}\n    ' + patch.OLD_RV80 + '\n    ' + patch.OLD_ERP + '\n'
    expected = 'filters={"custom_sent_to_wh": 0}\n    ' + patch.NEW_RV80 + '\n    ' + patch.NEW_ERP + '\n'
    assert patch.rewrite(source) == expected
    assert patch.rewrite(expected) == expected


@pytest.mark.parametrize('source', [
    '',
    patch.OLD_RV80 + '\n',
    patch.OLD_RV80 + '\n' + patch.NEW_RV80 + '\n' + patch.OLD_ERP + '\n',
    patch.OLD_RV80 + '\n' + patch.OLD_ERP.replace('MR_SUBMITTED', 'UNKNOWN') + '\n',
])
def test_unexpected_or_duplicate_gates_fail_closed(source):
    with pytest.raises(ValueError):
        patch.rewrite(source)

