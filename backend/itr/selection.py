from dataclasses import dataclass
from typing import List, Optional

from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax
from tax_engine.capital_gains import summarize_capital_gains
from tax_engine.models import TaxEngineError


@dataclass(frozen=True)
class ITRSelection:
    recommended_itr: Optional[str]
    eligible: bool
    assessment_year: str
    reasons: List[str]
    missing_information: List[str]
    unsupported_conditions: List[str]
    preparation_supported: bool = False


TOTAL_INCOME_CAP = 5_000_000
LTCG_112A_SIMPLE_CAP = 125_000
AGRICULTURAL_INCOME_CAP = 5_000
MAX_SIMPLE_FORM_HOUSES = 2
PRESUMPTIVE_44AD_CAP = 20_000_000
PRESUMPTIVE_44AD_CASH_CAP = 30_000_000
PRESUMPTIVE_44ADA_CAP = 5_000_000
PRESUMPTIVE_44ADA_CASH_CAP = 7_500_000


def _capital_gains_status(profile: TaxProfileCreate) -> tuple[bool, str, list[str]]:
    if not profile.capital_gains:
        return True, "", []

    try:
        summary = summarize_capital_gains(profile.capital_gains)
    except TaxEngineError as exc:
        if exc.code == "INSUFFICIENT_CAPITAL_GAIN_DATA":
            return False, "", [str(exc)]
        return False, "", [str(exc)]

    if summary.itr1_capital_gain_eligible:
        return True, summary.itr1_capital_gain_reason, []

    return False, summary.itr1_capital_gain_reason, []


def _taxable_total_income(profile: TaxProfileCreate, *, allow_business: bool = False) -> tuple[Optional[float], list[str]]:
    """Use the deterministic engine for the actual total-income ceiling.

    Form selection should not invent a gross-income proxy: the AY 2026-27
    simple-form ceiling is based on total income. If the engine cannot compute
    it because facts are incomplete, return that as missing information.
    """
    try:
        result = calculate_tax(profile, "new", allow_expanded_income=allow_business)
        return float(result.taxable_income), []
    except TaxEngineError as exc:
        if exc.code in {"INSUFFICIENT_CAPITAL_GAIN_DATA", "UNSUPPORTED_CAPITAL_GAINS"}:
            return None, [str(exc)]
        return None, [str(exc)]


def _itr4_disqualifiers(profile: TaxProfileCreate, *, capital_gain_ok: bool, total_income: Optional[float]) -> list[str]:
    blocks: list[str] = []
    if profile.residential_status != "resident":
        blocks.append("ITR-4 is limited to resident individuals in the supported workflow.")
    if profile.is_director:
        blocks.append("Company director status rules out ITR-4.")
    if profile.has_unlisted_equity:
        blocks.append("Held unlisted equity shares; ITR-4 is not eligible.")
    if profile.has_foreign_income or profile.has_foreign_assets or profile.foreign_income_assets:
        blocks.append("Foreign assets/income require a return with Schedule FA, not ITR-4.")
    if profile.has_esop_deferral:
        blocks.append("Deferred ESOP tax makes ITR-4 ineligible.")
    if profile.has_lottery_or_gaming_income:
        blocks.append("Lottery/gaming or other special-rate income is outside the supported ITR-4 scope.")
    if profile.has_carry_forward_loss:
        blocks.append("A brought-forward/current loss requires a loss schedule outside ITR-4.")
    if profile.has_speculative_income:
        blocks.append("Speculative income is outside ITR-4.")
    if profile.agricultural_income > AGRICULTURAL_INCOME_CAP:
        blocks.append("Agricultural income exceeds ₹5,000.")
    if len(profile.house_properties) > MAX_SIMPLE_FORM_HOUSES:
        blocks.append("More than two house properties require ITR-3/ITR-2.")
    if total_income is not None and total_income > TOTAL_INCOME_CAP:
        blocks.append("Total income exceeds ₹50 lakh.")
    if not capital_gain_ok:
        blocks.append("Capital-gain facts exceed the ITR-4 Section 112A-only allowance or need more transaction data.")

    for item in profile.business_income:
        section = item.presumptive_section
        if section not in {"44AD", "44ADA", "44AE"}:
            blocks.append("Every ITR-4 business/professional entry must use 44AD, 44ADA or 44AE.")
            continue
        if section == "44AD":
            cap = PRESUMPTIVE_44AD_CASH_CAP if item.cash_receipts_within_5pct is True else PRESUMPTIVE_44AD_CAP
            if item.cash_receipts_within_5pct is None:
                blocks.append("44AD cash-receipt status is missing; the ₹2 crore/₹3 crore ceiling cannot be verified.")
            elif item.gross_receipts > cap:
                blocks.append(f"44AD gross receipts exceed the applicable ₹{cap:,.0f} ceiling.")
        elif section == "44ADA":
            cap = PRESUMPTIVE_44ADA_CASH_CAP if item.cash_receipts_within_5pct is True else PRESUMPTIVE_44ADA_CAP
            if item.cash_receipts_within_5pct is None:
                blocks.append("44ADA cash-receipt status is missing; the ₹50 lakh/₹75 lakh ceiling cannot be verified.")
            elif item.gross_receipts > cap:
                blocks.append(f"44ADA gross receipts exceed the applicable ₹{cap:,.0f} ceiling.")
        elif section == "44AE":
            if item.goods_carriages_owned is None:
                blocks.append("44AE vehicle count is missing; the ten-goods-carriage limit cannot be verified.")
            elif item.goods_carriages_owned > 10:
                blocks.append("44AE covers at most ten goods carriages for ITR-4.")
    return blocks


def select_itr(profile: TaxProfileCreate) -> ITRSelection:
    reasons: List[str] = []
    missing: List[str] = []
    unsupported: List[str] = []

    if profile.assessment_year != "2026-27":
        return ITRSelection(
            None, False, profile.assessment_year,
            ["Only assessment year 2026-27 is supported."], [], [],
            False,
        )

    has_any_income = bool(
        profile.salary_income or profile.pension_income or profile.other_income
        or profile.house_properties or profile.capital_gains or profile.business_income
        or profile.agricultural_income
    )
    if not has_any_income:
        missing.append("Add at least one supported income source.")

    has_business = bool(profile.business_income or profile.has_business_income)
    has_capital_gains = bool(profile.capital_gains)
    has_foreign = bool(profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income)
    # Business/professional income is decided before ITR-1/2. This mirrors the
    # strong part of itr-agent: ITR-2 cannot carry Schedule BP, while ITR-4 is
    # only an optional simplified form for eligible presumptive cases.
    if has_business:
        if not profile.business_income:
            missing.append("Add business/professional income details.")

        all_presumptive = bool(profile.business_income) and all(
            item.presumptive_section in {"44AD", "44ADA", "44AE"} for item in profile.business_income
        )
        mixed_business = any(item.presumptive_section is None for item in profile.business_income)

        capital_ok, _, capital_missing = _capital_gains_status(profile)
        total_income, total_income_errors = _taxable_total_income(profile, allow_business=True)
        if capital_missing:
            missing.extend(capital_missing)
        if total_income_errors:
            missing.extend(total_income_errors)

        itr4_blocks = _itr4_disqualifiers(profile, capital_gain_ok=capital_ok, total_income=total_income)
        if mixed_business:
            itr4_blocks.append("Non-presumptive business/professional income requires ITR-3.")

        if all_presumptive and not itr4_blocks and not missing:
            return ITRSelection(
                "ITR-4", True, profile.assessment_year,
                ["Eligible presumptive business/professional income fits the supported ITR-4 scope."],
                [], [], True,
            )

        if profile.residential_status != "resident":
            unsupported.append("Non-resident ITR-3 preparation is not supported by this TaxWise workflow.")
        if has_foreign:
            unsupported.append("Foreign income and asset schedules are not prepared by this TaxWise workflow.")
        if any(item.net_profit_or_loss < 0 for item in profile.business_income):
            unsupported.append("Business losses and statutory loss schedules are not supported.")
        reasons.append("Business or professional income requires ITR-3 when ITR-4 is not eligible.")
        reasons.extend(itr4_blocks)
        return ITRSelection(
            "ITR-3",
            not missing and not unsupported,
            profile.assessment_year,
            reasons,
            list(dict.fromkeys(missing)),
            list(dict.fromkeys(unsupported)),
            not unsupported and not missing,
        )

    # Non-business taxpayers: apply the actual AY 2026-27 simple-form gates.
    capital_ok, capital_reason, capital_missing = _capital_gains_status(profile)
    if capital_missing:
        missing.extend(capital_missing)

    simple_blocks: list[str] = []
    if profile.residential_status != "resident":
        simple_blocks.append("RNOR/NRI taxpayers are outside ITR-1; use ITR-2 for non-business income.")
    if profile.is_director:
        simple_blocks.append("Director in a company.")
    if profile.has_unlisted_equity:
        simple_blocks.append("Held unlisted equity shares.")
    if has_foreign:
        simple_blocks.append("Foreign assets/income/signing-authority information requires Schedule FA/FSI.")
    if profile.has_esop_deferral:
        simple_blocks.append("Deferred ESOP tax.")
    if profile.has_carry_forward_loss:
        simple_blocks.append("Brought-forward or carry-forward loss requires a loss schedule.")
    if profile.tds_194n:
        simple_blocks.append("TDS was deducted under section 194N.")
    if profile.has_lottery_or_gaming_income:
        simple_blocks.append("Lottery/gaming/racehorse or other special-rate income is outside ITR-1.")
    if profile.agricultural_income > AGRICULTURAL_INCOME_CAP:
        simple_blocks.append("Agricultural income exceeds ₹5,000.")
    if len(profile.house_properties) > MAX_SIMPLE_FORM_HOUSES:
        simple_blocks.append("More than two house properties.")
    if has_capital_gains and not capital_ok:
        simple_blocks.append(capital_reason or "Capital-gain facts require ITR-2.")
    if profile.has_speculative_income:
        simple_blocks.append("Speculative income is outside ITR-1.")

    total_income, total_income_errors = _taxable_total_income(profile)
    if total_income_errors:
        missing.extend(total_income_errors)
    elif total_income is not None and total_income > TOTAL_INCOME_CAP:
        simple_blocks.append("Total income exceeds ₹50 lakh.")

    if simple_blocks:
        reasons.extend(simple_blocks)
        itr2_unsupported: list[str] = []
        if has_foreign:
            itr2_unsupported.append("Foreign income and asset schedules are not yet prepared by TaxWise.")
        if profile.has_speculative_income:
            itr2_unsupported.append("Speculative-income schedules are not supported.")
        if profile.has_carry_forward_loss:
            itr2_unsupported.append("Persistent carry-forward loss schedules are not supported.")
        return ITRSelection(
            "ITR-2",
            not missing and not itr2_unsupported,
            profile.assessment_year,
            reasons,
            list(dict.fromkeys(missing)),
            itr2_unsupported,
            not itr2_unsupported,
        )

    return ITRSelection(
        "ITR-1",
        not missing,
        profile.assessment_year,
        [capital_reason] if capital_reason else ["Profile satisfies the AY 2026-27 ITR-1 conditions."],
        list(dict.fromkeys(missing)),
        [],
        True,
    )
