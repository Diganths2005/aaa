<!-- {"assessment_year":"2026-27","status":"active","topic":"deductions","source_files":["../tax_engine/deductions.py","../../docs/TAX_ENGINE.md"]} -->

# Deductions

Deduction eligibility is calculated from section-specific profile facts using explicit old- and new-regime allowlists. Implemented sections include 80C, 80CCD(1B), 80CCD(2), 80D, 80TTA, 80TTB, and validated 80DD, 80DDB, 80EE, 80EEA, 80G, 80GG, and education-loan interest paths. Some claims require evidence or eligibility details; missing facts produce a structured engine error rather than an assumed deduction. The engine's current rules and validation are authoritative.