import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import ExtractedCandidate


def parse_currency(value: str) -> Decimal:
    cleaned = value.replace("₹", "").replace(",", "").strip()
    multiplier = Decimal("1")
    if re.search(r"\b(?:lakh|lakhs|lac|l)\b$", cleaned, re.IGNORECASE):
        cleaned = re.sub(r"\s*(?:lakh|lakhs|lac|l)$", "", cleaned, flags=re.IGNORECASE).strip()
        multiplier = Decimal("100000")
    try:
        parsed = Decimal(cleaned) * multiplier
    except InvalidOperation as exc:
        raise ValueError("Malformed currency value") from exc
    if parsed < 0:
        raise ValueError("Currency value cannot be negative")
    return parsed


def first_match(text: str, patterns: Iterable[str]) -> Optional[Tuple[str, int]]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(), text[:match.start()].count("\f") + 1
    return None


def extract_candidates(pages: List[str], source: str = "FORM_16") -> List[ExtractedCandidate]:
    text = "\f".join(pages)
    candidates: List[ExtractedCandidate] = []
    text_patterns: Dict[str, Iterable[str]] = {
        "name": (r"(?:Employee\s+Name|Taxpayer\s+Name)\s*:\s*([^\n]+)",),
        "pan_number": (r"PAN\s*(?:Number)?\s*:\s*([A-Z]{5}\d{4}[A-Z])",),
        "assessment_year": (r"Assessment\s+Year\s*:\s*(\d{4}-\d{2})",),
        "financial_year": (r"Financial\s+Year\s*:\s*(\d{4}-\d{2})",),
        "employer_name": (r"Employer\s*:\s*([^\n]+)",),
    }
    for field, patterns in text_patterns.items():
        result = first_match(text, patterns)
        if result:
            value, page = result
            candidates.append(ExtractedCandidate(field, value, source, "high", page))
    currency_patterns = {
        "salary_income": (r"(?:Gross\s+Salary|Gross\s+Pay)\s*:\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
        "tds": (r"(?:TDS\s+Deducted|Tax\s+Deducted\s+at\s+Source|TDS)\s*:\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
        "deduction_80C": (r"(?:Section\s*80C|80C\s+Investment)\s*:\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
        "deduction_80D": (r"(?:Section\s*80D|80D)\s*:\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
    }
    for field, patterns in currency_patterns.items():
        result = first_match(text, patterns)
        if result:
            raw_value, page = result
            try:
                value = parse_currency(raw_value)
            except ValueError:
                continue
            candidates.append(ExtractedCandidate(field, value, source, "high", page))
    return candidates