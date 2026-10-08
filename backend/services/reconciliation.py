from __future__ import annotations

from decimal import Decimal
from typing import Any

from models.document import UserDocument
from schemas.tax_profile import TaxProfileCreate


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def reconcile_candidate(
    profile: TaxProfileCreate | None,
    candidate: dict[str, Any],
    documents: list[UserDocument] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic contradictions without silently changing data."""
    warnings: list[dict[str, Any]] = []
    if profile and candidate.get("pan_number") and profile.pan_number:
        if candidate["pan_number"].upper() != profile.pan_number.upper():
            warnings.append({
                "field": "pan_number",
                "severity": "high",
                "message": "The uploaded document PAN differs from the confirmed Tax Profile PAN.",
            })

    if profile and candidate.get("salary_income") and profile.salary_income:
        new_salary = _decimal(candidate["salary_income"][0].get("gross_salary"))
        old_salary = _decimal(profile.salary_income[0].gross_salary)
        if new_salary is not None and old_salary is not None and new_salary != old_salary:
            warnings.append({
                "field": "salary_income",
                "severity": "medium",
                "message": f"The uploaded salary ({new_salary}) differs from the confirmed profile salary ({old_salary}).",
            })

    if profile and candidate.get("salary_tds") is not None and profile.salary_income:
        new_tds = _decimal(candidate["salary_tds"])
        old_tds = _decimal(profile.salary_income[0].tds)
        if new_tds is not None and old_tds is not None and old_tds != 0 and new_tds != old_tds:
            warnings.append({
                "field": "salary_tds",
                "severity": "medium",
                "message": f"The uploaded TDS ({new_tds}) differs from the confirmed profile salary TDS ({old_tds}).",
            })

    for document in documents or []:
        if document.status not in {"PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED"}:
            continue
        extracted = (document.processing_result or {}).get("candidates", [])
        for item in extracted:
            if item.get("field") != "pan_number" or not candidate.get("pan_number"):
                continue
            previous = str(item.get("value", "")).upper()
            current = str(candidate["pan_number"]).upper()
            if previous and previous != current:
                warnings.append({
                    "field": "pan_number",
                    "severity": "high",
                    "message": f"The PAN in {document.original_filename} differs from the PAN in the document being confirmed.",
                    "document_id": document.id,
                })
    return warnings
