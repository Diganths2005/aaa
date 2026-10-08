from decimal import Decimal

from schemas.tax_profile import SalaryIncome, TaxProfileCreate
from services.profile_completeness import profile_completeness
from services.reconciliation import reconcile_candidate


def test_profile_completeness_requires_income_and_tax_payment_confirmation():
    profile = TaxProfileCreate(
        pan_number="ABCDE1234F",
        date_of_birth="2005-01-15",
        employment_type="salaried",
        employer_name="Example Ltd",
        salary_income=[SalaryIncome(employer_name="Example Ltd", gross_salary=Decimal("600000"))],
    )
    result = profile_completeness(profile)
    assert result["complete"] is False
    assert "taxes_paid_or_confirmed_none" in result["missing_fields"]


def test_reconciliation_detects_scalar_salary_conflict():
    profile = TaxProfileCreate(
        pan_number="ABCDE1234F",
        salary_income=[SalaryIncome(employer_name="Example Ltd", gross_salary=Decimal("600000"))],
    )
    warnings = reconcile_candidate(profile, {"salary_income": "700000"})
    assert any(item["field"] == "salary_income" and item["severity"] == "medium" for item in warnings)


def test_reconciliation_detects_pan_conflict():
    profile = TaxProfileCreate(pan_number="ABCDE1234F")
    warnings = reconcile_candidate(profile, {"pan_number": "FGHIJ5678K"})
    assert warnings
    assert warnings[0]["field"] == "pan_number"
    assert warnings[0]["severity"] == "high"
