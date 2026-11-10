from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.tax_profile import TaxProfileCreate, TaxProfileUpdate


def test_valid_profile_supports_multiple_entries():
    profile = TaxProfileCreate(
        pan_number="ABCDE1234F",
        pincode="560001",
        salary_income=[{"employer_name": "One", "gross_salary": 1000}, {"employer_name": "Two", "gross_salary": 2000}],
        house_properties=[{"property_type": "self_occupied", "city": "Bengaluru"}, {"property_type": "let_out", "city": "Pune"}],
        bank_accounts=[{"bank_name": "Bank", "account_number": "12345678", "ifsc_code": "HDFC0001234"}, {"bank_name": "Other", "account_number": "87654321", "ifsc_code": "SBIN0001234"}],
    )
    assert len(profile.salary_income) == 2
    assert len(profile.house_properties) == 2
    assert len(profile.bank_accounts) == 2


@pytest.mark.parametrize("field,value", [("pan_number", "BAD"), ("pincode", "01234"), ("pincode", "ABCDEF")])
def test_invalid_identity_formats_are_rejected(field, value):
    with pytest.raises(ValidationError):
        TaxProfileCreate(**{field: value})


@pytest.mark.parametrize("date_of_birth", ["not-a-date", "1990-02-30", "2027-01-01"])
def test_invalid_or_future_date_of_birth_is_rejected(date_of_birth):
    with pytest.raises(ValidationError):
        TaxProfileCreate(date_of_birth=date_of_birth)


def test_invalid_ifsc_is_rejected():
    with pytest.raises(ValidationError):
        TaxProfileCreate(bank_accounts=[{"bank_name": "Bank", "account_number": "12345678", "ifsc_code": "INVALID"}])


def test_negative_normal_monetary_value_is_rejected():
    with pytest.raises(ValidationError):
        TaxProfileCreate(investments=[{"investment_type": "PPF", "amount": -1}])


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "1E100"])
def test_non_finite_or_extreme_money_is_rejected(amount):
    with pytest.raises(ValidationError):
        TaxProfileCreate(salary_income=[{"employer_name": "Example", "gross_salary": amount}])


def test_decimal_money_precision_is_preserved():
    profile = TaxProfileCreate(
        salary_income=[{"employer_name": "Example", "gross_salary": "100000.25"}]
    )
    assert profile.salary_income[0].gross_salary == Decimal("100000.25")


def test_capital_gain_reporting_metadata_and_80g_evidence_are_preserved():
    profile = TaxProfileCreate(
        capital_gains=[{
            "asset_type": "listed_equity_share",
            "asset_identifier": "NSE:EXAMPLE",
            "acquisition_date": "2025-04-15",
            "sale_date": "2025-11-20",
            "holding_period": "short_term",
            "gain_type": "STCG",
            "sale_consideration": 150000,
            "acquisition_cost": 125000,
            "quantity": 10,
            "is_listed": True,
            "stt_paid_on_transfer": True,
        }],
        deductions=[{
            "section": "80G",
            "amount": 5000,
            "donation_category": "50_no_limit",
            "donation_mode": "non_cash",
            "donation_reference": "RECEIPT-2026-01",
            "donation_ifsc": "hdfc0001234",
        }],
    )
    assert profile.capital_gains[0].asset_identifier == "NSE:EXAMPLE"
    assert profile.capital_gains[0].gain_type == "STCG"
    assert profile.deductions[0].donation_ifsc == "HDFC0001234"


def test_invalid_donation_ifsc_is_rejected():
    with pytest.raises(ValidationError):
        TaxProfileCreate(deductions=[{
            "section": "80G",
            "amount": 1000,
            "donation_ifsc": "INVALID",
        }])


def test_legitimate_business_loss_is_supported():
    profile = TaxProfileCreate(business_income=[{"business_name": "Studio", "nature_of_business": "Design", "gross_receipts": 10, "net_profit_or_loss": -2}])
    assert profile.business_income[0].net_profit_or_loss == -2


def test_profile_update_accepts_replacement_collections():
    update = TaxProfileUpdate(
        assessment_year="2026-27",
        other_income=[{"income_type": "interest", "description": "Savings", "amount": 500}],
    )
    assert update.other_income[0].description == "Savings"