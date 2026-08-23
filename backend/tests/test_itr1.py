from decimal import Decimal

from itr.pdf import generate_itr1_pdf
from itr.service import check_itr1_eligibility, explain_itr_question, prepare_itr1
from schemas.tax_profile import TaxProfileCreate


def demo_profile(**overrides):
    values = {
        "pan_number": "ABCDE1234F",
        "date_of_birth": "2005-01-15",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Example Technologies Pvt Ltd", "gross_salary": 600000, "standard_deduction": 0, "professional_tax": 0, "tds": 25000}],
        "deductions": [{"section": "80C", "amount": 100000}],
        "taxes_paid": [{"tax_type": "tds", "amount": 25000}],
        "bank_accounts": [{"bank_name": "Demo Bank", "account_number": "000000123456", "ifsc_code": "DEMO0000001", "account_type": "savings", "is_primary": True}],
    }
    values.update(overrides)
    return TaxProfileCreate(**values)


def test_itr1_eligible_demo_profile():
    result = check_itr1_eligibility(demo_profile())
    assert result.eligible is True
    assert result.itr_form == "ITR-1"
    assert result.assessment_year == "2026-27"


def test_itr1_rejects_business_income():
    result = check_itr1_eligibility(demo_profile(has_business_income=True))
    assert result.eligible is False
    assert result.itr_form is None
    assert result.reasons


def test_itr1_maps_tax_engine_result_and_masks_bank():
    preparation = prepare_itr1(demo_profile(), "Demo Taxpayer", "old")
    assert preparation["income"]["salary"] == Decimal("600000")
    assert preparation["taxes_paid"]["tds"] == Decimal("25000")
    assert preparation["bank_accounts"][0]["account_number"] == "******3456"
    assert preparation["calculation"]["taxable_income"] >= 0


def test_itr1_explanation_uses_actual_values():
    preparation = prepare_itr1(demo_profile(), "Demo Taxpayer")
    answer = explain_itr_question("Why is my taxable income this amount?", preparation)
    assert f"{preparation['calculation']['taxable_income']:,.0f}" in answer
    assert "Tax Engine" in answer


def test_itr1_pdf_is_real_pdf_with_disclaimer():
    pdf = generate_itr1_pdf(prepare_itr1(demo_profile(), "Demo Taxpayer"))
    assert pdf.startswith(b"%PDF")
    assert b"TaxWise" in pdf
    assert b"does not submit this return" in pdf