from io import BytesIO
from decimal import Decimal
from reportlab.pdfgen.canvas import Canvas
from openpyxl import Workbook

from documents.extractor import process_pdf
from documents.spreadsheet_extractor import process_spreadsheet

def make_pdf(lines):
    out=BytesIO(); c=Canvas(out)
    for i,line in enumerate(lines): c.drawString(40,780-i*20,line)
    c.save(); return out.getvalue()

def test_complete_supported_tax_fields_are_extracted():
    pdf=make_pdf([
        "Employee Name: Example Taxpayer","PAN: ABCDE1234F","Date of Birth: 15/08/1990",
        "Employer Name: Example Employer","Gross Salary: 1000000","Standard Deduction: 75000",
        "Professional Tax: 2400","Pension Income: 120000","TDS Deducted: 100000",
        "Annual Rent: 240000","Municipal Tax: 12000","Home Loan Interest: 180000",
        "Bank Interest: 30000","Dividend Income: 20000","Advance Tax: 10000",
        "Self-Assessment Tax: 5000","Section 80C: 100000","Section 80D: 25000",
        "80CCD(1B): 50000","80E: 30000","80EEA: 40000","80GG: 60000","80U: 50000",
    ])
    values={c.field:c.value for c in process_pdf(pdf,"form_16").candidates}
    assert values["standard_deduction"]==Decimal("75000")
    assert values["professional_tax"]==Decimal("2400")
    assert values["pension_income"]==Decimal("120000")
    assert values["house_property_rent"]==Decimal("240000")
    assert values["house_property_municipal_tax"]==Decimal("12000")
    assert values["house_property_loan_interest"]==Decimal("180000")
    assert values["other_income_interest"]==Decimal("30000")
    assert values["other_income_dividend"]==Decimal("20000")
    assert values["advance_tax"]==Decimal("10000")
    assert values["self_assessment_tax"]==Decimal("5000")
    assert values["deduction_80E"]==Decimal("30000")
    assert values["deduction_80EEA"]==Decimal("40000")
    assert values["deduction_80GG"]==Decimal("60000")
    assert values["deduction_80U"]==Decimal("50000")

def test_complete_supported_tax_fields_are_extracted_from_excel():
    out=BytesIO(); wb=Workbook(); ws=wb.active; ws.title="Tax Data"
    for row in [
        ["Field","Value"],["Gross Salary",1000000],["Standard Deduction",75000],
        ["Professional Tax",2400],["Pension Income",120000],["Annual Rent",240000],
        ["Municipal Tax",12000],["Home Loan Interest",180000],["Bank Interest",30000],
        ["Dividend Income",20000],["80E",30000],["80EEA",40000],["Advance Tax",10000],
    ]: ws.append(row)
    wb.save(out)
    values={c.field:c.value for c in process_spreadsheet(out.getvalue()).candidates}
    assert values["salary_income"]==Decimal("1000000")
    assert values["standard_deduction"]==Decimal("75000")
    assert values["professional_tax"]==Decimal("2400")
    assert values["pension_income"]==Decimal("120000")
    assert values["house_property_rent"]==Decimal("240000")
    assert values["house_property_municipal_tax"]==Decimal("12000")
    assert values["house_property_loan_interest"]==Decimal("180000")
    assert values["deduction_80EEA"]==Decimal("40000")
