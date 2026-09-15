from sig_warehouse.sig_warehouse.stage5_bulk import build_bulk_plan, retry_result
from sig_warehouse.sig_warehouse.stage5_counts import (
    approve_count, build_reconciliation_items, validate_counter_payload,
    validate_state_transition,
)
from sig_warehouse.sig_warehouse.stage5_custody import (
    apply_custody_event, ensure_allocation_within_issued,
    position_key, validate_condition, validate_custody_identity,
)


def test_blind_payload_rejects_book_quantity():
    try:
        validate_counter_payload([{"item_code": "I", "warehouse": "W", "count_qty": 2, "book_qty": 3}], "counter")
    except ValueError as error:
        assert "book" in str(error)
    else:
        raise AssertionError("book quantity was accepted into a blind payload")


def test_count_approval_requires_different_user():
    rows = validate_counter_payload([{"item_code": "I", "warehouse": "W", "count_qty": 2}], "counter")
    rows[0]["variance"] = -1
    try:
        approve_count(state="REVIEW", counter_user="counter", approver_user="counter", rows=rows)
    except ValueError as error:
        assert "cannot approve" in str(error)
    else:
        raise AssertionError("self-approval was accepted")


def test_custody_events_cannot_overdraw_position():
    assert apply_custody_event(3, "RETURN", 2) == 1
    try:
        apply_custody_event(1, "USE", 2)
    except ValueError as error:
        assert "negative" in str(error)
    else:
        raise AssertionError("negative custody position was accepted")
    assert validate_condition("Serviceable") == "SERVICEABLE"


def test_count_lifecycle_and_reconciliation_payload():
    assert validate_state_transition("DRAFT", "ISSUED") == "ISSUED"
    rows = validate_counter_payload([{"item_code": "I", "warehouse": "W", "count_qty": 2}], "counter")
    rows[0]["variance"] = 0
    approved = approve_count(state="REVIEW", counter_user="counter", approver_user="supervisor", rows=rows)
    payload = build_reconciliation_items("COUNT-1", approved)
    assert payload[0]["batch_id"] == "COUNT-1"


def test_custody_identity_and_allocation_are_bounded():
    identity = validate_custody_identity(
        custodian="EMP-1", item_code="ITEM-1", source_line="SED-1", qty=2,
        condition="Damaged", lot_no="LOT-1", tracking="BATCH",
    )
    assert identity["condition"] == "DAMAGED"
    assert position_key("EMP-1", "ITEM-1", "Damaged", lot_no="LOT-1").endswith("|LOT-1|")
    assert ensure_allocation_within_issued(10, returned=2, custody=3, additional=4) == 1


def test_bulk_dispatch_has_stable_retry_semantics():
    lines = [{"mr": "MR-1", "mri": "MRI-1", "warehouse": "W", "uom": "Nos", "qty": 2}]
    plan = build_bulk_plan("BULK-1", lines)
    duplicate = retry_result("BULK-1", plan["signature"], plan["signature"], {"stock_entries": ["STE-1"]})
    conflict = retry_result("BULK-1", "different", plan["signature"], {})
    assert duplicate["result"] == "duplicate"
    assert conflict["result"] == "conflict"
