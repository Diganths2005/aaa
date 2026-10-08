from typing import List

from .field_extractor import extract_candidates
from .models import ExtractionResult
from .pdf_extractor import extract_pdf_pages


def process_pdf(content: bytes, document_type: str = "other") -> ExtractionResult:
    pages = extract_pdf_pages(content)
    if not any(page.strip() for page in pages):
        raise ValueError("DOCUMENT_REQUIRES_OCR")

    source_map = {
        "form_16": "FORM_16",
        "form_26as": "FORM_26AS",
        "ais_tis": "AIS_TIS",
        "bank_statement": "BANK_STATEMENT",
        "investment_statement": "INVESTMENT_STATEMENT",
        "capital_gains": "CAPITAL_GAINS",
        "insurance": "INSURANCE",
        "loan": "LOAN",
        "other": "OTHER",
    }
    source = source_map.get(document_type, "OTHER")
    candidates = extract_candidates(pages, source=source)

    # Never infer the document type from a single extracted field. The caller
    # selected the document type explicitly, so retain that provenance.
    return ExtractionResult("\f".join(pages), len(pages), candidates, document_type)
