from itr.eligibility import build_itr_decision, evaluate_itr_readiness
from schemas.tax_profile import TaxProfileCreate


def make_profile(**overrides):
    values = {
        "assessment_year": "2026-27",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
    }
    values.update(overrides)
    return TaxProfileCreate(**values)


def test_salary_only_profile_recommends_itr1():
    profile = make_profile()
    decision = build_itr_decision(profile)
    assert decision["recommended_itr"] == "ITR-1"
    assert decision["forms"]["ITR-1"]["eligible"] is True
    assert decision["forms"]["ITR-1"]["recommended"] is True


def test_salary_plus_capital_gains_recommends_itr2():
    profile = make_profile(
        capital_gains=[{
            "asset_type": "listed_equity_share",
            "acquisition_date": "2024-01-01",
            "sale_date": "2025-08-01",
            "sale_consideration": 200000,
            "acquisition_cost": 150000,
            "quantity": 10,
            "is_listed": True,
            "stt_paid_on_acquisition": True,
            "stt_paid_on_transfer": True,
        }]
    )
    decision = build_itr_decision(profile)
    assert decision["recommended_itr"] == "ITR-2"
    assert decision["forms"]["ITR-2"]["eligible"] is True
    assert decision["forms"]["ITR-2"]["preparationSupported"] is False
    assert decision["preparation_supported"] is False
    assert evaluate_itr_readiness(decision)["ready"] is False
    assert decision["forms"]["ITR-1"]["eligible"] is False


def test_professional_income_selects_itr3():
    profile = make_profile(
        salary_income=[],
        employment_type="self_employed",
        has_business_income=True,
        business_income=[{
            "business_name": "Consulting",
            "nature_of_business": "Legal advisory",
            "gross_receipts": 1800000,
            "net_profit_or_loss": 400000,
        }],
    )
    decision = build_itr_decision(profile)
    assert decision["recommended_itr"] == "ITR-3"
    assert decision["forms"]["ITR-3"]["eligible"] is True
    assert decision["forms"]["ITR-3"]["preparationSupported"] is True
    assert decision["preparation_supported"] is True
    assert evaluate_itr_readiness(decision)["ready"] is True


def test_itr3_decision_rejects_business_loss_and_missing_statutory_schedules():
    profile = make_profile(
        salary_income=[],
        employment_type="self_employed",
        has_business_income=True,
        business_income=[{
            "business_name": "Retail",
            "nature_of_business": "Retail trade",
            "gross_receipts": 1000000,
            "net_profit_or_loss": -50000,
        }],
    )
    decision = build_itr_decision(profile)
    assert decision["recommended_itr"] is None
    assert decision["forms"]["ITR-3"]["preparationSupported"] is False
    assert "Business losses and their statutory schedules are not supported." in decision["forms"]["ITR-3"]["unsupportedConditions"]


def test_itr3_decision_rejects_company_director_without_disclosure_schedule():
    profile = make_profile(
        salary_income=[],
        employment_type="self_employed",
        is_director=True,
        has_business_income=True,
        business_income=[{
            "business_name": "Consulting",
            "nature_of_business": "Professional services",
            "gross_receipts": 500000,
            "net_profit_or_loss": 250000,
        }],
    )
    decision = build_itr_decision(profile)
    assert decision["recommended_itr"] is None
    assert decision["preparation_supported"] is False
    assert "Company-director disclosure schedules are not prepared by this workflow." in decision["forms"]["ITR-3"]["unsupportedConditions"]


def test_unknown_income_does_not_silently_choose_itr1():
    profile = make_profile(salary_income=[], employment_type="salaried")
    decision = build_itr_decision(profile)
    assert decision["forms"]["ITR-1"]["status"] in {"needs_information", "not_eligible"}
    assert decision["status"] in {"needs_information", "not_eligible"}
    readiness = evaluate_itr_readiness(decision)
    assert readiness["ready"] is False
    assert readiness["missing_fields"]


def test_foreign_schedules_are_not_marked_eligible_for_itr2():
    decision = build_itr_decision(make_profile(
        salary_income=[],
        foreign_income_assets=[{"country": "Example", "item_type": "bank_account", "description": "Foreign account", "value": 1000}],
    ))
    assert decision["forms"]["ITR-2"]["eligible"] is False
    assert decision["forms"]["ITR-2"]["unsupportedConditions"]


def test_itr3_decision_rejects_wrong_year_and_speculative_income():
    profile = make_profile(
        assessment_year="2025-26",
        has_business_income=True,
        business_income=[{"business_name": "Consulting", "nature_of_business": "Professional", "gross_receipts": 100000, "net_profit_or_loss": 50000}],
        has_speculative_income=True,
    )
    decision = build_itr_decision(profile)
    assert decision["forms"]["ITR-3"]["eligible"] is False
    assert decision["forms"]["ITR-3"]["unsupportedConditions"]
