from io import BytesIO
from typing import List

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf_pages(content: bytes) -> List[str]:
    try:
        reader = PdfReader(BytesIO(content))
    except PdfReadError as exc:
        raise ValueError("Invalid PDF document") from exc
    return [page.extract_text() or "" for page in reader.pages]