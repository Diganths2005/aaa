from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from services.deduction_discovery import discover_deductions


def make_profile(**kwargs):
    defaults = {
        "assessment_year": "2026-27",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
    }
    defaults.update(kwargs)
    return TaxProfileCreate(**defaults)


def test_discover_deductions_identifies_salary_related_candidates():
    profile = make_profile()
    findings = discover_deductions(profile, regime="old")
    sections = {item["section"] for item in findings}
    assert "80C" in sections
    assert "80CCD(1B)" in sections
    assert "80D" in sections


def test_missing_health_insurance_stays_unknown_not_no():
    profile = make_profile()
    findings = {item["section"]: item for item in discover_deductions(profile, regime="old")}
    result = findings["80D"]
    assert result["status"] in {"UNKNOWN", "NEEDS_INFORMATION"}
    assert result["claimedAmount"] == 0
    assert result["appliedAmount"] == 0
    assert "health insurance" in result["explanation"].lower()


def test_deduction_amount_uses_existing_engine_for_confirmed_80c():
    profile = make_profile(deductions=[{"section": "80C", "amount": 100000}])
    findings = {item["section"]: item for item in discover_deductions(profile, regime="old")}
    result = findings["80C"]
    assert result["claimedAmount"] == Decimal("100000")
    assert result["eligibleAmount"] == Decimal("100000")
    assert result["appliedAmount"] == Decimal("100000")
    assert result["status"] in {"ELIGIBLE", "CONFIRMED", "APPLIED"}


def test_nps_contribution_is_detected_when_present():
    profile = make_profile(deductions=[{"section": "80CCD(1B)", "amount": 50000}])
    findings = {item["section"]: item for item in discover_deductions(profile, regime="old")}
    result = findings["80CCD(1B)"]
    assert result["claimedAmount"] == Decimal("50000")
    assert result["appliedAmount"] == Decimal("50000")
    assert result["status"] in {"ELIGIBLE", "CONFIRMED", "APPLIED"}
