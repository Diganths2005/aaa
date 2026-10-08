import pytest

from itr.service import prepare_return, select_return
from schemas.tax_profile import TaxProfileCreate


def base_profile(**overrides):
    values = {
        "pan_number": "ABCDE1234F",
        "date_of_birth": "1990-01-01",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000}],
    }
    values.update(overrides)
    return TaxProfileCreate(**values)


def test_selector_recommends_itr2_for_multiple_capital_gain_transactions():
    profile = base_profile(capital_gains=[
        {
            "asset_type": "listed_equity_share",
            "acquisition_date": "2025-01-01",
            "sale_date": "2025-08-01",
            "sale_consideration": 200000,
            "acquisition_cost": 150000,
            "quantity": 10,
            "is_listed": True,
            "stt_paid_on_acquisition": True,
            "stt_paid_on_transfer": True,
        },
        {
            "asset_type": "immovable_property",
            "acquisition_date": "2020-01-01",
            "sale_date": "2025-08-01",
            "sale_consideration": 800000,
            "acquisition_cost": 500000,
        },
    ])
    selection = select_return(profile)
    assert selection.eligible is True
    assert selection.recommended_itr == "ITR-2"
    assert selection.preparation_supported is False

    with pytest.raises(ValueError, match="outside the supported preparation scope"):
        prepare_return(profile, "Test Taxpayer")


def test_selector_recommends_itr4_only_for_presumptive_income():
    profile = base_profile(
        salary_income=[],
        employment_type="self_employed",
        has_business_income=True,
        business_income=[{
            "business_name": "Consulting",
            "nature_of_business": "Professional services",
            "gross_receipts": 500000,
            "net_profit_or_loss": 300000,
            "presumptive_section": "44ADA",
        }],
    )
    selection = select_return(profile)
    assert selection.eligible is True
    assert selection.recommended_itr == "ITR-4"
    assert selection.preparation_supported is False
    with pytest.raises(ValueError, match="outside the supported preparation scope"):
        prepare_return(profile, "Test Taxpayer")


def test_selector_recommends_itr3_for_non_presumptive_business_income():
    profile = base_profile(
        salary_income=[],
        employment_type="self_employed",
        has_business_income=True,
        business_income=[{
            "business_name": "Retail",
            "nature_of_business": "Retail trade",
            "gross_receipts": 1000000,
            "net_profit_or_loss": 200000,
        }],
    )
    selection = select_return(profile)
    assert selection.eligible is True
    assert selection.recommended_itr == "ITR-3"
    assert selection.preparation_supported is True

    preparation = prepare_return(profile, "Test Taxpayer")
    assert preparation["itr_form"] == "ITR-3"
    assert preparation["income"]["business"] == 200000
    assert preparation["schedules"]["business_income"][0]["gross_receipts"] == "1000000"
    assert preparation["support_status"]["statutory_itr3_schedules"].startswith("Not supported")


def test_itr3_rejects_foreign_schedules():
    profile = base_profile(
        salary_income=[],
        employment_type="self_employed",
        has_business_income=True,
        business_income=[{
            "business_name": "Retail",
            "nature_of_business": "Retail trade",
            "gross_receipts": 1000000,
            "net_profit_or_loss": 200000,
        }],
        has_foreign_assets=True,
    )
    selection = select_return(profile)
    assert selection.recommended_itr == "ITR-3"
    assert selection.preparation_supported is False
    with pytest.raises(ValueError, match="outside the supported preparation scope"):
        prepare_return(profile, "Test Taxpayer")