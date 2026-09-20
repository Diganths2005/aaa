from io import BytesIO
from typing import List

import fitz
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import pytesseract


def extract_pdf_pages(content: bytes) -> List[str]:
    try:
        reader = PdfReader(BytesIO(content))
    except PdfReadError as exc:
        raise ValueError("Invalid PDF document") from exc

    pages = [page.extract_text() or "" for page in reader.pages]
    if any(page.strip() for page in pages):
        return pages

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
        return [pytesseract.image_to_string(page.get_pixmap(matrix=fitz.Matrix(2, 2))) for page in pdf]
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from exc
    except (RuntimeError, ValueError) as exc:
        raise ValueError("Could not render PDF for OCR") from exc