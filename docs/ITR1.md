# ITR-1 Preparation

TaxWise supports a preparation-only demonstration for AY 2026-27. It does not file a return, submit to the Income Tax Department, e-verify, or create an acknowledgement number.

Return selection can identify other return families. TaxWise also supports a constrained ITR-3 business-income review summary; this does not change the ITR-1 eligibility rules or imply complete preparation of other statutory forms. Unsupported selections are not converted into ITR-1 preparation.

## Supported scope

The deterministic eligibility service currently accepts resident individuals with salary or pension income, supported other-source income, supported house-property scenarios, supported deductions, tax payments, and optional refund bank details. It rejects foreign income/assets, business or professional income, speculative income, unlisted equity, capital gains, and non-resident profiles for this demo.

ITR-1 eligibility is checked by `backend/itr/service.py`; broader family selection is handled by `backend/itr/selection.py`. The assistant cannot choose or override a return form. AY 2026-27 is the only active assessment year. The implementation is a preparation demo and requires professional review before filing.

## Tax Engine integration

The ITR mapper calls the existing `calculate_tax` function and maps its `TaxCalculationResult` into the preparation response. It does not duplicate slabs, deductions, rebate, surcharge, cess, tax-payment reconciliation, refund, or payable calculations. Editing the Tax Profile and selecting Recalculate runs that same engine again.

## Preview and assistant

The preview presents taxpayer details, income, deductions, taxes paid, tax computation, refund/payable, and masked bank information. The right-side assistant answers from the current preparation response. It can explain tax, taxable income, deductions, TDS, refund, and supported reduction options, but cannot change calculated values.

## PDF export

`POST /api/itr/pdf` generates a real ReportLab PDF containing the current preparation data, masked PAN/bank details, timestamp, and a clear TaxWise review disclaimer. It is explicitly not an Income Tax Department acknowledgement, ITR-V, proof of filing, or submission.

## Limitations

- Only AY 2026-27 is supported. This document describes the ITR-1 preparation scope.
- Capital gains, business income, foreign schedules, ITD submission, e-verification, and final ITR filing are not included in this ITR-1 workflow. TaxWise has a limited ITR-3 review-summary workflow, but does not prepare full ITR-3 statutory schedules. ITR-2 and ITR-4 preparation remain unsupported; see [Return Selection and Future Preparation](ITR2_3.md).
- Bank details are displayed masked; the current demo does not submit them anywhere.
- The source references are documentation-level references; official rules should be revalidated before production use.