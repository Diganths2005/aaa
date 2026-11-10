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
    preparation_supported: bool = False


def _capital_gains_itr2_supported(profile: TaxProfileCreate) -> tuple[bool, list[str]]:
    unsupported: list[str] = []
    if profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income:
        unsupported.append("Foreign income and asset schedules require additional ITR-2 implementation and are not yet prepared.")
    if profile.has_speculative_income:
        unsupported.append("Speculative-income schedules are not supported.")
    if profile.has_carry_forward_loss:
        unsupported.append("Persistent carry-forward loss schedules are not supported.")
    return not unsupported, unsupported


def _itr4_supported(profile: TaxProfileCreate) -> tuple[bool, list[str]]:
    unsupported: list[str] = []
    if profile.residential_status != "resident":
        unsupported.append("ITR-4 is limited to resident individuals in this TaxWise workflow.")
    if profile.is_director:
        unsupported.append("Company-director disclosure is outside ITR-4 scope.")
    if profile.has_unlisted_equity:
        unsupported.append("Unlisted equity makes the profile ineligible for ITR-4.")
    if profile.has_foreign_income or profile.has_foreign_assets or profile.foreign_income_assets:
        unsupported.append("Foreign income/assets are outside ITR-4 scope.")
    if profile.has_speculative_income:
        unsupported.append("Speculative income is outside ITR-4 scope.")
    if profile.has_carry_forward_loss:
        unsupported.append("Carry-forward loss schedules are outside ITR-4 scope.")
    if not profile.business_income:
        unsupported.append("Presumptive business/professional income details are required.")
    if any(not item.presumptive_section for item in profile.business_income):
        unsupported.append("Every business/professional entry must use a supported presumptive section: 44AD, 44ADA or 44AE.")
    if any(item.net_profit_or_loss < 0 for item in profile.business_income):
        unsupported.append("Business losses are outside the supported ITR-4 workflow.")
    if len(profile.house_properties) > 2:
        unsupported.append("ITR-4 preparation supports at most two house properties.")
    return not unsupported, unsupported


def select_itr(profile: TaxProfileCreate) -> ITRSelection:
    reasons: List[str] = []
    missing: List[str] = []
    unsupported: List[str] = []

    year_supported = profile.assessment_year == "2026-27"
    if not year_supported:
        reasons.append("Only assessment year 2026-27 is supported.")
    has_any_income = bool(profile.salary_income or profile.pension_income or profile.other_income or profile.house_properties or profile.capital_gains or profile.business_income)
    if not has_any_income:
        missing.append("Add at least one supported income source.")
    if profile.has_speculative_income:
        unsupported.append("Speculative income schedules are not supported.")
    if profile.has_carry_forward_loss:
        unsupported.append("Persistent carry-forward loss schedules are not supported.")

    has_business = bool(profile.business_income or profile.has_business_income)
    has_capital_gains = bool(profile.capital_gains)
    has_foreign = bool(profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income)

    if has_business:
        if not profile.business_income:
            missing.append("Add business or professional income details.")
        presumptive = bool(profile.business_income) and all(item.presumptive_section for item in profile.business_income)
        if presumptive and not has_capital_gains and not has_foreign and not profile.has_speculative_income and not profile.has_unlisted_equity:
            itr4_ok, itr4_unsupported = _itr4_supported(profile)
            return ITRSelection("ITR-4", year_supported and not missing and itr4_ok, profile.assessment_year, reasons + ["Presumptive business or professional income is present."], missing, itr4_unsupported, itr4_ok)
        if profile.residential_status != "resident":
            unsupported.append("Non-resident ITR-3 schedules are not prepared by this workflow.")
        if profile.is_director:
            unsupported.append("Company-director disclosure schedules are not prepared by this workflow.")
        if has_foreign:
            unsupported.append("Foreign income and asset schedules are not prepared by this workflow.")
        if any(item.net_profit_or_loss < 0 for item in profile.business_income):
            unsupported.append("Business losses and their statutory schedules are not supported.")
        if any(item.presumptive_section for item in profile.business_income):
            unsupported.append("Mixed/non-presumptive business income requires the ITR-3 path.")
        eligible = year_supported and not missing and not unsupported
        return ITRSelection("ITR-3", eligible, profile.assessment_year, reasons + ["Business or professional income requires ITR-3."], missing, unsupported, eligible)

    if has_capital_gains or has_foreign:
        if has_foreign:
            reasons.append("Foreign income or assets require ITR-2.")
        if has_capital_gains:
            reasons.append("Capital-gain transactions require ITR-2.")
        itr2_ok, itr2_unsupported = _capital_gains_itr2_supported(profile)
        return ITRSelection("ITR-2", year_supported and not missing and itr2_ok, profile.assessment_year, reasons, missing, itr2_unsupported, itr2_ok)

    if profile.residential_status != "resident":
        reasons.append("Non-resident profiles are outside the supported ITR-1 scope.")
    if not profile.salary_income and not profile.pension_income:
        reasons.append("Salary or pension income is required for ITR-1.")
    return ITRSelection("ITR-1", year_supported and not reasons and not missing and not unsupported, profile.assessment_year, reasons or ["Salary or pension income fits the supported ITR-1 scope."], missing, unsupported, True)
