from io import BytesIO
from decimal import Decimal

import pytest
from reportlab.pdfgen.canvas import Canvas

from documents.extractor import process_pdf
from documents.field_extractor import parse_currency


def synthetic_form16() -> bytes:
    output = BytesIO()
    canvas = Canvas(output)
    lines = [
        "Employee Name: Diganth H M",
        "PAN: ABCDE1234F",
        "Assessment Year: 2026-27",
        "Financial Year: 2025-26",
        "Employer: Example Technologies Pvt Ltd",
        "Gross Salary: ₹8,40,000",
        "TDS Deducted: ₹42,000",
        "Section 80C Investment: ₹1,00,000",
        "Section 80D: ₹20,000",
    ]
    for index, line in enumerate(lines):
        canvas.drawString(40, 780 - index * 24, line)
    canvas.save()
    return output.getvalue()


def test_extracts_form16_candidates_from_pdf_text():
    result = process_pdf(synthetic_form16())
    values = {candidate.field: candidate.value for candidate in result.candidates}
    assert values["name"] == "Diganth H M"
    assert values["pan_number"] == "ABCDE1234F"
    assert values["employer_name"] == "Example Technologies Pvt Ltd"
    assert values["salary_income"] == Decimal("840000")
    assert values["tds"] == Decimal("42000")
    assert values["deduction_80C"] == Decimal("100000")
    assert values["deduction_80D"] == Decimal("20000")


def test_extracts_common_form16_labels_without_colons():
    output = BytesIO()
    canvas = Canvas(output)
    lines = [
        "Name of Employee Diganth H M",
        "PAN No. ABCDE1234F",
        "Employer Name Example Technologies Pvt Ltd",
        "Total Gross Salary 840000",
        "Total amount of TDS deducted 42000",
        "Deductions under section 80C 100000",
    ]
    for index, line in enumerate(lines):
        canvas.drawString(40, 780 - index * 24, line)
    canvas.save()

    values = {candidate.field: candidate.value for candidate in process_pdf(output.getvalue()).candidates}
    assert values["name"] == "Diganth H M"
    assert values["pan_number"] == "ABCDE1234F"
    assert values["salary_income"] == Decimal("840000")
    assert values["tds"] == Decimal("42000")
    assert values["deduction_80C"] == Decimal("100000")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("₹8,40,000", Decimal("840000")), ("8.4 lakh", Decimal("840000")), ("840000", Decimal("840000"))],
)
def test_parse_currency(value, expected):
    assert parse_currency(value) == expected


def test_scanned_pdf_requires_ocr():
    output = BytesIO()
    Canvas(output).save()
    with pytest.raises(ValueError, match="DOCUMENT_REQUIRES_OCR"):
        process_pdf(output.getvalue())