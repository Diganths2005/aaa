# Tax Engine Phase 2A

TaxWise Phase 2A is a deterministic calculator for individual taxpayers with the ITR-1-compatible income subset for AY 2026-27 (FY 2025-26). It does not choose an ITR, calculate capital gains or business income, generate ITR files, call an LLM, or connect to ITD/bank APIs. Profiles containing those unsupported sections are rejected rather than silently miscalculated.

## Flow

`Tax Profile -> /api/tax/calculate or /api/tax/compare-regimes -> income -> deductions -> slabs -> rebate -> surcharge -> cess -> tax payments`

All currency values use Python `Decimal`; rupee rounding is centralized and applied to statutory tax outputs rather than every input. Salary and pension share one standard-deduction cap: Rs 50,000 in the old regime and Rs 75,000 in the new regime. House-property income preserves the raw result, applies the 30% statutory deduction to let-out/deemed-let-out property, and applies the old-regime Rs 2 lakh inter-head loss set-off separately. The new-regime calculator does not set off house-property loss against other heads.

## AY 2026-27 rules implemented

New regime slabs: up to Rs 4,00,000 nil; Rs 4,00,001-8,00,000 5%; Rs 8,00,001-12,00,000 10%; Rs 12,00,001-16,00,000 15%; Rs 16,00,001-20,00,000 20%; Rs 20,00,001-24,00,000 25%; above Rs 24,00,000 30%.

Old regime slabs for individuals are up to Rs 2,50,000 nil, then 5% to Rs 5,00,000, 20% to Rs 10,00,000, and 30% above. The nil slab is Rs 3,00,000 for resident senior citizens and Rs 5,00,000 for resident super-senior citizens. Age is derived from date of birth on 31 March 2026 where available; non-residents use the individual slabs. Section 87A rebate, surcharge with threshold marginal relief, and 4% health and education cess are separate layers. Special-rate income is excluded from the 87A rebate calculation; the current ITR-1 subset has no special-rate capital-gain input.

The deduction layer has explicit old/new regime allowlists and structured metadata. It calculates 80C, 80CCD(1B), 80CCD(2), 80D (self/family and parents, including parent age), 80TTA, 80TTB, and validated loan/disability/rent/donation paths. 80DD and 80U use fixed statutory amounts (Rs 75,000 or Rs 1,25,000 for severe disability), not user-entered amounts. 80DDB uses actual eligible expenditure after reimbursement and age-based limits. 80CCD(2) uses basic salary plus qualifying dearness allowance, with 14% for the new regime or government employer and 10% for other old-regime employers. 80G qualifying-limit claims derive the 10% limit from engine-calculated adjusted total income; the legacy `qualifying_limit` input is ignored. Sections requiring facts or proof not present in the profile return `INSUFFICIENT_DEDUCTION_DATA`, `INELIGIBLE_DEDUCTION`, or `INVALID_DEDUCTION`; the engine never guesses a deduction from an amount alone.

## API

`POST /api/tax/calculate` accepts `{ "profile": <TaxProfileCreate>, "regime": "old" | "new" }`.

`POST /api/tax/compare-regimes` accepts `<TaxProfileCreate>` and returns both results, the lower-liability recommendation, and estimated saving. Equal liabilities return `recommended_regime = "equal"`. Recommendation is mathematical and contains no AI-generated values. Unsupported capital gains, business income, and foreign income/assets return structured error codes rather than being ignored.

## Versioning and sources

Rules live under `backend/tax_engine/rules/ay_2026_27/`. A future assessment year gets a new rules package rather than mutating these constants.

Official sources consulted:

- [Union Budget 2025-26, Budget Speech, Ministry of Finance](https://www.indiabudget.gov.in/doc/budget_speech.pdf), proposals for the revised personal income-tax slabs, Rs 12 lakh rebate, and marginal relief.
- [Income Tax Department, Salaried Individuals for AY 2026-27](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1), official return/help material and AY 2026-27 publication context.

## Limitations

**Phase 2A is an ITR-1-compatible core tax calculator. Full capital gains, business/professional income and foreign income/assets processing are planned for Phase 2B.** Limited Section 112A treatment, other special-rate income, detailed surcharge marginal-relief edge cases, donation/payment proof eligibility, carry-forward losses, and return filing are not implemented. No AI, ITD submission, bank integration, or ITR generation is included.

House-property `house_property_loss_carried_forward` is a calculated current-return amount only. TaxWise has no persistent loss ledger and does not claim that this amount was stored for a future assessment year. The calculation reports the raw loss, current-year set-off, and current-year carry-forward separately.

Tax law can change through notifications and circulars. The rules package and tests must be reviewed before production use or adding another assessment year.
