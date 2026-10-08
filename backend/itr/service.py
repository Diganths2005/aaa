from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax
from tax_engine.models import TaxCalculationResult
from .selection import ITRSelection, select_itr


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    itr_form: Optional[str]
    assessment_year: str
    reasons: List[str]
    warnings: List[str]


def check_itr1_eligibility(profile: TaxProfileCreate) -> EligibilityResult:
    reasons: List[str] = []
    warnings: List[str] = []
    if profile.assessment_year != "2026-27":
        reasons.append("Only assessment year 2026-27 is supported for this preparation demo.")
    if profile.residential_status != "resident":
        reasons.append("ITR-1 preparation is limited to resident individuals in this demo.")
    if profile.has_business_income or profile.business_income:
        reasons.append("Business or professional income requires a different ITR form.")
    if profile.has_foreign_income or profile.foreign_income_assets:
        reasons.append("Foreign income or assets are outside the supported ITR-1 scope.")
    if profile.capital_gains:
        reasons.append("Capital gains are outside this ITR-1 preparation scope.")
    if profile.has_speculative_income:
        reasons.append("Speculative income requires a different ITR form.")
    if profile.has_unlisted_equity:
        reasons.append("Unlisted equity is outside the supported ITR-1 scope.")
    if not profile.salary_income and not profile.pension_income:
        reasons.append("Salary or pension income is required for this ITR-1 demo.")
    if not profile.bank_accounts:
        warnings.append("Add a bank account before filing; it is needed for refund details.")
    return EligibilityResult(not reasons, "ITR-1" if not reasons else None, profile.assessment_year, reasons, warnings)


def select_return(profile: TaxProfileCreate) -> ITRSelection:
    return select_itr(profile)


def _masked_account(account: Dict[str, Any]) -> Dict[str, Any]:
    number = str(account.get("account_number", ""))
    return {**account, "account_number": f"******{number[-4:]}" if number else ""}


def _calculation_details(calculation: TaxCalculationResult) -> Dict[str, Any]:
    return {
        "ordinary_taxable_income": calculation.ordinary_taxable_income,
        "capital_gains_tax": calculation.capital_gains_tax,
        "tax_after_rebate": calculation.tax_after_rebate,
        "slab_calculation": [step.model_dump(mode="json") for step in calculation.slab_calculation],
    }


def prepare_itr1(profile: TaxProfileCreate, taxpayer_name: str, regime: str = "new") -> Dict[str, Any]:
    eligibility = check_itr1_eligibility(profile)
    if not eligibility.eligible:
        raise ValueError("ITR-1 is not eligible: " + " ".join(eligibility.reasons))
    calculation: TaxCalculationResult = calculate_tax(profile, regime, allow_expanded_income=True)
    return {
        "eligibility": eligibility.__dict__,
        "assessment_year": profile.assessment_year,
        "taxpayer": {
            "name": taxpayer_name,
            "pan": f"{profile.pan_number[:2]}******{profile.pan_number[-2:]}" if profile.pan_number else None,
            "date_of_birth": profile.date_of_birth,
            "address": profile.address,
            "residential_status": profile.residential_status,
        },
        "income": {
            "salary": calculation.income_from_salary,
            "pension": calculation.income_from_pension,
            "house_property": calculation.house_property_income,
            "other_sources": calculation.other_sources_income,
            "gross_total_income": calculation.gross_total_income,
        },
        "deductions": {
            "total": calculation.total_deductions,
            "items": profile.deductions,
        },
        "taxes_paid": {
            "tds": calculation.tds,
            "advance_tax": calculation.advance_tax,
            "self_assessment_tax": calculation.self_assessment_tax,
            "total": calculation.total_tax_paid,
        },
        "calculation": {
            **_calculation_details(calculation),
            "taxable_income": calculation.taxable_income,
            "tax_before_rebate": calculation.tax_before_rebate,
            "tax": calculation.total_tax_liability,
            "rebate": calculation.rebate,
            "surcharge": calculation.surcharge,
            "cess": calculation.cess,
            "total_tax": calculation.total_tax_liability,
            "refund": calculation.refund,
            "payable": calculation.balance_payable,
            "regime": calculation.regime,
        },
        "bank_accounts": [_masked_account(account.model_dump()) for account in profile.bank_accounts],
    }


def prepare_return(profile: TaxProfileCreate, taxpayer_name: str, regime: str = "new", requested_itr: Optional[str] = None) -> Dict[str, Any]:
    selection = select_return(profile)
    if selection.recommended_itr and not selection.preparation_supported:
        reasons = " ".join(selection.reasons + selection.unsupported_conditions)
        raise ValueError(
            f"{selection.recommended_itr} is indicated by your profile, but this profile is outside the supported preparation scope. "
            f"No preparation summary was generated. {reasons}"
        )
    if not selection.eligible:
        details = selection.missing_information + selection.unsupported_conditions + selection.reasons
        raise ValueError("TaxWise cannot prepare this return: " + " ".join(details))
    if requested_itr and requested_itr != selection.recommended_itr:
        raise ValueError(f"{requested_itr} is not the deterministic recommendation for this profile; TaxWise selected {selection.recommended_itr}.")

    is_itr3 = selection.recommended_itr == "ITR-3"
    calculation: TaxCalculationResult = calculate_tax(profile, regime, allow_expanded_income=is_itr3)
    has_foreign_information = bool(
        profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income
    )
    has_capital_loss_carry_forward = calculation.capital_gains.capital_loss_carry_forward > 0
    has_property_loss_carry_forward = calculation.house_property_loss_carried_forward > 0
    return {
        "itr_form": selection.recommended_itr,
        "selection": selection.__dict__,
        "support_status": {
            "income_and_tax_calculation": "Supported",
            "capital_gains_computation": "Supported for implemented transaction rules" if profile.capital_gains else "Not applicable",
            "business_income_summary": "User-entered non-negative net profit included" if is_itr3 else "Not applicable",
            "business_books_and_detailed_schedules": "Not supported; books, expenses, and depreciation are not modeled" if is_itr3 else "Not applicable",
            "statutory_itr3_schedules": "Not supported; this is a review summary, not a completed statutory return" if is_itr3 else "Not applicable",
            "foreign_schedules": "Not supported" if has_foreign_information else "Not applicable",
            "capital_loss_carry_forward": "Calculated for review; historical loss schedules are not supported" if has_capital_loss_carry_forward else "Not applicable",
            "property_loss_carry_forward": "Calculated for review; historical loss schedules are not supported" if has_property_loss_carry_forward else "Not applicable",
            "return_filing_or_submission": "Not supported",
        },
        "assessment_year": profile.assessment_year,
        "taxpayer": {
            "name": taxpayer_name,
            "pan": f"{profile.pan_number[:2]}******{profile.pan_number[-2:]}" if profile.pan_number else None,
            "date_of_birth": profile.date_of_birth,
            "address": profile.address,
            "residential_status": profile.residential_status,
        },
        "income": {
            "salary": calculation.income_from_salary,
            "pension": calculation.income_from_pension,
            "house_property": calculation.house_property_income,
            "other_sources": calculation.other_sources_income,
            "business": calculation.business_income,
            "capital_gains": calculation.capital_gains,
            "gross_total_income": calculation.gross_total_income,
        },
        "schedules": {
            "salary_and_pension": [
                *[item.model_dump(mode="json") for item in profile.salary_income],
                *[item.model_dump(mode="json") for item in profile.pension_income],
            ],
            "house_property": [item.model_dump(mode="json") for item in profile.house_properties],
            "other_sources": [item.model_dump(mode="json") for item in profile.other_income],
            "capital_gains": [item.model_dump(mode="json") for item in calculation.capital_gains.transactions],
            "business_income": [item.model_dump(mode="json") for item in profile.business_income],
        },
        "deductions": {"total": calculation.total_deductions, "items": profile.deductions},
        "taxes_paid": {
            "tds": calculation.tds,
            "advance_tax": calculation.advance_tax,
            "self_assessment_tax": calculation.self_assessment_tax,
            "total": calculation.total_tax_paid,
        },
        "calculation": {
            **_calculation_details(calculation),
            "taxable_income": calculation.taxable_income,
            "tax_before_rebate": calculation.tax_before_rebate,
            "tax": calculation.total_tax_liability,
            "rebate": calculation.rebate,
            "surcharge": calculation.surcharge,
            "cess": calculation.cess,
            "total_tax": calculation.total_tax_liability,
            "refund": calculation.refund,
            "payable": calculation.balance_payable,
            "regime": calculation.regime,
        },
        "bank_accounts": [_masked_account(account.model_dump()) for account in profile.bank_accounts],
    }


def explain_itr_question(question: str, preparation: Dict[str, Any]) -> str:
    calculation = preparation["calculation"]
    income = preparation["income"]
    deductions = preparation["deductions"]
    taxes_paid = preparation["taxes_paid"]
    lower = question.lower()
    if "taxable income" in lower:
        return f"Your taxable income is ₹{calculation['taxable_income']:,.0f} because gross total income of ₹{income['gross_total_income']:,.0f} is reduced by ₹{deductions['total']:,.0f} in deductions. This is the result from the TaxWise Tax Engine."
    if "tds" in lower:
        return f"Your current Tax Profile records ₹{taxes_paid['tds']:,.0f} of TDS, included in total tax paid of ₹{taxes_paid['total']:,.0f}."
    if "deduction" in lower:
        return f"Your deductions total ₹{deductions['total']:,.0f}. The individual claims shown in the preview come directly from your Tax Profile and are validated by the Tax Engine."
    if "refund" in lower:
        return f"Your refund is ₹{calculation['refund']:,.0f} because recorded tax paid of ₹{taxes_paid['total']:,.0f} exceeds the calculated liability of ₹{calculation['total_tax']:,.0f}."
    if "reduce" in lower:
        return "You can review supported deductions in your Tax Profile. Any change must be made there and recalculated by the Tax Engine."
    return f"Your calculated total tax is ₹{calculation['total_tax']:,.0f}. It is based on taxable income of ₹{calculation['taxable_income']:,.0f}, rebate of ₹{calculation['rebate']:,.0f}, cess of ₹{calculation['cess']:,.0f}, and the current Tax Profile."