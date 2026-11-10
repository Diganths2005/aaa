from decimal import Decimal

from itr.readiness import build_return_readiness
from schemas.tax_profile import TaxProfileCreate


def profile(**overrides):
    values = {
        "pan_number": "ABCDE1234F",
        "date_of_birth": "1990-01-01",
        "residential_status": "resident",
        "employment_type": "salaried",
        "address": "42 Test Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "salary_income": [{
            "employer_name": "Acme",
            "gross_salary": 1800000,
            "standard_deduction": 75000,
            "tds": 210000,
        }],
        "bank_accounts": [{
            "bank_name": "HDFC Bank",
            "account_number": "1234567890",
            "ifsc_code": "HDFC0001234",
            "is_primary": True,
        }],
        "documents": [{
            "document_type": "form_16",
            "file_name": "form16.pdf",
        }],
    }
    values.update(overrides)
    return TaxProfileCreate(**values)


def test_readiness_is_return_family_aware():
    result = build_return_readiness(profile())
    assert result["recommended_itr"] == "ITR-1"
    assert result["completion_percentage"] == 100
    assert result["status"] == "ready"


def test_itr2_readiness_exposes_transaction_level_missing_data():
    p = profile(capital_gains=[{
        "asset_type": "listed_equity_share",
        "acquisition_date": "2025-01-01",
        "sale_date": "2025-08-01",
        "sale_consideration": 500000,
        "acquisition_cost": 400000,
        "is_listed": True,
    }], documents=[{
        "document_type": "form_16",
        "file_name": "form16.pdf",
    }])
    result = build_return_readiness(p)
    assert result["recommended_itr"] == "ITR-2"
    labels = {item["label"] for item in result["missing"]}
    assert "Listed-equity/STT details #1" in labels
    assert "Capital-gains statement/evidence" in labels


def test_80g_is_not_marked_complete_without_schedule_identifiers():
    p = profile(deductions=[{"section": "80G", "amount": 20000}])
    result = build_return_readiness(p)
    item = next(item for item in result["missing"] if "80G" in item["label"])
    assert "identifier" in item["reason"].lower()
