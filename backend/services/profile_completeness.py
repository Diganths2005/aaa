from __future__ import annotations

from typing import Any

from schemas.tax_profile import TaxProfileCreate


REQUIRED_BASE_FIELDS = ("pan_number", "date_of_birth", "residential_status", "employment_type")


def _has_salary(profile: TaxProfileCreate) -> bool:
    return bool(profile.salary_income or profile.pension_income or profile.business_income)


def profile_completeness(profile: TaxProfileCreate | None) -> dict[str, Any]:
    if profile is None:
        return {
            "complete": False,
            "missing_fields": list(REQUIRED_BASE_FIELDS) + ["income_source"],
            "completion_ratio": 0.0,
        }

    missing: list[str] = []
    for field in REQUIRED_BASE_FIELDS:
        value = getattr(profile, field, None)
        if field == "residential_status" and value == "resident":
            # "resident" is the schema default; without explicit evidence it is
            # safer to require confirmation than to silently assume it.
            missing.append(field)
        elif field == "employment_type" and value == "salaried" and not profile.salary_income:
            missing.append(field)
        elif not value:
            missing.append(field)

    if not _has_salary(profile):
        missing.append("income_source")

    if profile.employment_type == "salaried":
        if not profile.employer_name and profile.salary_income:
            missing.append("employer_name")

    # These are conditional facts needed to avoid silently treating absent
    # information as a confirmed "no".
    if profile.salary_income and not profile.taxes_paid:
        missing.append("taxes_paid_or_confirmed_none")

    if profile.has_business_income and not profile.business_income:
        missing.append("business_income_details")

    if profile.has_foreign_income or profile.has_foreign_assets:
        if not profile.foreign_income_assets:
            missing.append("foreign_income_asset_details")

    if profile.capital_gains and any(
        item.sale_consideration is None or item.acquisition_cost is None
        for item in profile.capital_gains
    ):
        missing.append("capital_gain_transaction_details")

    total = len(REQUIRED_BASE_FIELDS) + 1
    ratio = max(0.0, min(1.0, (total - min(len(missing), total)) / total))
    return {
        "complete": not missing,
        "missing_fields": list(dict.fromkeys(missing)),
        "completion_ratio": round(ratio, 3),
    }
