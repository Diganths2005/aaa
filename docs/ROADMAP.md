# Roadmap

This roadmap separates active code paths from work that still needs implementation. The current application is an AI-assisted tax-preparation framework, not a filing service.

## Implemented

- JWT authentication and Tax Profile persistence, with the conversational onboarding UI deprecated and its API retained for compatibility.
- Deterministic AY 2026-27 tax calculation, old/new regime comparison, supported deduction and capital-gain calculations, and structured calculation breakdowns.
- Local assessment-year-versioned tax notes connected to chat through hybrid BM25 and TF-IDF retrieval. Chat receives verified calculation facts; unsupported questions without matching knowledge are declined.
- PDF/Excel upload, extraction, optional OCR, private per-user passage retrieval, and an owner-scoped fact/evidence store with per-field review, conflict resolution, readiness reporting, and a Tax Profile compatibility projection.
- General return-family selection with reasons and unsupported conditions.
- ITR-1 eligibility, preparation summary, recalculation, result explanation, and review PDF.
- Limited ITR-3 business-income summary for supported non-presumptive profiles, using user-entered non-negative net profit and the shared tax engine.

## Incomplete or Not Implemented

- ITR-2 and ITR-4 preparation, plus completion of ITR-3 statutory schedules. Current ITR-3 output is a review summary, not a completed return.
- Complete statutory schedules, official return export, e-filing, e-verification, acknowledgements, and government/bank integrations.
- Foreign schedules, persistent loss-history management, and full business books/expense/depreciation computation.
- Complete ITR-specific dynamic fact requirements/readiness rules, OCR setup automation, protected persistent file storage, and retention controls.
- Knowledge-note coverage beyond current project rules, reviewed external rule-source synchronization, and additional assessment years.
- Production hardening beyond the current baseline remains: secrets management, rate limiting, audit logging, encryption/retention policy, monitoring, and formal security/compliance review.

## Validation

Run the backend suite and frontend checks after changes:

```powershell
cd backend
python -m pytest
cd ..\frontend
npm run type-check
npm run build
```

These tests exercise selected functionality; they do not prove universal tax accuracy, statutory completeness, or production readiness.