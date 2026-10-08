from datetime import date, datetime
import json
import re
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
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


def _workbook_text(content: bytes) -> str:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    rows: list[str] = []
    for worksheet in workbook.worksheets:
        rows.append(f"Sheet: {worksheet.title}")
        for row in worksheet.iter_rows(values_only=True):
            values = [str(value).strip() for value in row if value is not None and str(value).strip()]
            if values:
                rows.append(": ".join(values) if len(values) == 2 else " | ".join(values))
    return "\n".join(rows)


def _import_template_candidates(content: bytes) -> list[ExtractedCandidate]:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    worksheet = workbook["TaxWise Import Data"]
    candidates: list[ExtractedCandidate] = []
    seen_fields: set[str] = set()

    for row in worksheet.iter_rows(min_row=4, min_col=1, max_col=2, values_only=True):
        label, raw_value = row
        if label is None or raw_value is None or not str(raw_value).strip():
            continue

        mapped = IMPORT_FIELDS.get(str(label).strip().casefold())
        if mapped is None:
            continue

        field, value_type = mapped
        if field in seen_fields:
            raise ValueError(f"DUPLICATE_IMPORT_FIELD: {label}")
        seen_fields.add(field)

        value: Any
        if value_type == "currency":
            try:
                value = parse_currency(str(raw_value))
            except ValueError as exc:
                raise ValueError(f"INVALID_IMPORT_AMOUNT: {label}") from exc
        elif value_type == "pan":
            value = str(raw_value).strip().upper()
            if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", value):
                raise ValueError("INVALID_IMPORT_PAN")
        elif value_type == "date":
            if isinstance(raw_value, (datetime, date)):
                value = raw_value.date().isoformat() if isinstance(raw_value, datetime) else raw_value.isoformat()
            else:
                value = normalize_date_of_birth(str(raw_value).strip())
                if value == str(raw_value).strip() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError("INVALID_IMPORT_DATE_OF_BIRTH")
        else:
            value = str(raw_value).strip()

        candidates.append(ExtractedCandidate(field, value, "SPREADSHEET", "high", 1))

    return candidates


def _profile_import_candidates(content: bytes) -> list[ExtractedCandidate]:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    scalar_sheet = workbook[PROFILE_IMPORT_SHEET]
    scalar_values: dict[str, Any] = {}
    taxpayer_name: str | None = None
    seen_taxpayer_name = False

    for row in scalar_sheet.iter_rows(min_row=4, min_col=1, max_col=2, values_only=True):
        field, value = row
        if field is None or value is None or not str(value).strip():
            continue
        field_name = str(field).strip()
        if field_name == "taxpayer_name":
            if seen_taxpayer_name:
                raise ValueError("DUPLICATE_PROFILE_FIELD: taxpayer_name")
            seen_taxpayer_name = True
            taxpayer_name = str(value).strip()
        elif field_name in TaxProfileCreate.model_fields:
            if field_name in scalar_values:
                raise ValueError(f"DUPLICATE_PROFILE_FIELD: {field_name}")
            if field_name == "date_of_birth":
                if isinstance(value, (datetime, date)):
                    normalized_date = value.date() if isinstance(value, datetime) else value
                    value = normalized_date.isoformat()
                else:
                    original_value = str(value).strip()
                    value = normalize_date_of_birth(original_value)
                    try:
                        date.fromisoformat(value)
                    except ValueError as exc:
                        raise ValueError("INVALID_IMPORT_DATE_OF_BIRTH") from exc
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            scalar_values[field_name] = value
        else:
            raise ValueError(f"UNKNOWN_PROFILE_IMPORT_FIELD: {field_name}")

    try:
        validated_scalars = TaxProfileCreate.model_validate(scalar_values).model_dump(
            mode="json", exclude_unset=True
        )
    except ValidationError as exc:
        raise ValueError(f"INVALID_PROFILE_IMPORT: {exc}") from exc

    profile_values: dict[str, Any] = dict(validated_scalars)
    if taxpayer_name:
        profile_values["name"] = taxpayer_name

    for field_name, model in PROFILE_COLLECTION_MODELS.items():
        if field_name not in workbook.sheetnames:
            continue
        worksheet = workbook[field_name]
        headers = [
            str(value).strip() if value is not None else ""
            for value in next(worksheet.iter_rows(min_row=3, max_row=3, values_only=True))
        ]
        if not headers or not headers[0] or len(headers) != len(set(headers)):
            raise ValueError(f"INVALID_PROFILE_IMPORT_HEADERS: {field_name}")

        records: list[dict[str, Any]] = []
        for row in worksheet.iter_rows(min_row=4, values_only=True):
            record = {
                header: value.isoformat() if isinstance(value, (datetime, date)) else value
                for header, value in zip(headers, row)
                if header and value is not None and value != ""
            }
            if not record:
                continue
            unknown_fields = set(record) - set(model.model_fields)
            if unknown_fields:
                raise ValueError(
                    f"UNKNOWN_PROFILE_IMPORT_FIELDS: {field_name}: {', '.join(sorted(unknown_fields))}"
                )
            try:
                records.append(model.model_validate(record).model_dump(mode="json", exclude_unset=True))
            except ValidationError as exc:
                raise ValueError(f"INVALID_PROFILE_IMPORT: {field_name}: {exc}") from exc
        if records:
            profile_values[field_name] = records

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
    text = _workbook_text(content)
    if not text.strip():
        raise ValueError("EMPTY_SPREADSHEET")
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    if PROFILE_IMPORT_SHEET in workbook.sheetnames:
        candidates = _profile_import_candidates(content)
    elif "TaxWise Import Data" in workbook.sheetnames:
        candidates = _import_template_candidates(content)
    else:
        candidates = extract_candidates([text], source="SPREADSHEET")
    return ExtractionResult(text, 1, candidates, "form_16" if any(item.field in {"salary_income", "tds"} for item in candidates) else "other")
