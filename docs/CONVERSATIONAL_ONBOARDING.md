# Legacy Onboarding APIs

The conversational onboarding wizard is deprecated. The current user workflow is the structured Tax Profile editor, document upload and per-fact review, and the Fact Readiness panel. Backend onboarding endpoints remain available for compatibility with existing clients; new frontend features should use the fact and Tax Profile APIs instead.

The notes below describe the legacy backend workflow only. They are not a recommendation to add the retired assistant UI back to Tax Profile.

## State machine

`OnboardingSession.state` stores `current_field`, completed fields, skipped fields, missing fields, answers, and a pending candidate. The question engine owns order and branching; a future LLM may improve wording and extraction but cannot select the workflow or write values.

The initial order is name, PAN, date of birth, residential status, employment, employer, salary, salary TDS, other income, house property, capital gains, business income, deductions, taxes, bank account, documents, and review. Existing profile values are marked complete when a session resumes.

## Parsing and validation

The deterministic parser understands contextual short answers such as `6 lakh`, `6.5 lakhs`, `₹6,00,000`, `600000`, `No`, and `Yes, rental income`. Amounts are parsed through `Decimal`, rejected when invalid or negative, and validated again through `TaxProfileCreate` before persistence. PAN, dates, and existing bank validators remain authoritative.

## Branching and progress

Negative answers mark optional branches skipped. Positive answers complete the branch decision and allow the engine to continue without asking irrelevant detail questions until those detail questions are introduced. Progress counts structured completed or skipped fields, never chat messages. `GET /api/v1/onboarding/progress` is safe to call when resuming.

## Synchronization and confirmation

`POST /api/v1/onboarding/message` returns the assistant response, current field, candidate values, confirmation requirement, progress, next field, and profile. Candidates are not saved. `POST /api/v1/onboarding/confirm` accepts `confirm` or `reject`; only confirmation persists a candidate and returns the updated profile for the left form. Manual left-panel edits continue through the existing profile `PUT` route, so the next session read sees the latest database value.

New document review persists facts and evidence at extraction time and resolves them through `/api/v1/facts`. The legacy `POST /api/v1/onboarding/document-candidate` and confirmation routes remain only for older clients.

## Sources and safety

The newer fact store records source type, confidence, evidence, assessment year, status, and mapping status. The LLM boundary is explanation and natural-language understanding only: it cannot calculate tax, decide eligibility, bypass validation, or write directly to the database. The deterministic Tax Engine remains the source of truth.

## API

- `POST /api/v1/onboarding/session` creates or resumes the authenticated user's single session.
- `GET /api/v1/onboarding/session` resumes the same session.
- `POST /api/v1/onboarding/message` parses one answer using the current question.
- `POST /api/v1/onboarding/confirm` confirms or rejects the pending candidate.
- `GET /api/v1/onboarding/progress` returns structured progress and missing fields.
- `POST /api/v1/onboarding/document-candidate` queues extracted values for confirmation without automatic profile mutation.