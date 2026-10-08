<!-- {"assessment_year":"2026-27","status":"active","topic":"salary","source_files":["../tax_engine/income.py","../tax_engine/rules/ay_2026_27/slabs.py","../../docs/TAX_ENGINE.md"]} -->

# Salary income

Salary income is taken from the confirmed profile and aggregated by the deterministic engine. Salary and pension share the engine's standard-deduction cap: Rs 50,000 under the old regime and Rs 75,000 under the new regime. The engine applies the configured regime slabs and rupee-rounding behavior; it does not infer salary from unconfirmed documents.