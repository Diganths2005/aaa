# Document Intelligence Architecture

Document intelligence is an optional extension to the existing TaxWise workflow. A user can complete a tax profile, calculate tax, and continue toward ITR filing without creating a document record.

## Boundaries

```text
Optional PDF intake
        |
        v
DocumentProcessor: extract -> OCR -> clean -> classify -> chunk
        |
        +--> user confirmation gate --> TaxProfile update (future)
        |
        +--> EmbeddingStore (future)
                    |
Question --> KnowledgeRetriever --> official AY knowledge + user's documents
                                      |
                                      v
                              CopilotAnswerer (future)
                                      |
                                      v
                        explanation with source references
```

The deterministic tax engine remains the only source of truth for taxable income, deductions, tax, rebate, surcharge, cess, refund, and payable amount. A future copilot receives those results as read-only context and cannot calculate or overwrite them.

## Data model

`user_documents` stores metadata and processing state separately from `tax_profiles`:

- `user_id` is required and is used on every read and delete query.
- `document_type`, filename, assessment year, status, page count, and processing result are tracked independently.
- `storage_key` is reserved for an encrypted object-storage adapter; raw PDF content is not stored in application logs.
- `processing_result` is provisional until the user confirms, edits, or rejects extracted fields.

The initial API registers metadata only. PDF storage, extraction, OCR, embeddings, and LLM providers are intentionally adapter points rather than fake implementations.

## Knowledge separation

Official tax material must be indexed under an assessment-year namespace, for example `knowledge/ay_2026_27/`. Each indexed chunk carries its source, section, assessment year, and provenance. User-document chunks are stored in a separate tenant scope and are always filtered by the authenticated user ID. Retrieval should prefer official material for tax-rule questions while using user documents for personal facts.

## Security requirements

- Require the existing JWT authentication for every document operation.
- Enforce ownership in the database query, not only in the UI.
- Validate PDF type and size at the upload boundary when binary storage is enabled.
- Encrypt stored objects where the storage provider supports it and use opaque storage keys.
- Keep document text and extracted personal data out of logs and error messages.
- Delete the object, chunks, embeddings, and metadata together; support secure deletion policies.
- Never include another user's document IDs in retrieval candidates or copilot context.

## Processing and confirmation contract

`backend/services/document_processing.py` defines the future processor and embedding-store boundaries. Processing should return page-aware chunks and extracted fields with `requires_confirmation=True`. The UI must show extracted information and require Confirm, Edit, or Reject before any profile mutation. No processor may write directly to `TaxProfile`.

`backend/services/rag.py` defines retrieval filters and source-aware context. The required `user_id` filter and optional assessment-year/document filters make tenant isolation and year separation explicit at the interface boundary.

## API surface

- `POST /api/v1/documents`: register optional document metadata; returns `202` with `pending` status.
- `GET /api/v1/documents`: list only the authenticated user's documents.
- `DELETE /api/v1/documents/{document_id}`: delete only the authenticated user's document metadata; future storage adapters must delete associated content too.
- Future: multipart upload, processing status, extracted-field review, confirmation, and source-aware copilot endpoints.
