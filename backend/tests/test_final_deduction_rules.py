from decimal import Decimal

import pytest

from pydantic import ValidationError
from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax
from tax_engine.deductions import calculate_deductions
from tax_engine.income import calculate_income
from tax_engine.models import TaxEngineError


def profile(**kwargs):
    return TaxProfileCreate(assessment_year="2026-27", **kwargs)


def deduction(section, **kwargs):
    return {"section": section, "amount": kwargs.pop("amount", 1), **kwargs}


def test_80dd_fixed_amount_requires_dependent_and_expense():
    normal = deduction("80DD", disability_percentage=40, is_dependent=True, medical_expenditure=50000)
    severe = deduction("80DD", disability_percentage=80, is_dependent=True, medical_expenditure=50000)
    assert calculate_deductions(profile(deductions=[normal]), "old") == Decimal("75000")
    assert calculate_deductions(profile(deductions=[severe]), "old") == Decimal("125000")
    with pytest.raises(TaxEngineError) as error:
        calculate_deductions(profile(deductions=[deduction("80DD", disability_percentage=40, is_dependent=False, medical_expenditure=50000)]), "old")
    assert error.value.code == "INELIGIBLE_DEDUCTION"


def test_80u_is_taxpayer_fixed_amount_and_not_expense_based():
    assert calculate_deductions(profile(deductions=[deduction("80U", disability_percentage=80, is_dependent=False)]), "old") == Decimal("125000")
    with pytest.raises(ValidationError):
        calculate_deductions(profile(deductions=[deduction("80U", disability_percentage=20, is_dependent=False)]), "old")
    with pytest.raises(TaxEngineError) as error:
        calculate_deductions(profile(deductions=[deduction("80U", disability_percentage=40, is_dependent=True)]), "old")
    assert error.value.code == "INELIGIBLE_DEDUCTION"


def test_80ddb_reduces_reimbursement_and_uses_age_limit():
    item = deduction("80DDB", amount=100000, specified_disease=True, is_dependent=False, medical_expenditure=120000, reimbursement_amount=30000)
    assert calculate_deductions(profile(deductions=[item]), "old", age_category="individual") == Decimal("40000")
    assert calculate_deductions(profile(deductions=[item]), "old", age_category="senior") == Decimal("90000")
    with pytest.raises(TaxEngineError):
        calculate_deductions(profile(deductions=[deduction("80DDB", specified_disease=False, is_dependent=False, medical_expenditure=1000)]), "old")


def test_80g_uses_engine_income_for_qualifying_limit():
    income = profile(salary_income=[{"employer_name": "E", "gross_salary": 1000000}])
    adjusted = calculate_income(income, "old").gross_total_income - Decimal("50000")
    item = deduction("80G", amount=200000, donation_category="100_qualifying_limit")
    assert calculate_deductions(profile(salary_income=income.salary_income, deductions=[item]), "old", adjusted_total_income=adjusted) == adjusted * Decimal("0.10")
    assert calculate_deductions(profile(deductions=[deduction("80G", amount=1000, donation_category="100_no_limit")]), "old") == Decimal("1000")
    assert calculate_deductions(profile(deductions=[deduction("80G", amount=1000, donation_category="50_no_limit")]), "old") == Decimal("500")


def test_80gg_uses_least_of_three_and_rejects_hra_or_property():
    item = deduction("80GG", annual_rent=180000, has_hra=False, owns_residential_property=False)
    assert calculate_deductions(profile(deductions=[item]), "old", adjusted_total_income=Decimal("600000")) == Decimal("60000")
    with pytest.raises(TaxEngineError):
        calculate_deductions(profile(deductions=[deduction("80GG", annual_rent=180000, has_hra=True, owns_residential_property=False)]), "old", adjusted_total_income=Decimal("600000"))


def test_80ee_and_80eea_boundary_conditions():
    ee = deduction("80EE", amount=70000, loan_sanction_date="2017-03-31", first_home_owner=True, loan_amount=3500000, property_stamp_duty_value=5000000)
    eea = deduction("80EEA", amount=200000, loan_sanction_date="2022-03-31", first_home_owner=True, loan_amount=4000000, property_stamp_duty_value=4500000)
    assert calculate_deductions(profile(deductions=[ee]), "old") == Decimal("50000")
    assert calculate_deductions(profile(deductions=[eea]), "old") == Decimal("150000")
    with pytest.raises(TaxEngineError):
        calculate_deductions(profile(deductions=[{**ee, "loan_amount": 3500001}]), "old")
    with pytest.raises(TaxEngineError):
        calculate_deductions(profile(deductions=[{**eea, "property_stamp_duty_value": 4500001}]), "old")


def test_property_loss_is_not_deducted_twice():
    data = profile(salary_income=[{"employer_name": "E", "gross_salary": 1000000}], house_properties=[{"property_type": "self_occupied", "city": "Pune", "home_loan_interest": 300000}])
    result = calculate_tax(data, "old")
    assert result.house_property_income == Decimal("-300000")
    assert result.house_property_loss_set_off == Decimal("200000")
    assert result.house_property_loss_carried_forward == Decimal("100000")
    assert result.gross_total_income == Decimal("900000")
    assert result.taxable_income == Decimal("850000")
