# ITR-1 Preparation

TaxWise supports a preparation-only demonstration for AY 2026-27. It does not file a return, submit to the Income Tax Department, e-verify, or create an acknowledgement number.

## Supported scope

The deterministic eligibility service currently accepts resident individuals with salary or pension income, supported other-source income, supported house-property scenarios, supported deductions, tax payments, and optional refund bank details. It rejects foreign income/assets, business or professional income, speculative income, unlisted equity, capital gains, and non-resident profiles for this demo.

Eligibility is computed by `backend/itr/service.py`; the assistant cannot decide it. AY 2026-27 rules are the only active assessment-year rules. The implemented scope is based on the Income Tax Department's ITR-1 filing guidance and instructions for AY 2026-27; it is a preparation demo and requires professional review before filing.

## Tax Engine integration

The ITR mapper calls the existing `calculate_tax` function and maps its `TaxCalculationResult` into the preparation response. It does not duplicate slabs, deductions, rebate, surcharge, cess, tax-payment reconciliation, refund, or payable calculations. Editing the Tax Profile and selecting Recalculate runs that same engine again.

## Preview and assistant

The preview presents taxpayer details, income, deductions, taxes paid, tax computation, refund/payable, and masked bank information. The right-side assistant answers from the current preparation response. It can explain tax, taxable income, deductions, TDS, refund, and supported reduction options, but cannot change calculated values.

## PDF export

`POST /api/itr/pdf` generates a real ReportLab PDF containing the current preparation data, masked PAN/bank details, timestamp, and a clear TaxWise review disclaimer. It is explicitly not an Income Tax Department acknowledgement, ITR-V, proof of filing, or submission.

## Limitations

- Only AY 2026-27 and ITR-1 preparation are supported.
- Capital gains, business income, foreign income/assets, ITD submission, e-verification, OCR, RAG, and final ITR filing are not implemented.
- Bank details are displayed masked; the current demo does not submit them anywhere.
- The source references are documentation-level references; official rules should be revalidated before production use.