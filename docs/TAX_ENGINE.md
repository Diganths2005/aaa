# Tax Engine Phase 2A

TaxWise Phase 2A is a deterministic calculator for individual taxpayers with the ITR-1-compatible income subset for AY 2026-27 (FY 2025-26). It does not choose an ITR, calculate capital gains or business income, generate ITR files, call an LLM, or connect to ITD/bank APIs. Profiles containing those unsupported sections are rejected rather than silently miscalculated.

## Flow

`Tax Profile -> /api/tax/calculate or /api/tax/compare-regimes -> income -> deductions -> slabs -> rebate -> surcharge -> cess -> tax payments`

All currency values use Python `Decimal` and are rounded to whole rupees at the tax stages. Salary and pension, house-property income (including 30% statutory deduction for let-out property), and other sources are aggregated. Standard deduction is AY-specific. Old-regime deductions are applied by section and cap; the new-regime layer currently permits only 80CCD(2).

## AY 2026-27 rules implemented

New regime slabs: up to Rs 4,00,000 nil; Rs 4,00,001-8,00,000 5%; Rs 8,00,001-12,00,000 10%; Rs 12,00,001-16,00,000 15%; Rs 16,00,001-20,00,000 20%; Rs 20,00,001-24,00,000 25%; above Rs 24,00,000 30%.

Old regime slabs for individuals: up to Rs 2,50,000 nil, then Rs 2,50,001-5,00,000 5%, Rs 5,00,001-10,00,000 20%, above Rs 10,00,000 30%. The first nil slab is Rs 3,00,000 for resident senior citizens. Section 87A rebate, surcharge, and 4% health and education cess are separate calculation layers. The new-regime rebate includes the AY 2026-27 marginal-relief treatment above Rs 12,00,000.

## API

`POST /api/tax/calculate` accepts `{ "profile": <TaxProfileCreate>, "regime": "old" | "new" }`.

`POST /api/tax/compare-regimes` accepts `<TaxProfileCreate>` and returns both results, the lower-liability recommendation, and estimated saving. Recommendation is mathematical and contains no AI-generated values.

## Versioning and sources

Rules live under `backend/tax_engine/rules/ay_2026_27/`. A future assessment year gets a new rules package rather than mutating these constants.

Official sources consulted:

- [Union Budget 2025-26, Budget Speech, Ministry of Finance](https://www.indiabudget.gov.in/doc/budget_speech.pdf), proposals for the revised personal income-tax slabs, Rs 12 lakh rebate, and marginal relief.
- [Income Tax Department, Salaried Individuals for AY 2026-27](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1), official return/help material and AY 2026-27 publication context.
- [Income Tax Department, Tax Rates and Computation](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1), official portal reference for return and tax computation guidance.

Tax law can change through notifications and circulars. The rules package and tests must be reviewed before production use or adding another assessment year.
