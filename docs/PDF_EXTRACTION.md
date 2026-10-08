# Document Extraction and Review

TaxWise accepts PDFs and Excel workbooks (`.xlsx`, `.xlsm`) through the authenticated document workflow. Uploading or processing a document never changes the Tax Profile by itself.

## Flow

```text
Upload -> temporary storage -> text/workbook extraction -> field candidates
  -> review on Documents page -> Confirm or Reject -> Tax Profile
```

`POST /api/v1/documents/upload` accepts a file up to 10 MB. `POST /api/v1/documents/{document_id}/process` extracts text and field candidates. Each candidate includes its source, confidence, and page where available; extracted amounts are parsed with `Decimal`. The processor also builds an onboarding-compatible payload for profile validation.

PDF text is extracted with `pypdf`. When no page text is available, the backend attempts OCR through PyMuPDF and `pytesseract`. A working Tesseract executable must be installed on the backend host; otherwise the API returns `DOCUMENT_REQUIRES_OCR`. OCR is a conditional fallback, not a guarantee that every scanned layout can be read.

Excel worksheets are read with `openpyxl`; supported text labels are passed through the same field detector. The extraction rules cover only known labels and candidate fields. Other layouts and ambiguous values may not be recognized correctly.

The Documents page shows candidates and requires the user to confirm or reject the mapped set. Confirmed values are validated and merged with the existing profile through the onboarding confirmation service. Rejection does not write profile data. Review status is persisted as `CONFIRMED` or `REJECTED`; ownership is checked on document reads, processing, and review.

## Limits

- The extractor does not validate extracted amounts against an external statement or tax-credit source.
- Review supports whole-candidate confirmation or rejection, not per-field editing.
- Uploaded files currently use local temporary storage. Production use requires protected persistent storage, an explicit retention policy, and privacy/security review.
- The legacy profile document route returns `410 Gone`; use `/api/v1/documents`.

Automated coverage is in `backend/tests/test_document_extraction.py` and `backend/tests/test_document_api.py`.