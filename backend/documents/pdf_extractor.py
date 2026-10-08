from io import BytesIO
from typing import List

import fitz
from pypdf import PdfReader
from pypdf.errors import PdfReadError
try:
    import pytesseract
except ImportError:
    pytesseract = None


def extract_pdf_pages(content: bytes) -> List[str]:
    try:
        reader = PdfReader(BytesIO(content))
    except PdfReadError as exc:
        raise ValueError("Invalid PDF document") from exc

    pages = [page.extract_text() or "" for page in reader.pages]
    if any(page.strip() for page in pages):
        return pages
    if not pages:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from None

    if pytesseract is None:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from None

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
        pages = []
        for page in pdf:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pages.append(pytesseract.image_to_string(pixmap))
        if not any(page.strip() for page in pages):
            raise ValueError("DOCUMENT_REQUIRES_OCR")
        return pages
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from exc
    except pytesseract.TesseractError as exc:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from exc
    except (RuntimeError, ValueError) as exc:
        raise ValueError("Could not render PDF for OCR") from exc