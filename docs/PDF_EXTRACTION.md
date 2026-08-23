# PDF Tax Data Extraction

TaxWise supports optional text-based tax PDF processing for the presentation flow. Uploading a document never changes the Tax Profile automatically.

## Flow

```text
PDF upload -> UPLOADED -> PROCESSING -> pypdf text extraction
  -> field candidates -> REQUIRES_CONFIRMATION
  -> onboarding document candidate -> Confirm -> Tax Profile
```

`POST /api/v1/documents/upload` accepts an authenticated PDF up to 10 MB and stores its bytes behind an opaque temporary storage key. `POST /api/v1/documents/{document_id}/process` reads that file using `pypdf`, extracts each page, and applies generic labels such as Employee Name, PAN, Employer, Gross Salary, TDS Deducted, Section 80C, and Section 80D.

Currency values are parsed with `Decimal`, supporting rupee-marked/grouped values and lakh notation. Each candidate contains field, value, source, confidence, page, and confirmation requirement. The processing result also contains an onboarding-compatible candidate payload.

The existing onboarding confirmation API is the only profile write path. Confirmed candidates update the existing Tax Profile and advance its persisted onboarding state. Rejected candidates do not update the profile. Future conflict review can compare document candidates with current profile values before confirmation.

Textless or scanned PDFs return `DOCUMENT_REQUIRES_OCR`; OCR is deliberately not implemented. Invalid files, unsupported types, oversized files, and extraction failures return explicit errors without blocking manual profile entry.

Document access requires JWT authentication and every query is scoped by authenticated `user_id`. Raw extracted text is not returned in logs; stored document bytes are behind an opaque storage key and must be replaced with encrypted object storage in production.