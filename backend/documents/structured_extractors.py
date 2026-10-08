from __future__ import annotations

import re
from typing import Iterable

from .field_extractor import first_match, normalize_date_of_birth, parse_currency
from .models import ExtractedCandidate


def _candidate(field: str, value: object, source: str, page: int, confidence: str = "medium") -> ExtractedCandidate:
    return ExtractedCandidate(field, value, source, confidence, page)


def _currency_candidate(text: str, field: str, patterns: Iterable[str], source: str) -> ExtractedCandidate | None:
    result = first_match(text, patterns)
    if not result:
        return None
    raw, page = result
    try:
        return _candidate(field, parse_currency(raw), source, page, "high")
    except ValueError:
        return None


def extract_form_16_candidates(pages: list[str]) -> list[ExtractedCandidate]:
    text = "\f".join(pages)
    result: list[ExtractedCandidate] = []
    for field, patterns in {
        "name": (r"(?:Employee\s+Name|Name\s+of\s+(?:the\s+)?Employee)\s*(?:[:|]\s*)?([^\n|]+)",),
        "pan_number": (r"PAN\s*(?:Number|No\.?)?\s*(?:[:|]\s*)?([A-Z]{5}\d{4}[A-Z])",),
        "employer_name": (r"(?:Name\s+and\s+address\s+of\s+the\s+Employer|Employer\s+Name)\s*(?:[:|]\s*)?([^\n|]+)",),
        "date_of_birth": (r"(?:Date\s+of\s+Birth|DOB)\s*(?:[:|]\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",),
    }.items():
        found = first_match(text, patterns)
        if found:
            value, page = found
            if field == "date_of_birth":
                value = normalize_date_of_birth(value)
            result.append(_candidate(field, value, "FORM_16", page, "high"))
    for field, patterns in {
        "salary_income": (
            r"(?:Gross\s+Salary|Total\s+Gross\s+Salary|Salary\s+as\s+per\s+provisions\s+contained\s+in\s+section\s+17\(1\))\s*:?[\s|]*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
        "tds": (
            r"(?:Total\s+amount\s+of\s+TDS\s+deducted|TDS\s+Deducted|Tax\s+Deducted\s+at\s+Source)\s*:?[\s|]*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
    }.items():
        candidate = _currency_candidate(text, field, patterns, "FORM_16")
        if candidate:
            result.append(candidate)
    return result


def extract_form_26as_candidates(pages: list[str]) -> list[ExtractedCandidate]:
    text = "\f".join(pages)
    result: list[ExtractedCandidate] = []
    pan = first_match(text, (r"PAN\s*(?:of\s+the\s+Deductee|Number|No\.?)?\s*(?:[:|]\s*)?([A-Z]{5}\d{4}[A-Z])",))
    if pan:
        result.append(_candidate("pan_number", pan[0], "FORM_26AS", pan[1], "high"))

    total = _currency_candidate(
        text,
        "tds",
        (
            r"(?:Total\s+(?:TDS|tax)\s+deducted|Total\s+amount\s+of\s+tax\s+deducted)\s*:?[\s|]*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
            r"(?:Total\s+TDS\s+Deposited)\s*:?[\s|]*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
        "FORM_26AS",
    )
    if total:
        result.append(total)
    return result


def extract_ais_tis_candidates(pages: list[str]) -> list[ExtractedCandidate]:
    text = "\f".join(pages)
    result: list[ExtractedCandidate] = []
    pan = first_match(text, (r"PAN\s*(?:Number|No\.?)?\s*(?:[:|]\s*)?([A-Z]{5}\d{4}[A-Z])",))
    if pan:
        result.append(_candidate("pan_number", pan[0], "AIS_TIS", pan[1], "high"))

    patterns = {
        "salary_income": (
            r"(?:Salary|Income\s+from\s+Salary)\s*(?:[:|]\s*)?[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
        "other_income_interest": (
            r"(?:Interest\s+Income|Interest\s+from\s+Bank)\s*(?:[:|]\s*)?[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
        "other_income_dividend": (
            r"(?:Dividend\s+Income|Dividend)\s*(?:[:|]\s*)?[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
        "tds": (
            r"(?:TDS|Tax\s+Deducted)\s*(?:[:|]\s*)?[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",
        ),
    }
    for field, field_patterns in patterns.items():
        candidate = _currency_candidate(text, field, field_patterns, "AIS_TIS")
        if candidate:
            result.append(candidate)
    return result


def extract_structured_candidates(pages: list[str], document_type: str) -> list[ExtractedCandidate]:
    if document_type == "form_16":
        return extract_form_16_candidates(pages)
    if document_type == "form_26as":
        return extract_form_26as_candidates(pages)
    if document_type == "ais_tis":
        return extract_ais_tis_candidates(pages)
    return []
