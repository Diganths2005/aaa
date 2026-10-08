# API Reference

The interactive OpenAPI reference is available at `/docs` when the backend is running. The API uses `/api/v1` for authenticated application routes. Tax calculation routes use `/api/tax`; return selection and preparation routes use `/api/itr`.

Authenticated `/api/v1` requests use `Authorization: Bearer <access_token>`, except signup and login. The standalone calculation endpoints accept validated profile data in their request body.

## Authentication

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | Create an account |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain a bearer token |
| `GET` | `/api/v1/auth/me` | Read the current user |
| `POST` | `/api/v1/auth/logout` | Log out |

## Tax Profile and Onboarding

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/tax-profiles/` | Create the current user's profile |
| `GET` | `/api/v1/tax-profiles/current` | Read the current user's profile |
| `GET` | `/api/v1/tax-profiles/{profile_id}` | Read an owned profile |
| `PUT` | `/api/v1/tax-profiles/{profile_id}` | Update an owned profile |
| `DELETE` | `/api/v1/tax-profiles/{profile_id}` | Delete an owned profile |
| `POST` | `/api/v1/onboarding/session` | Start or resume onboarding |
| `GET` | `/api/v1/onboarding/session` | Read onboarding state |
| `GET` | `/api/v1/onboarding/progress` | Read completion progress |
| `POST` | `/api/v1/onboarding/message` | Submit a structured onboarding answer |
| `POST` | `/api/v1/onboarding/confirm` | Confirm or reject a pending profile candidate |

The legacy `POST /api/v1/tax-profiles/{profile_id}/documents` endpoint is retired and returns `410 Gone`.

## Tax Calculation

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/tax/calculate` | Calculate one regime from `{ "profile": ..., "regime": "old" | "new" }` |
| `POST` | `/api/tax/compare-regimes` | Calculate both regimes and return the deterministic recommendation |
| `GET` | `/api/v1/deductions/discovery?regime=old` | List deduction discovery results for the current profile |
| `GET` | `/api/v1/deductions/summary?regime=old` | Read the current deduction summary |
| `POST` | `/api/v1/what-if/simulate` | Calculate a non-persisted profile scenario |
| `POST` | `/api/v1/what-if/apply` | Apply a confirmed what-if change |

Calculation responses include Decimal-derived totals, regime inputs, tax stages, slab contributions, rebate, surcharge, cess, taxes paid, refund, and balance payable. Unsupported inputs return a structured `422` tax-engine error. The engine supports AY 2026-27 only.

## Chat

`POST /api/v1/chat` accepts `{ "message": "..." }` and returns `{ "answer": "...", "sources": [...], "mode": "..." }`.

The route retrieves matching assessment-year notes and, for questions explicitly about uploaded tax documents, passages from the current user's processed documents. Sources identify the note path or document filename and page. The deterministic engine remains the source of calculation facts. A configured GitHub Models provider may explain answers grounded in shared notes; private uploaded passages are never sent to it. Unsupported tax questions with no relevant source receive an explicit out-of-scope answer.

## Documents

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/documents/` | Register document metadata only (`202 Accepted`) |
| `POST` | `/api/v1/documents/upload` | Upload PDF/Excel, max 10 MB (`202 Accepted`) |
| `POST` | `/api/v1/documents/{document_id}/process` | Extract candidate fields for review |
| `POST` | `/api/v1/onboarding/document-candidate` | Stage candidate values for an owned pending document |
| `POST` | `/api/v1/onboarding/confirm` | Confirm or reject staged values |
| `GET` | `/api/v1/documents/` | List the current user's documents |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete an owned document and its temporary file |

Processing returns extracted candidates and onboarding-compatible values and indexes passages for private chat retrieval. Extraction does not update the profile. Confirmation validates and merges values; rejection leaves the profile unchanged and removes that document from search. Only the owner can retrieve a processed document; deletion removes its indexed passages and temporary file. Scanned PDF OCR requires the Tesseract executable to be installed on the backend host.

## Return Selection and Preparation

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/itr/eligibility` | Check the ITR-1 preparation conditions |
| `GET` | `/api/itr/selection` | Return the selected family, reasons, and `preparation_supported` flag |
| `GET` | `/api/itr/current` | Build the current supported preparation response |
| `POST` | `/api/itr/prepare` | Prepare the selected supported form and regime |
| `POST` | `/api/itr/recalculate` | Recalculate preparation from the saved profile |
| `POST` | `/api/itr/ask` | Explain a preparation result using its calculation facts |
| `POST` | `/api/itr/pdf` | Download the preparation review PDF |

Selection may identify ITR-2, ITR-3, or ITR-4. ITR-1 preparation and a constrained ITR-3 business-income review summary are supported. The ITR-3 path is limited to resident, non-presumptive profiles with non-negative user-entered net profit and no unsupported schedules; it does not generate complete books, depreciation, or statutory schedules. ITR-2, ITR-4, and unsupported ITR-3 profiles return `422` with an explanation. Generated PDFs are review summaries, not official filing forms or submissions.

## Errors and Data Handling

- `401` indicates missing or invalid authentication on protected routes.
- `404` is returned for missing resources and documents not owned by the current user.
- `413` indicates a document exceeds 10 MB; `415` indicates an unsupported file type.
- `422` indicates request validation, extraction, unsupported return preparation, or tax-engine failure.

Profile responses mask PAN and bank-account numbers. Document bytes currently use local temporary storage; production deployment requires a protected persistent storage design and retention policy.