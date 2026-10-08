#!/bin/bash
set -euo pipefail

printf '%s\n' \
  'TaxWise: AI-assisted tax preparation' \
  '' \
  'Implemented:' \
  '  - Next.js/TypeScript frontend and FastAPI backend' \
  '  - Authenticated profile and onboarding workflows' \
  '  - Deterministic AY 2026-27 tax calculations and regime comparison' \
  '  - Structured tax knowledge notes connected to chat' \
  '  - PDF/Excel extraction with explicit candidate review' \
  '  - General return selection and ITR-1 preparation with review PDF' \
  '' \
  'Not implemented:' \
  '  - ITR-2/3/4 preparation' \
  '  - Government filing, e-verification, or acknowledgements' \
  '  - Complete business or foreign-income schedules' \
  '  - Production document storage and retention controls' \
  '' \
  'Run backend tests: cd backend && python -m pytest' \
  'Frontend checks: cd frontend && npm run type-check && npm run build' \
  '' \
  'See README.md and docs/ for supported scope and setup.'