<!-- {"assessment_year":"2026-27","status":"active","topic":"new-regime","source_files":["../tax_engine/rules/ay_2026_27/slabs.py","../tax_engine/rules/ay_2026_27/rebates.py","../../docs/TAX_ENGINE.md"]} -->

# New tax regime

The AY 2026-27 new-regime slabs are maintained in the tax-engine rules: nil up to Rs 4 lakh, then 5%, 10%, 15%, 20%, and 25% bands through Rs 24 lakh, followed by 30% above that threshold. The engine applies supported deductions, rebate, surcharge, cess, tax-payment reconciliation, and rounding. Use the deterministic calculation for taxpayer-specific amounts.