from io import BytesIO
from decimal import Decimal

import pytest
from reportlab.pdfgen.canvas import Canvas

from documents.extractor import process_pdf
from documents.field_extractor import parse_currency
from documents.pdf_extractor import extract_pdf_pages
from documents.spreadsheet_extractor import process_spreadsheet
from openpyxl import Workbook


def synthetic_form16() -> bytes:
    output = BytesIO()
    canvas = Canvas(output)
    lines = [
        "Employee Name: Diganth H M",
        "PAN: ABCDE1234F",
        "Date of Birth: 15/08/1990",
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
    assert values["date_of_birth"] == "1990-08-15"
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


def test_extracts_official_form16_salary_labels():
    output = BytesIO()
    canvas = Canvas(output)
    canvas.drawString(40, 780, "Total amount of salary received from current employer(s) 1250000")
    canvas.drawString(40, 756, "Income chargeable under the head Salaries 1180000")
    canvas.save()

    values = {candidate.field: candidate.value for candidate in process_pdf(output.getvalue()).candidates}
    assert values["salary_income"] == Decimal("1250000")


def test_extracts_itr3_workbook_income_and_tax_rows():
    output = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ITR-3 Test Data"
    for row in [
        ["Business/Professional", "Professional Receipts", "2400000"],
        ["Business/Professional", "Professional Expenses", "700000"],
        ["Business/Professional", "Net Professional Income", "1700000"],
        ["Income", "Bank Interest", "30000"],
        ["Income", "Dividend Income", "10000"],
        ["Deductions", "80C", "100000"],
        ["Deductions", "80CCD(1B)", "50000"],
        ["Tax Paid", "TDS", "150000"],
        ["Tax Paid", "Advance Tax", "50000"],
    ]:
        sheet.append(row)
    workbook.save(output)

    values = {candidate.field: candidate.value for candidate in process_spreadsheet(output.getvalue()).candidates}
    assert values["business_receipts"] == Decimal("2400000")
    assert values["business_net_income"] == Decimal("1700000")
    assert values["other_income_interest"] == Decimal("30000")
    assert values["other_income_dividend"] == Decimal("10000")
    assert values["deduction_80C"] == Decimal("100000")
    assert values["deduction_80CCD_1B"] == Decimal("50000")
    assert values["advance_tax"] == Decimal("50000")


def test_extracts_personal_fields_from_pipe_delimited_workbook_rows():
    output = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ITR-3 Test Data"
    for row in [
        ["Section", "Field", "Test Value"],
        ["Personal", "Date of Birth", "15-06-1990"],
        ["Personal", "PAN", "ABCDE1234F"],
    ]:
        sheet.append(row)
    workbook.save(output)

    values = {candidate.field: candidate.value for candidate in process_spreadsheet(output.getvalue()).candidates}
    assert values["date_of_birth"] == "1990-06-15"
    assert values["pan_number"] == "ABCDE1234F"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("₹8,40,000", Decimal("840000")),
        ("Rs. 8,40,000", Decimal("840000")),
        ("INR 8.4 lakh", Decimal("840000")),
        ("8.4 lakh", Decimal("840000")),
        ("840000", Decimal("840000")),
    ],
)
def test_parse_currency(value, expected):
    assert parse_currency(value) == expected


def test_scanned_pdf_requires_ocr():
    output = BytesIO()
    Canvas(output).save()
    with pytest.raises(ValueError, match="DOCUMENT_REQUIRES_OCR"):
        process_pdf(output.getvalue())


def test_scanned_pdf_uses_ocr_fallback(monkeypatch):
    output = BytesIO()
    canvas = Canvas(output)
    canvas.showPage()
    canvas.save()

    monkeypatch.setattr("documents.pdf_extractor.pytesseract.image_to_string", lambda image: "Employee Name: OCR User")
    assert extract_pdf_pages(output.getvalue()) == ["Employee Name: OCR User"]