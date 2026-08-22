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


def test_invalid_ifsc_is_rejected():
    with pytest.raises(ValidationError):
        TaxProfileCreate(bank_accounts=[{"bank_name": "Bank", "account_number": "12345678", "ifsc_code": "INVALID"}])


def test_negative_normal_monetary_value_is_rejected():
    with pytest.raises(ValidationError):
        TaxProfileCreate(investments=[{"investment_type": "PPF", "amount": -1}])


def test_legitimate_business_loss_is_supported():
    profile = TaxProfileCreate(business_income=[{"business_name": "Studio", "nature_of_business": "Design", "gross_receipts": 10, "net_profit_or_loss": -2}])
    assert profile.business_income[0].net_profit_or_loss == -2


def test_profile_update_accepts_replacement_collections():
    update = TaxProfileUpdate(
        assessment_year="2026-27",
        other_income=[{"income_type": "interest", "description": "Savings", "amount": 500}],
    )
    assert update.other_income[0].description == "Savings"