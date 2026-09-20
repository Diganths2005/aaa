from dataclasses import dataclass
from typing import List, Optional

from schemas.tax_profile import TaxProfileCreate


@dataclass(frozen=True)
class ITRSelection:
    recommended_itr: Optional[str]
    eligible: bool
    assessment_year: str
    reasons: List[str]
    missing_information: List[str]
    unsupported_conditions: List[str]


def select_itr(profile: TaxProfileCreate) -> ITRSelection:
    reasons: List[str] = []
    missing: List[str] = []
    unsupported: List[str] = []

    year_supported = profile.assessment_year == "2026-27"
    if not year_supported:
        reasons.append("Only assessment year 2026-27 is supported.")
    has_any_income = bool(
        profile.salary_income
        or profile.pension_income
        or profile.other_income
        or profile.house_properties
        or profile.capital_gains
        or profile.business_income
    )
    if not has_any_income:
        missing.append("Add at least one supported income source.")
    if profile.has_speculative_income:
        unsupported.append("Speculative income schedules are not supported.")
    if profile.has_carry_forward_loss:
        unsupported.append("Persistent carry-forward loss schedules are not supported.")
    if profile.has_unlisted_equity:
        unsupported.append("Unlisted-equity return schedules are not supported.")

    has_business = bool(profile.business_income or profile.has_business_income)
    has_capital_gains = bool(profile.capital_gains)
    has_foreign = bool(profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income)

    if has_business:
        if not profile.business_income:
            missing.append("Add business or professional income details.")
        presumptive = bool(profile.business_income) and all(item.presumptive_section for item in profile.business_income)
        if presumptive and not has_capital_gains and not has_foreign and not profile.has_speculative_income and not profile.has_unlisted_equity:
            return ITRSelection("ITR-4", year_supported and not missing and not unsupported, profile.assessment_year, reasons + ["Presumptive business or professional income is present."], missing, unsupported)
        return ITRSelection("ITR-3", year_supported and not missing and not unsupported, profile.assessment_year, reasons + ["Business or professional income requires ITR-3."], missing, unsupported)

    if has_capital_gains or has_foreign:
        if has_foreign:
            reasons.append("Foreign income or assets require ITR-2 within the supported scope.")
            unsupported.append("Foreign schedules are not yet supported for preparation.")
        if has_capital_gains:
            reasons.append("Capital-gain transactions require ITR-2 within the supported scope.")
        return ITRSelection("ITR-2", year_supported and not missing and not unsupported, profile.assessment_year, reasons, missing, unsupported)

    if profile.residential_status != "resident":
        reasons.append("Non-resident profiles are outside the supported ITR-1 scope.")
    if not profile.salary_income and not profile.pension_income:
        reasons.append("Salary or pension income is required for ITR-1.")
    return ITRSelection("ITR-1", year_supported and not reasons and not missing and not unsupported, profile.assessment_year, reasons or ["Salary or pension income fits the supported ITR-1 scope."], missing, unsupported)