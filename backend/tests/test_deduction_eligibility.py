from decimal import Decimal

import pytest

from schemas.tax_profile import TaxProfileCreate
from tax_engine.deductions import calculate_deductions
from tax_engine.income import taxpayer_age_category
from tax_engine.models import TaxEngineError


def make(**kwargs):
    return TaxProfileCreate(assessment_year="2026-27", **kwargs)


def test_80d_components_and_caps():
    item = {"section": "80D", "amount": 1, "self_health_insurance": 40000, "family_health_insurance": 30000, "parents_health_insurance": 70000, "parents_senior": True}
    assert calculate_deductions(make(deductions=[item]), "old", age_category="individual") == Decimal("75000")
    assert calculate_deductions(make(deductions=[item]), "old", age_category="senior") == Decimal("100000")


def test_80ccd2_uses_basic_and_da_and_regime_rate():
    item = {"section": "80CCD(2)", "amount": 1, "employer_contribution": 200000, "basic_salary": 1000000, "dearness_allowance_for_retirement": 100000}
    assert calculate_deductions(make(deductions=[item]), "old") == Decimal("110000")
    assert calculate_deductions(make(deductions=[item]), "new") == Decimal("154000")


def test_interest_deduction_age_rules():
    assert calculate_deductions(make(deductions=[{"section": "80TTA", "amount": 20000}]), "old", age_category="individual") == Decimal("10000")
    assert calculate_deductions(make(deductions=[{"section": "80TTB", "amount": 70000}]), "old", age_category="senior") == Decimal("50000")
    with pytest.raises(TaxEngineError):
        calculate_deductions(make(deductions=[{"section": "80TTB", "amount": 1}]), "old", age_category="individual")


@pytest.mark.parametrize("section", ["80G", "80GG", "80E", "80DD", "80DDB", "80U", "80EE", "80EEA"])
def test_complex_deductions_require_metadata(section):
    with pytest.raises(TaxEngineError) as error:
        calculate_deductions(make(deductions=[{"section": section, "amount": 1000}]), "old", age_category="individual")
    assert error.value.code in {"INSUFFICIENT_DEDUCTION_DATA", "INELIGIBLE_DEDUCTION"}


def test_age_boundary_dates():
    assert taxpayer_age_category(make(date_of_birth="1967-04-01")) == "individual"
    assert taxpayer_age_category(make(date_of_birth="1966-03-31")) == "senior"
    assert taxpayer_age_category(make(date_of_birth="1947-04-01")) == "senior"
    assert taxpayer_age_category(make(date_of_birth="1946-03-31")) == "super_senior"
