from decimal import Decimal

import pytest

from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax, compare_regimes
from tax_engine.models import TaxEngineError


def profile(**kwargs):
    return TaxProfileCreate(assessment_year="2026-27", **kwargs)


def test_zero_income():
    result = calculate_tax(profile(), "new")
    assert result.total_tax_liability == 0
    assert result.taxable_income == 0


def test_salary_only_applies_standard_deduction():
    result = calculate_tax(profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1000000}]), "old")
    assert result.total_deductions == Decimal("50000")
    assert result.taxable_income == Decimal("950000")
    assert result.total_tax_liability == Decimal("106600")


def test_multiple_income_sources_and_house_property():
    result = calculate_tax(profile(
        salary_income=[{"employer_name": "A", "gross_salary": 800000}, {"employer_name": "B", "gross_salary": 200000}],
        pension_income=[{"payer_name": "Pension office", "amount": 100000}],
        house_properties=[{"property_type": "let_out", "city": "Pune", "annual_rent": 240000, "municipal_tax": 20000}],
        other_income=[{"income_type": "interest", "description": "Savings", "amount": 50000}],
    ), "old")
    assert result.gross_total_income == Decimal("1254000")
    assert result.total_tax_liability == Decimal("196248")


def test_new_regime_rebate_at_twelve_lakh_taxable_income():
    result = calculate_tax(profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1275000}]), "new")
    assert result.taxable_income == Decimal("1200000")
    assert result.rebate == Decimal("60000")
    assert result.total_tax_liability == Decimal("0")


def test_new_regime_marginal_relief_above_rebate_threshold():
    result = calculate_tax(profile(salary_income=[{"employer_name": "Acme", "gross_salary": 1280000}]), "new")
    assert result.taxable_income == Decimal("1205000")
    assert result.total_tax_liability == Decimal("5200")


def test_old_regime_senior_citizen_slab():
    result = calculate_tax(profile(is_senior_citizen=True, salary_income=[{"employer_name": "Acme", "gross_salary": 600000}]), "old")
    assert result.taxable_income == Decimal("550000")
    assert result.tax_before_rebate == Decimal("20000")
    assert result.total_tax_liability == Decimal("20800")


def test_tds_greater_than_liability_is_refund():
    result = calculate_tax(profile(
        salary_income=[{"employer_name": "Acme", "gross_salary": 1000000}],
        taxes_paid=[{"tax_type": "tds", "amount": 200000}],
    ), "old")
    assert result.refund == Decimal("93400")
    assert result.balance_payable == 0


def test_tax_greater_than_tds_is_payable():
    result = calculate_tax(profile(
        salary_income=[{"employer_name": "Acme", "gross_salary": 1000000}],
        taxes_paid=[{"tax_type": "tds", "amount": 1000}],
    ), "old")
    assert result.balance_payable == Decimal("105600")


def test_compare_regimes_is_deterministic():
    comparison = compare_regimes(profile(salary_income=[{"employer_name": "Acme", "gross_salary": 2000000}], deductions=[{"section": "80C", "amount": 150000}]))
    assert comparison.recommended_regime in {"old", "new"}
    assert comparison.estimated_saving >= 0


def test_itr1_subset_rejects_unimplemented_income_types():
    with pytest.raises(TaxEngineError):
        calculate_tax(profile(capital_gains=[{"asset_type": "equity", "holding_period": "short_term", "sale_value": 10, "cost_of_acquisition": 5, "gain_or_loss": 5}]), "new")
