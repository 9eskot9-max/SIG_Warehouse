from sig_warehouse.sig_accounting.bank_router.business_routes import legacy_route_proposals, resolve_route


def test_multiple_employee_purposes_require_a_choice_without_a_tag():
    memories = [
        {"confirmed": True, "purpose": "XXPC", "route": "custody_topup", "account": "1322"},
        {"confirmed": True, "purpose": "XXSL", "route": "employee_salary", "account": "5122"},
    ]
    result = resolve_route({"direction": "DEBIT"}, {"employee": "EMP-1"}, memories)
    assert result["state"] == "ASK"
    assert result["route"] == ""


def test_employee_petty_cash_memory_does_not_assign_untagged_payments():
    memory = {"confirmed": True, "purpose": "XXPC", "route": "custody_topup", "account": "1322"}
    assert resolve_route({"direction": "DEBIT"}, {"employee": "EMP-1"}, [memory])["route"] == ""


def test_confirmed_tagged_memory_is_used_but_seed_is_not():
    movement = {"direction": "DEBIT", "category": "XXPC"}
    party = {"employee": "EMP-1", "custody_account": "1322"}
    memory = {"confirmed": True, "purpose": "XXPC", "route": "custody_topup", "account": "1322"}
    assert resolve_route(movement, party, [memory])["evidence"] == ["confirmed_memory"]
    memory["confirmed"] = False
    assert resolve_route(movement, party, [memory])["evidence"] == ["tx_category"]


def test_existing_document_and_paired_transfer_are_preserved():
    assert resolve_route({"erp_document": "JV-1", "paired_transfer": "other"})["state"] == "LINKED"
    assert resolve_route({"paired_transfer": "other"})["route"] == "own_transfer"


def test_employee_purpose_requires_employee_identity():
    assert resolve_route({"direction": "DEBIT", "category": "XXPC"})["route"] == ""


def test_unconfirmed_string_does_not_promote_a_suggestion_to_memory():
    memory = {"confirmed": "0", "route": "supplier", "purpose": "XXMR"}
    result = resolve_route({"direction": "DEBIT", "category": "XXMR"}, memories=[memory])
    assert result["evidence"] == ["tx_category"]


def test_unknown_direction_does_not_choose_payment_route():
    assert resolve_route({"category": "XXMR"})["route"] == ""


def test_memory_cannot_cross_transaction_direction():
    memory = {"confirmed": True, "route": "supplier", "direction": "DEBIT", "purpose": ""}
    result = resolve_route({"direction": "CREDIT"}, {"customer": "CUSTOMER-1"}, [memory])
    assert result["route"] == "client_receipt"
    assert result["evidence"] == ["party_type"]


def test_one_confirmed_purpose_can_be_suggested_for_untagged_payment():
    memory = {"confirmed": True, "route": "supplier", "direction": "DEBIT", "purpose": "SUPPLIER", "party_type": "Supplier", "party": "S1"}
    result = resolve_route({"direction": "DEBIT"}, memories=[memory])
    assert result["route"] == "supplier"
    assert result["party"] == "S1"
    assert result["state"] == "ASK"


def test_tagged_salary_reuses_generic_salary_without_mixing_work_purposes():
    salary = {"confirmed": True, "route": "employee_salary", "direction": "DEBIT", "purpose": "EMPLOYEE_SALARY", "account": "5122"}
    assert resolve_route({"direction": "DEBIT", "category": "XXSL"}, {"employee": "E1"}, [salary])["account"] == "5122"
    work = {"confirmed": True, "route": "person_work", "direction": "DEBIT", "purpose": "PERSON_WORK", "account": "5130"}
    assert resolve_route({"direction": "DEBIT", "category": "XXMT"}, memories=[work])["evidence"] == ["tx_category"]


def test_migration_does_not_promote_seeded_accounts_or_incomplete_decisions():
    cp = {"expense_account": "SEEDED-5130", "supplier": "SUP-1", "purpose_defaults_json": {
        "XXMR": {"treatment": "PAYMENT_ENTRY"}, "XXMT": "JOURNAL_ENTRY",
        "XXSC": {"treatment": "JOURNAL_ENTRY", "account": "CONTRACT"}}}
    result = legacy_route_proposals(cp)
    assert [(p["purpose"], p["route"], p["account"]) for p in result["proposals"]] == [
        ("XXMR", "supplier", ""), ("XXSC", "person_work", "CONTRACT")]
    assert result["held"] == ["XXMT"]
