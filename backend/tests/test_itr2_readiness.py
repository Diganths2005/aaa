from services.itr2_readiness import build_itr2_readiness


def base_profile():
    return {
        "assessment_year": "2026-27",
        "date_of_birth": "1995-08-15",
        "pan_number": "ABCDE1234F",
        "residential_status": "resident",
        "employment_type": "salaried",
        "citizenship": "Indian",
        "address": "Bengaluru",
        "pincode": "560001",
        "salary_income": [{
            "employer_name": "Infosys Limited",
            "gross_salary": "1800000",
            "standard_deduction": "75000",
            "professional_tax": "2400",
            "tds": "210000",
        }],
        "pension_income": [],
        "house_properties": [],
        "other_income": [],
        "capital_gains": [],
        "deductions": [],
        "taxes_paid": [],
        "bank_accounts": [{
            "bank_name": "HDFC Bank",
            "account_number": "501234567890",
            "ifsc_code": "HDFC0001234",
            "account_type": "savings",
            "is_primary": True,
        }],
        "has_foreign_assets": False,
        "has_foreign_income": False,
        "foreign_income_assets": [],
    }


def test_itr2_readiness_only_counts_applicable_requirements():
    result = build_itr2_readiness(base_profile())
    assert result["ready"] is True
    assert result["completion_percentage"] == 100
    assert not any(item["section"] == "Capital gains" for item in result["requirements"])


def test_itr2_readiness_requires_every_capital_gain_transaction():
    profile = base_profile()
    profile["capital_gains"] = [
        {
            "asset_type": "listed_equity_share",
            "acquisition_date": "2025-06-10",
            "sale_date": "2025-12-20",
            "sale_consideration": "300000",
            "acquisition_cost": "220000",
            "improvement_cost": "0",
            "transfer_expenses": "2000",
        },
        {
            "asset_type": "listed_equity_share",
            "acquisition_date": "2023-05-10",
            "sale_date": "2026-01-15",
            "sale_consideration": "500000",
            "acquisition_cost": "300000",
            "improvement_cost": "0",
            "transfer_expenses": "2000",
        },
    ]
    result = build_itr2_readiness(profile)
    assert result["ready"] is True
    assert result["completion_percentage"] == 100
    assert len([x for x in result["requirements"] if x["section"] == "Capital gains"]) >= 10


def test_itr2_readiness_does_not_mark_unconfirmed_document_facts_complete():
    profile = base_profile()
    profile["pan_number"] = None
    result = build_itr2_readiness(profile, extraction_candidates=[{
        "field": "pan_number",
        "value": "ABCDE1234F",
        "source": "FORM_16",
        "page": 1,
        "confidence": "high",
        "requires_confirmation": True,
        "status": "candidate",
    }])
    assert result["ready"] is False
    assert any(item["key"] == "pan_number" and item["status"] == "needs_confirmation" for item in result["requirements"])
