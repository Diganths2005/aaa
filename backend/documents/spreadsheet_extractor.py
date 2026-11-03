from datetime import date, datetime
from io import BytesIO
import json
import re
from typing import Any, get_args

from openpyxl import load_workbook
from pydantic import ValidationError

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

from .complete_field_extractor import extract_complete_candidates
from .field_extractor import extract_candidates, normalize_date_of_birth, parse_currency
from .models import ExtractedCandidate, ExtractionResult

PROFILE_IMPORT_SHEET = "TaxWise Profile Import"
SIMPLE_IMPORT_SHEET = "TaxWise Import Data"
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
    "employer name": ("employer_name", "text"),
    "gross salary": ("salary_income", "currency"),
    "salary": ("salary_income", "currency"),
    "tds deducted": ("tds", "currency"),
    "tds": ("tds", "currency"),
    "professional receipts": ("business_receipts", "currency"),
    "net professional income": ("business_net_income", "currency"),
    "bank interest": ("other_income_interest", "currency"),
    "interest income": ("other_income_interest", "currency"),
    "dividend income": ("other_income_dividend", "currency"),
    "section 80c": ("deduction_80C", "currency"),
    "section 80d": ("deduction_80D", "currency"),
    "80ccd(1b)": ("deduction_80CCD_1B", "currency"),
    "80g": ("deduction_80G", "currency"),
    "section 80g": ("deduction_80G", "currency"),
    "advance tax": ("advance_tax", "currency"),
}

BOOLEAN_FIELDS = {
    "is_senior_citizen",
    "is_director",
    "has_unlisted_equity",
    "has_foreign_assets",
    "has_foreign_income",
    "has_business_income",
    "has_speculative_income",
    "has_carry_forward_loss",
}


def _is_boolean_field(model: Any, field: str) -> bool:
    annotation = model.model_fields[field].annotation
    return annotation is bool or bool in get_args(annotation)


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _workbook_rows(content: bytes) -> list[tuple[str, int, list[str]]]:
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("INVALID_SPREADSHEET") from exc

    rows = []
    try:
        for worksheet in workbook.worksheets:
            for index, row in enumerate(worksheet.iter_rows(values_only=True), 1):
                values = [_cell_text(value) for value in row]
                if any(values):
                    rows.append((worksheet.title, index, values))
    finally:
        workbook.close()
    if not rows:
        raise ValueError("EMPTY_SPREADSHEET")
    return rows


def _normalize_import_date(value: str) -> str:
    normalized = normalize_date_of_birth(value)
    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        raise ValueError("INVALID_IMPORT_DATE_OF_BIRTH") from exc


def _simple_import(rows: list[tuple[str, int, list[str]]]) -> list[ExtractedCandidate]:
    imported_rows = [row for row in rows if row[0] == SIMPLE_IMPORT_SHEET]
    candidates = []
    seen_fields = set()
    for _, row_number, cells in imported_rows:
        if row_number < 4 or len(cells) < 2:
            continue
        mapped = IMPORT_FIELDS.get(cells[0].strip().casefold())
        raw_value = cells[1].strip()
        if mapped is None or not raw_value:
            continue

        field, value_type = mapped
        if field in seen_fields:
            raise ValueError("DUPLICATE_IMPORT_FIELD")
        seen_fields.add(field)

        if value_type == "currency":
            try:
                value = parse_currency(raw_value)
            except ValueError as exc:
                raise ValueError(f"INVALID_IMPORT_AMOUNT: {cells[0]}") from exc
        elif value_type == "pan":
            value = raw_value.upper()
            if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", value):
                raise ValueError("INVALID_IMPORT_PAN")
        elif value_type == "date":
            value = _normalize_import_date(raw_value)
        else:
            value = raw_value
        candidates.append(ExtractedCandidate(field, value, "SPREADSHEET", "high", row_number))
    return candidates


def _profile_import(rows: list[tuple[str, int, list[str]]]) -> list[ExtractedCandidate]:
    imported_rows = [row for row in rows if row[0] == PROFILE_IMPORT_SHEET]
    if not imported_rows:
        return []

    scalar_values: dict[str, Any] = {}
    taxpayer_name = None
    for _, row_number, cells in imported_rows:
        if row_number < 4 or len(cells) < 2:
            continue
        key, value = cells[0].strip().lower(), cells[1].strip()
        if not value:
            continue
        if key == "taxpayer_name":
            if taxpayer_name is not None:
                raise ValueError("DUPLICATE_PROFILE_FIELD: taxpayer_name")
            taxpayer_name = value
            continue
        if key not in TaxProfileCreate.model_fields:
            raise ValueError(f"UNKNOWN_PROFILE_IMPORT_FIELD: {key}")
        if key in scalar_values:
            raise ValueError(f"DUPLICATE_PROFILE_FIELD: {key}")
        if key == "date_of_birth":
            value = _normalize_import_date(value)
        elif key in BOOLEAN_FIELDS:
            normalized = value.casefold()
            if normalized not in {"yes", "no", "true", "false", "1", "0"}:
                raise ValueError(f"INVALID_PROFILE_IMPORT: {key}")
            value = normalized in {"yes", "true", "1"}
        scalar_values[key] = value

    try:
        profile_values = TaxProfileCreate.model_validate(scalar_values).model_dump(
            mode="json", exclude_unset=True
        )
    except ValidationError as exc:
        raise ValueError(f"INVALID_PROFILE_IMPORT: {exc}") from exc
    if taxpayer_name:
        profile_values["name"] = taxpayer_name

    for sheet_name, model in PROFILE_COLLECTION_MODELS.items():
        sheet_rows = [row for row in rows if row[0] == sheet_name]
        if not sheet_rows:
            continue
        header_row = next((row[2] for row in sheet_rows if row[1] == 3), [])
        headers = [header.strip() for header in header_row]
        while headers and not headers[-1]:
            headers.pop()
        if not headers or any(not header for header in headers) or len(headers) != len(set(headers)):
            raise ValueError(f"INVALID_PROFILE_IMPORT_HEADERS: {sheet_name}")
        unknown_headers = set(headers) - set(model.model_fields)
        if unknown_headers:
            raise ValueError(
                f"UNKNOWN_PROFILE_IMPORT_FIELDS: {sheet_name}: {', '.join(sorted(unknown_headers))}"
            )

        records = []
        for _, row_number, cells in sheet_rows:
            if row_number < 4:
                continue
            record = {
                header: value
                for header, value in zip(headers, cells)
                if value != ""
            }
            if not record:
                continue
            boolean_fields = {
                field for field in record if _is_boolean_field(model, field)
            }
            for field in boolean_fields:
                normalized = record[field].casefold()
                if normalized not in {"yes", "no", "true", "false", "1", "0"}:
                    raise ValueError(f"INVALID_PROFILE_IMPORT: {sheet_name}.{field}")
                record[field] = normalized in {"yes", "true", "1"}
            try:
                records.append(model.model_validate(record).model_dump(mode="json", exclude_unset=True))
            except ValidationError as exc:
                raise ValueError(f"INVALID_PROFILE_IMPORT: {sheet_name}: {exc}") from exc
        if records:
            profile_values[sheet_name] = records

    if not profile_values:
        return []
    return [
        ExtractedCandidate(
            "profile_import",
            json.dumps(profile_values, ensure_ascii=False, separators=(",", ":")),
            "TAXWISE_PROFILE_WORKBOOK",
            "high",
            1,
        )
    ]


def process_spreadsheet(content: bytes) -> ExtractionResult:
    rows = _workbook_rows(content)
    sheet_count = len({row[0] for row in rows})
    text = "\n".join(" | ".join(row[2]) for row in rows)
    if any(row[0] == PROFILE_IMPORT_SHEET for row in rows):
        return ExtractionResult(
            text,
            sheet_count,
            _profile_import(rows),
            "spreadsheet",
        )

    if any(row[0] == SIMPLE_IMPORT_SHEET for row in rows):
        return ExtractionResult(
            text,
            sheet_count,
            _simple_import(rows),
            "spreadsheet",
        )

    text = "\n".join(
        f"Sheet: {sheet} Row {row}: " + " | ".join(cells)
        for sheet, row, cells in rows
    )
    candidates = extract_complete_candidates([text], "SPREADSHEET")
    seen = {candidate.field for candidate in candidates}
    candidates.extend(
        candidate
        for candidate in extract_candidates([text], "SPREADSHEET")
        if candidate.field not in seen
    )
    return ExtractionResult(text, sheet_count, candidates, "spreadsheet")
