# Document Processing and Tax Knowledge

Document extraction and chat retrieval are separate workflows. Chat can retrieve checked-in, assessment-year-scoped tax notes and passages from the authenticated user's processed documents. Uploaded material is never shared across users.

## Document Workflow

```text
Authenticated PDF / Excel upload
        -> local temporary file storage
        -> PDF text extraction / optional OCR / workbook text extraction
        -> field candidates
        -> user review on the Documents page
        -> Confirm or Reject
        -> confirmed values update the Tax Profile
```

The profile is not changed during upload or extraction. Confirmed fields are validated by the profile schema before persistence. Rejected candidates leave the profile unchanged. The document record stores `CONFIRMED` or `REJECTED` so reviewed candidates are not presented again as pending.

### Implemented behavior

- `POST /api/v1/documents/upload` accepts PDF, `.xlsx`, and `.xlsm` files up to 10 MB for the authenticated user.
- `POST /api/v1/documents/{document_id}/process` extracts page text, applies supported labels, parses monetary candidates as `Decimal`, and stores candidate values for review.
- PDF text is extracted with `pypdf`. If the document has no extractable text, the service attempts OCR with PyMuPDF and `pytesseract`.
- Excel workbooks are read with `openpyxl` and passed through the same field-candidate rules.
- The `TaxWise Profile Import` sheet in `TaxWise_App_Import_Template.xlsx` maps scalar fields to the Tax Profile schema; each collection tab uses one row per profile record. Only populated cells are imported. Unknown or duplicate field names and values that fail schema validation are rejected. The older `TaxWise Import Data` label/value sheet remains supported for backward compatibility.
- The workbook covers the TaxWise profile's scalar fields and record collections: salary, pension, house property, other income, capital gains, business income, foreign income/assets, investments, deductions, tax payments, bank accounts, and document metadata. It imports TaxWise profile data, not a complete official ITR-3 return or every government return schedule.
- The document review screen lets the user edit the imported profile JSON before confirming it. Values are schema-validated and saved only after explicit confirmation. Existing profile fields not supplied in the workbook are retained; populated collection tabs replace that collection when confirmed.
- The workbook includes sensitive identifiers and financial information. Keep the completed file private and review its extracted data before confirming.
- `/documents` lists only the authenticated user's records. Deletion is owner-scoped and removes the temporary file.
- The onboarding candidate endpoint checks ownership and pending status when given a document ID; confirmation and rejection update that document's status.
- Extracted page text is split into bounded overlapping passages and stored separately for private chat retrieval. Queries are scoped to the authenticated owner and assessment year; rejected, failed, deleted, and unprocessed documents are excluded. Rejecting or deleting a document removes its indexed passages.
- Document lookup answers quote matching passages and cite the filename and page. Private passages are not sent to a hosted language-model provider, and extracted document values do not affect tax calculations until confirmed in the profile.
- The shared reference corpus consists of checked-in, reviewed, assessment-year-scoped knowledge notes. User uploads are never promoted into the shared corpus.

### Limits and operational requirements

- OCR requires a working Tesseract executable on the server. Installing the Python `pytesseract` package alone is insufficient. If OCR cannot run, the API returns `DOCUMENT_REQUIRES_OCR`; users can upload a text-based document or enter values manually.
- Field detection for ordinary documents uses explicit text-label patterns. It is not a general-purpose document classifier, and extracted candidates may be incomplete or wrong. The structured profile workbook instead relies on exact schema field names.
- Review confirms or rejects the mapped candidate set as a whole; edits are available before confirmation, not as separate per-field save actions.
- Files are stored under the operating system's temporary directory. Replace this with protected persistent storage and define retention/encryption before production use.
- Upload processing is synchronous. Background jobs, document viewing, OCR quality measurement, and automatic document-to-profile reconciliation are not implemented.

## Structured Tax Knowledge Base

Notes live in `backend/knowledge/` and declare `assessment_year`, `status`, `topic`, and source-file metadata in a JSON comment. Active notes are scoped to AY 2026-27 and link their statements to existing engine rules and project references. A new year should use a separate note set after its rules and references are reviewed.

`backend/services/knowledge.py` chunks active Markdown sections and ranks them using local BM25 and TF-IDF cosine similarity. Processed private document passages use the same hybrid ranking, with owner and assessment-year filters applied before scoring. Retrieval does not require a hosted embedding service or vector database. Shared tax references are curated and version-controlled; new assessment years require reviewed notes and matching engine support.

For shared-note answers, `/api/v1/chat` may use the configured hosted language model with retrieved public notes and verified calculation facts. Private-document lookups remain deterministic and quote retrieved passages locally; they are not sent to a hosted model. Tax questions without a relevant shared note or explicitly requested personal-document passage receive an out-of-scope answer.

The calculation engine remains authoritative for taxable income, tax, rebate, surcharge, cess, taxes paid, refund, and payable amount. Knowledge notes explain existing rules; they do not compute or override amounts.

## Tests

- `backend/tests/test_document_extraction.py` covers PDF/Excel field extraction, workbook schema validation, money parsing, and OCR fallback behavior.
- `backend/tests/test_document_api.py` covers upload, ownership, confirmation, rejection, and profile effects, including the full-profile workbook.
- `backend/tests/test_knowledge.py` covers assessment-year-scoped hybrid retrieval and passage chunking.
- `backend/tests/test_document_api.py` covers upload ownership, private retrieval, and index cleanup on deletion.
- `backend/tests/test_chat_api.py` covers chat sources, unsupported questions, and deterministic fallback on provider or knowledge lookup failure.