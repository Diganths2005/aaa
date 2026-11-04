from io import BytesIO
from typing import List

import fitz
from pypdf import PdfReader
from pypdf.errors import PdfReadError

try:
    import pytesseract
except ImportError:
    pytesseract = None


def _ocr_page(page: fitz.Page) -> str:
    if pytesseract is None:
        raise ValueError("DOCUMENT_REQUIRES_OCR")
    try:
        # 300-ish DPI gives Tesseract enough resolution for government forms
        # without creating unnecessarily huge images.
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
        text = pytesseract.image_to_string(pixmap, config="--psm 6")
        return text or ""
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from exc
    except pytesseract.TesseractError as exc:
        raise ValueError("DOCUMENT_REQUIRES_OCR") from exc


def extract_pdf_pages(content: bytes) -> List[str]:
    """Extract every PDF page, using OCR only for pages with no usable text.

    A PDF can be mixed: some pages contain a real text layer while other pages
    are scanned images. The old implementation returned as soon as it found
    any text page, silently losing all scanned pages. We now process pages
    independently and preserve page boundaries.
    """
    try:
        reader = PdfReader(BytesIO(content))
    except (PdfReadError, ValueError, TypeError) as exc:
        raise ValueError("Invalid PDF document") from exc

    if not reader.pages:
        raise ValueError("DOCUMENT_REQUIRES_OCR")

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise ValueError("Invalid PDF document") from exc

    if pdf.page_count != len(reader.pages):
        raise ValueError("PDF_PAGE_COUNT_MISMATCH")

    extracted: List[str] = []
    needs_ocr = False
    for index, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            extracted.append(text)
            continue

        needs_ocr = True
        extracted.append("")

    if needs_ocr:
        if pytesseract is None:
            raise ValueError("DOCUMENT_REQUIRES_OCR")
        for index, text in enumerate(extracted):
            if text:
                continue
            ocr_text = _ocr_page(pdf.load_page(index)).strip()
            if not ocr_text:
                raise ValueError(f"DOCUMENT_REQUIRES_OCR_PAGE:{index + 1}")
            extracted[index] = ocr_text

    if not any(page.strip() for page in extracted):
        raise ValueError("DOCUMENT_REQUIRES_OCR")
    return extracted
