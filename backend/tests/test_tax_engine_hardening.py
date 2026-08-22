from datetime import date
from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax, compare_regimes
from tax_engine.deductions import calculate_deductions
from tax_engine.income import calculate_house_property, calculate_income, taxpayer_age_category
from tax_engine.models import TaxEngineError
from tax_engine.rounding import round_rupee
from tax_engine.surcharge import calculate_surcharge, surcharge_rate


def profile(**kwargs):
    return TaxProfileCreate(assessment_year="2026-27", **kwargs)


def test_standard_deduction_salary_pension_and_zero_salary():
    old = calculate_income(profile(pension_income=[{"payer_name": "P", "amount": 60000}]), "old")
    new = calculate_income(profile(pension_income=[{"payer_name": "P", "amount": 60000}]), "new")
    combined = calculate_income(profile(salary_income=[{"employer_name": "E", "gross_salary": 100000}], pension_income=[{"payer_name": "P", "amount": 100000}]), "new")
    zero = calculate_income(profile(), "old")
    assert old.standard_deduction == Decimal("50000")
    assert new.standard_deduction == Decimal("60000")
    assert combined.standard_deduction == Decimal("75000")
    assert zero.standard_deduction == 0


def test_age_categories_are_explicit_and_residential_status_matters():
    assert taxpayer_age_category(profile(date_of_birth="1946-03-31")) == "super_senior"
    assert taxpayer_age_category(profile(date_of_birth="1966-03-31")) == "senior"
    assert taxpayer_age_category(profile(date_of_birth="1986-04-01")) == "individual"
    assert taxpayer_age_category(profile(date_of_birth="1940-01-01", residential_status="non_resident")) == "individual"


def test_house_property_types_loss_and_coownership():
    self_occupied = profile(house_properties=[{"property_type": "self_occupied", "city": "Pune", "home_loan_interest": 100000}])
    let_out = profile(house_properties=[{"property_type": "let_out", "city": "Pune", "annual_rent": 240000, "municipal_tax": 20000}])
    coowned = profile(house_properties=[{"property_type": "deemed_let_out", "city": "Pune", "annual_rent": 240000, "municipal_tax": 20000, "ownership_share": 50}])
    assert calculate_house_property(self_occupied) == Decimal("-100000")
    assert calculate_house_property(let_out) == Decimal("154000")
    assert calculate_house_property(coowned) == Decimal("77000")


def test_house_property_loss_setoff_is_separate_and_limited():
    data = profile(salary_income=[{"employer_name": "E", "gross_salary": 1000000}], house_properties=[{"property_type": "self_occupied", "city": "Pune", "home_loan_interest": 300000}])
    old = calculate_income(data, "old")
    new = calculate_income(data, "new")
    assert old.house_property == Decimal("-300000")
    assert old.house_property_loss_set_off == Decimal("200000")
    assert new.house_property_loss_set_off == 0
    assert calculate_tax(data, "old").gross_total_income == Decimal("900000")


def test_deduction_caps_and_regime_restrictions():
    data = profile(is_senior_citizen=True, salary_income=[{"employer_name": "E", "gross_salary": 1000000}], deductions=[
        {"section": "80C", "amount": 200000}, {"section": "80CCD(1B)", "amount": 70000}, {"section": "80D", "amount": 200000}, {"section": "80TTB", "amount": 70000}, {"section": "80TTA", "amount": 5000}
    ])
    assert calculate_deductions(data, "old", Decimal("1000000")) == Decimal("350000")
    assert calculate_deductions(data, "new", Decimal("1000000")) == 0


def test_surcharge_rates_caps_and_marginal_relief():
    assert surcharge_rate(Decimal("5000000"), "old") == 0
    assert surcharge_rate(Decimal("5000001"), "old") == Decimal("0.10")
    assert surcharge_rate(Decimal("50000000"), "old") == Decimal("0.25")
    assert surcharge_rate(Decimal("50000001"), "old") == Decimal("0.37")
    assert surcharge_rate(Decimal("50000001"), "new") == Decimal("0.25")
    surcharge = calculate_surcharge(Decimal("1000000"), Decimal("5000001"), "old", lambda value: Decimal("750000"))
    assert surcharge == Decimal("0")


def test_cess_and_rounding():
    assert round_rupee(Decimal("1.5")) == Decimal("2")
    from tax_engine.cess import calculate_cess
    assert calculate_cess(Decimal("100000"), Decimal("10000")) == Decimal("4400")


def test_exact_tax_payment_and_equal_regime_result():
    data = profile(salary_income=[{"employer_name": "E", "gross_salary": 1000000}])
    liability = calculate_tax(data, "old").total_tax_liability
    exact = profile(salary_income=[{"employer_name": "E", "gross_salary": 1000000}], taxes_paid=[{"tax_type": "tds", "amount": liability}])
    result = calculate_tax(exact, "old")
    assert result.balance_payable == 0 and result.refund == 0
    equal = compare_regimes(profile())
    assert equal.recommended_regime == "equal" and equal.estimated_saving == 0


def test_unsupported_errors_are_structured():
    with __import__("pytest").raises(TaxEngineError) as error:
        calculate_tax(profile(business_income=[{"business_name": "B", "nature_of_business": "N", "gross_receipts": 1, "net_profit_or_loss": 1}]), "new")
    assert error.value.code == "UNSUPPORTED_BUSINESS_INCOME"
