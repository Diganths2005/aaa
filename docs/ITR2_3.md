# Return Selection and Future Preparation

TaxWise separates return-family selection from return preparation. The selector in `backend/itr/selection.py` evaluates the saved taxpayer profile and can recommend ITR-1, ITR-2, ITR-3, or ITR-4 with reasons, missing information, and unsupported conditions.

## Current Preparation Boundary

ITR-1 preparation is supported for the AY 2026-27 scope described in [ITR1.md](ITR1.md). TaxWise also generates a limited ITR-3 review summary for resident profiles with non-presumptive business income, non-negative user-entered net profit, and no unsupported schedules. The selector's `preparation_supported` flag is true for these two implemented paths only. ITR-2 and ITR-4 recommendations remain selection outcomes, not preparation capability.

Requests to prepare or download an unsupported form or profile return an explanatory `422` response. TaxWise does not silently prepare ITR-1 for a taxpayer whose profile indicates another form. It does not generate ITR-2 or ITR-4 summaries, or a complete statutory ITR-3 return/PDF; the ITR-3 PDF is a review summary only.

## Limited ITR-3 Review Summary

The current ITR-3 preparation path uses the deterministic engine for supported AY 2026-27 income inputs and accepts non-presumptive business profiles with user-entered, non-negative net profit. It can include supported salary, pension, house-property, other-source, and capital-gain calculations already handled by the engine. The preview and PDF show the business name, nature, gross receipts, entered net profit, tax calculation, tax payments, and support limitations.

This is not a completed ITR-3 filing package. Business books, expense categorization, depreciation, complete statutory schedules, foreign income/assets, speculative income, non-resident cases, business losses, and historical carry-forward schedules remain unsupported. No filing, e-verification, official export, or acknowledgement is generated. Review the summary with a qualified tax professional before filing.

## Future Work

The current preparation scope is:

- ITR-1: supported for the deterministic eligibility rules already implemented.
- ITR-2: supported preparation summary for profiles whose non-business complexity is covered by the TaxWise capital-gains engine. Foreign schedules, speculative income, and persistent loss schedules remain explicitly unsupported.
- ITR-4: supported preparation summary for validated resident presumptive 44AD/44ADA/44AE business entries, subject to the implemented eligibility checks.
- ITR-3: supported review summary for non-negative user-entered business/professional net profit.

The following remain outside the current preparation scope:

- Full statutory ITR-3 books, expense/depreciation calculations, and business-loss history.
- Full foreign-income and foreign-asset schedules.
- Every government-form field and every statutory validation rule beyond the supported profile/calculation model.
- Official government-form export, filing, e-verification, and acknowledgement handling.

The application must not present a review summary as an official filed return.

- Complete statutory ITR-2 and ITR-4 schedules and form-specific validation.
- Full ITR-3 schedules, books, expense/depreciation calculations, and business-loss history.
- Foreign-income and foreign-asset schedules.
- Official government-form export, filing, e-verification, and acknowledgement handling.

The tax engine's supported capital-gain and expanded business-income calculations are calculation capabilities only; they do not complete the corresponding return-preparation workflows. Automated tests cover selected selector and refusal cases, not tax accuracy on a representative population.