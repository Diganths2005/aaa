# Deterministic Tax Engine

The Python tax engine is the source of truth for numerical tax calculations. It uses `Decimal`, assessment-year rule modules, validated profile inputs, and centralized rupee rounding. The active rules cover AY 2026-27 (FY 2025-26). The engine does not file returns or rely on an AI model for calculations.

## Calculation Flow

```text
Confirmed Tax Profile
  -> income aggregation and standard deduction
  -> supported deductions
  -> ordinary taxable income and applicable slabs
  -> supported capital-gain tax, where present
  -> rebate -> surcharge -> cess
  -> taxes paid -> refund or balance payable
```

The returned result includes gross total income, deductions, taxable income, ordinary taxable income, capital-gain tax, slab contributions, tax before and after rebate, rebate, surcharge, cess, final liability, tax paid by type, refund, and payable. `slab_calculation` describes the ordinary-income bands; supported special-rate capital-gain transactions are reported separately.

## Supported Calculation Inputs

- Salary, pension, supported other-source income, and supported house-property scenarios.
- Explicit old/new regime deduction allowlists and validated deduction facts, including the implemented 80C, 80CCD, 80D, 80TTA, 80TTB, 80DD, 80DDB, 80EE/80EEA, 80G, 80GG, and education-loan-interest paths.
- Capital-gain transactions for `listed_equity_share`, `equity_oriented_mutual_fund`, `other_security`, `immovable_property`, and `gold_or_other`. Required dates, costs, quantities, listing/STT facts, and grandfathered FMV are validated where applicable. The implementation applies its current-year loss set-off and special-rate rules from `backend/tax_engine/rules/ay_2026_27/capital_gains.py`.
- User-entered business/professional net profit only through the expanded calculation path. The engine does not derive business profit from books or prepare business schedules; negative business income is rejected.

Foreign income and foreign-asset schedules are rejected. Unsupported assets, missing transaction facts, missing deduction facts, and unsupported assessment years return structured errors instead of guessed values.

## AY 2026-27 Rules

New-regime slabs: nil up to Rs 4,00,000; then 5%, 10%, 15%, 20%, and 25% bands through Rs 24,00,000; 30% above Rs 24,00,000.

Old-regime slabs for individuals: nil up to Rs 2,50,000, then 5% to Rs 5,00,000, 20% to Rs 10,00,000, and 30% above. Resident senior and super-senior age categories use the configured higher nil-slab thresholds. Age is derived at 31 March 2026 when date of birth is available.

Salary and pension share one standard-deduction cap: Rs 50,000 under the old regime and Rs 75,000 under the new regime. The engine applies its implemented section 87A rebate, surcharge and marginal relief, and 4% health and education cess. The rebate calculation applies to ordinary tax as implemented; special-rate capital-gain tax is handled separately.

House-property calculations apply the documented 30% deduction to let-out/deemed-let-out property, validate self-occupied interest facts and limits, and apply the implemented old-regime Rs 2 lakh inter-head loss set-off. The new regime does not set off a current house-property loss against other heads.

## API

- `POST /api/tax/calculate` accepts `{ "profile": <TaxProfileCreate>, "regime": "old" | "new" }` for the standard calculation path.
- `POST /api/tax/compare-regimes` accepts a profile and optional `allow_expanded_income` query flag; it returns both calculations, the lower-liability recommendation, and estimated saving.

Equal liabilities return `recommended_regime = "equal"`. Return-form selection is a separate service. ITR-1 preparation and a limited ITR-3 business-income review summary are supported. Capital-gain or expanded business-income calculation does not imply complete statutory schedule preparation; ITR-2/4 preparation and full ITR-3 schedules remain unsupported.

## Versioning and Sources

Rule constants live under `backend/tax_engine/rules/ay_2026_27/`. New assessment years must use separately reviewed rule packages and knowledge notes rather than mutating existing constants.

Sources consulted by the project include:

- [Union Budget 2025-26, Budget Speech, Ministry of Finance](https://www.indiabudget.gov.in/doc/budget_speech.pdf), for proposed personal-tax slabs, rebate, and marginal relief.
- [Income Tax Department, Salaried Individuals for AY 2026-27](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1).
- [Income Tax Department, AY 2026-27 individual return guidance](https://www.incometax.gov.in/iec/foportal/help/individual-business-profession), for supported deduction and house-property conditions.
- [Income Tax Department, Section 80G FAQs](https://www.incometax.gov.in/iec/foportal/sites/default/files/2026-03/FAQs_80G%20Section%20mentioned%20%28final%29%20to%20upload.pdf), for adjusted-total-income and qualifying-limit calculations.

These references and tests require review against current law before any production use. Automated tests cover selected cases; they do not establish overall tax accuracy.

## Limitations

- Only AY 2026-27 is implemented.
- Capital-gain and expanded business calculations are limited to implemented transaction/input rules; they are not full statutory schedules or a complete return-preparation flow.
- Foreign schedules, persistent loss-history management, and government or bank integrations are not implemented.
- The engine's `house_property_loss_carried_forward` is a current-return calculation only; no persistent loss ledger is maintained.
- No independent multi-case salary-reference comparison is included in this repository.