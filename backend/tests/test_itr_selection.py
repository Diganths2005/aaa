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
    assert selection.preparation_supported is True

    preparation = prepare_return(profile, "Test Taxpayer")
    assert preparation["itr_form"] == "ITR-2"
    assert preparation["schedules"]["capital_gains"]


def test_rahul_sharma_ay_2026_27_profile_keeps_transaction_provenance_and_itr2_support():
    profile = TaxProfileCreate(
        assessment_year="2026-27",
        financial_year="2025-26",
        pan_number="ABCDE1234F",
        date_of_birth="1988-04-10",
        residential_status="resident",
        employment_type="salaried",
        salary_income=[{
            "employer_name": "Example Technologies",
            "gross_salary": 1800000,
            "standard_deduction": 75000,
            "professional_tax": 2400,
            "tds": 150000,
        }],
        other_income=[{
            "income_type": "interest",
            "description": "Savings and deposit interest",
            "amount": 24000,
        }],
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
            "donation_ifsc": "HDFC0001234",
            "donation_eligible": True,
        }],
        taxes_paid=[{"tax_type": "tds", "amount": 150000, "reference": "FORM16"}],
    )

    selection = select_return(profile)
    assert selection.eligible is True
    assert selection.recommended_itr == "ITR-2"
    assert selection.preparation_supported is True
    preparation = prepare_return(profile, "Rahul Sharma")
    reported_gain = preparation["schedules"]["capital_gains"][0]
    assert reported_gain["asset_identifier"] == "NSE:EXAMPLE"
    assert reported_gain["source_reported_holding_period"] == "short_term"
    assert reported_gain["holding_period"] == "short_term"


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
    assert selection.preparation_supported is True
    preparation = prepare_return(profile, "Test Taxpayer")
    assert preparation["itr_form"] == "ITR-4"
    assert preparation["support_status"]["itr4_presumptive_schedule"].startswith("Supported")


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