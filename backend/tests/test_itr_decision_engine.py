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


def test_unknown_income_does_not_silently_choose_itr1():
    profile = make_profile(salary_income=[], employment_type="salaried")
    decision = build_itr_decision(profile)
    assert decision["forms"]["ITR-1"]["status"] in {"needs_information", "not_eligible"}
    assert decision["status"] in {"needs_information", "not_eligible"}
    readiness = evaluate_itr_readiness(decision)
    assert readiness["ready"] is False
    assert readiness["missing_fields"]
