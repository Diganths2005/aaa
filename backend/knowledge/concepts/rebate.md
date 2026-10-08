<!-- {"assessment_year":"2026-27","status":"active","topic":"rebate","source_files":["../tax_engine/rebates.py","../tax_engine/rules/ay_2026_27/rebates.py","../../docs/TAX_ENGINE.md"]} -->

# Rebate

The engine calculates the supported section 87A rebate from taxable income, regime, and residential status. Special-rate income is excluded from the rebate calculation. The returned `rebate` field is the verified amount; this knowledge note does not calculate or promise an additional rebate.