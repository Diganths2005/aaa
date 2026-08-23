from typing import List

from .field_extractor import extract_candidates
from .models import ExtractionResult
from .pdf_extractor import extract_pdf_pages


def process_pdf(content: bytes) -> ExtractionResult:
    pages = extract_pdf_pages(content)
    if not any(page.strip() for page in pages):
        raise ValueError("DOCUMENT_REQUIRES_OCR")
    candidates = extract_candidates(pages)
    return ExtractionResult("\f".join(pages), len(pages), candidates, "form_16" if any(item.field in {"salary_income", "tds"} for item in candidates) else "other")