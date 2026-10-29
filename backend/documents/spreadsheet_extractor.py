from datetime import date, datetime
import json
import re
from io import BytesIO
from typing import Any

from openpyxl import load_workbook\nfrom openpyxl.utils.cell import range_boundaries
from pydantic import ValidationError

from .field_extractor import extract_candidates, normalize_date_of_birth, parse_currency
from .models import ExtractedCandidate, ExtractionResult
from schemas.tax_profile import (
    BankAccount,
    BusinessIncome,
    CapitalGain,
    Deduction,
    DocumentReference,
    ForeignIncomeAsset,
    HouseProperty,
    Investment,
    OtherIncome,
    PensionIncome,
    SalaryIncome,
    TaxPayment,
    TaxProfileCreate,
)

PROFILE_IMPORT_SHEET = "TaxWise Profile Import"
PROFILE_COLLECTION_MODELS = {
    "salary_income": SalaryIncome,
    "pension_income": PensionIncome,
    "house_properties": HouseProperty,
    "other_income": OtherIncome,
    "capital_gains": CapitalGain,
    "business_income": BusinessIncome,
    "foreign_income_assets": ForeignIncomeAsset,
    "investments": Investment,
    "deductions": Deduction,
    "taxes_paid": TaxPayment,
    "bank_accounts": BankAccount,
    "documents": DocumentReference,
}

IMPORT_FIELDS = {
    "employee name": ("name", "text"),
    "taxpayer name": ("name", "text"),
    "name": ("name", "text"),
    "pan": ("pan_number", "pan"),
    "pan number": ("pan_number", "pan"),
    "date of birth": ("date_of_birth", "date"),
    "dob": ("date_of_birth", "date"),
    "employer": ("employer_name", "text"),
    "gross salary": ("salary_income", "currency"),
    "tds deducted": ("tds", "currency"),
    "professional receipts": ("business_receipts", "currency"),
    "net professional income": ("business_net_income", "currency"),
    "bank interest": ("other_income_interest", "currency"),
    "dividend income": ("other_income_dividend", "currency"),
    "section 80c": ("deduction_80C", "currency"),
    "section 80d": ("deduction_80D", "currency"),
    "80ccd(1b)": ("deduction_80CCD_1B", "currency"),
    "80g": ("deduction_80G", "currency"),
    "section 80g": ("deduction_80G", "currency"),
    "advance tax": ("advance_tax", "currency"),
}


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value).strip()


def _workbook_text(content: bytes) -> str:
    """Read workbook values with sheet/cell context.

    data_only=True is preferred for formulas because it exposes cached results.
    If a workbook has formulas without cached results, we also load the formula
    view and retain the formula text instead of silently dropping the cell.
    Merged cells and blank rows are handled without corrupting column order.
    """
    try:
        values_wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
        formulas_wb = load_workbook(BytesIO(content), read_only=True, data_only=False)
    except Exception as exc:
        raise ValueError("INVALID_SPREADSHEET") from exc

    rows: list[str] = []
    for worksheet in values_wb.worksheets:
        formula_sheet = formulas_wb[worksheet.title]
        rows.append(f"Sheet: {worksheet.title}")
        for row_index, value_row in enumerate(worksheet.iter_rows(values_only=True), start=1):
            formula_row = next(formula_sheet.iter_rows(
                min_row=row_index, max_row=row_index,
                min_col=1, max_col=worksheet.max_column,
                values_only=True
            ))
            parts: list[str] = []
            for column_index, value in enumerate(value_row, start=1):
                text = _cell_text(value)
                if not text:
                    formula = _cell_text(formula_row[column_index - 1])
                    if formula.startswith("="):
                        text = formula
                if text:
                    parts.append(text)
            if parts:
                rows.append(f"Row {row_index}: " + " | ".join(parts))
    values_wb.close()
    formulas_wb.close()

    text = "\n".join(rows)
    if not text.strip():
        raise ValueError("EMPTY_SPREADSHEET")
    return text

