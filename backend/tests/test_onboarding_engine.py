from decimal import Decimal

import pytest

from services.onboarding import amount, apply_candidate, initial_state, next_question, parse_answer, progress, start_state


def state_at(field):
    state = initial_state()
    while next_question(state).field != field:
        state["completed_fields"].append(next_question(state).field)
        state = start_state(state)
    return state


@pytest.mark.parametrize(
    ("text", "expected"),
    [("6 lakh", Decimal("600000")), ("6.5 lakhs", Decimal("650000")), ("₹6,00,000", Decimal("600000")), ("600000", Decimal("600000"))],
)
def test_amount_normalization(text, expected):
    assert amount(text) == expected


def test_contextual_salary_answer_requires_confirmation():
    result = parse_answer(state_at("salary_income"), "6 lakh")
    assert result["candidate_values"]["salary_income"][0]["gross_salary"] == Decimal("600000")
    assert result["requires_confirmation"] is True


def test_no_other_income_skips_branch():
    state = state_at("other_income")
    result = parse_answer(state, "No")
    assert result["skip_field"] == "other_income"


def test_yes_house_property_keeps_relevant_branch_decision():
    state = state_at("house_property")
    result = parse_answer(state, "Yes, rental income")
    assert result["complete_field"] == "house_property"


def test_whats_next_uses_missing_state():
    state = start_state(initial_state())
    assert state["current_field"] == "name"
    state["completed_fields"].extend(["name", "pan_number"])
    assert start_state(state)["current_field"] == "date_of_birth"


def test_profile_with_salary_does_not_ask_salary_again():
    state = start_state(initial_state({"salary_income": [{"gross_salary": 600000}]}))
    assert state["current_field"] != "salary_income"


def test_salary_correction_candidate_is_confirmation_only():
    state = state_at("salary_income")
    state["completed_fields"].append("salary_income")
    result = parse_answer(state, "6.5 lakh")
    assert result["requires_confirmation"] is True


def test_salary_correction_is_contextual():
    state = initial_state({"salary_income": [{"employer_name": "Acme", "gross_salary": 600000}]})
    state["answers"]["salary_income"] = [{"employer_name": "Acme", "gross_salary": 600000}]
    result = parse_answer(start_state(state), "Actually my salary is 6.5 lakh")
    assert result["candidate_values"]["salary_income"][0]["gross_salary"] == Decimal("650000")
    assert result["requires_confirmation"] is True


def test_progress_is_structured():
    state = start_state(initial_state())
    assert progress(state)["total"] > 0
    assert set(("current_field", "completed_fields", "missing_fields", "skipped_fields")) <= set(state)