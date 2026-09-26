from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from schemas.what_if import ScenarioChange, WhatIfScenarioRequest
from services.what_if import apply_changes, simulate


def profile(**kwargs):
    return TaxProfileCreate(assessment_year="2026-27", **kwargs)


def test_salary_increase_simulates_without_mutating_base_profile():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}])
    result = simulate(base, WhatIfScenarioRequest(changes=[ScenarioChange(field="salary_income", operation="replace", value=[{"employer_name": "Acme", "gross_salary": 1800000}])]))

    assert base.salary_income[0].gross_salary == Decimal("1500000")
    assert Decimal(result["what_if"]["profile"]["salary_income"][0]["gross_salary"]) == Decimal("1800000")
    assert result["comparison"]["income_difference"] == Decimal("300000")
    assert result["comparison"]["tax_difference"] > 0


def test_salary_increment_change_increases_gross_salary():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}])
    result = simulate(base, WhatIfScenarioRequest(changes=[ScenarioChange(field="salary_income", operation="increase_by", value=10000, index=0)]))

    assert Decimal(result["what_if"]["profile"]["salary_income"][0]["gross_salary"]) == Decimal("1510000")
    assert result["comparison"]["income_difference"] == Decimal("10000")


def test_additional_80c_changes_old_regime_and_explanation():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}])
    result = simulate(base, WhatIfScenarioRequest(changes=[ScenarioChange(field="deductions", operation="add", value={"section": "80C", "amount": 100000})], regime="old"))

    assert result["what_if"]["tax"]["total_deductions"] == Decimal("150000")
    assert result["comparison"]["tax_difference"] < 0
    assert result["explanation"]["deduction_changes"][0]["section"] == "80C"


def test_business_income_changes_itr_recommendation():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}])
    result = simulate(base, WhatIfScenarioRequest(changes=[ScenarioChange(field="business_income", operation="add", value={"business_name": "Consulting", "nature_of_business": "Professional", "gross_receipts": 1000000, "net_profit_or_loss": 600000})]))

    assert result["baseline"]["itr"]["recommended_itr"] == "ITR-1"
    assert result["what_if"]["itr"]["recommended_itr"] == "ITR-3"
    assert result["comparison"]["itr_changed"] is True
    assert result["explanation"]["itr_change"]["what_if"]["recommended_itr"] == "ITR-3"


def test_tax_payment_change_only_changes_refund_or_payable():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}], taxes_paid=[{"tax_type": "tds", "amount": 100000}])
    result = simulate(base, WhatIfScenarioRequest(changes=[ScenarioChange(field="taxes_paid", operation="replace", value=[{"tax_type": "tds", "amount": 150000}])], regime="new"))

    assert result["comparison"]["income_difference"] == 0
    assert result["comparison"]["tax_difference"] == 0
    assert result["comparison"]["tax_paid_difference"] == Decimal("50000")
    assert result["comparison"]["refund_difference"] == Decimal("50000")


def test_invalid_negative_scenario_is_rejected():
    base = profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1500000}])
    try:
        apply_changes(base, [ScenarioChange(field="salary_income", operation="increase_by", value=-1)])
    except ValueError:
        pass
    else:
        raise AssertionError("negative scenario value should be rejected")
