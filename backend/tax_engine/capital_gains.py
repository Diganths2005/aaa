from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Iterable

from schemas.tax_profile import CapitalGain

from .models import CapitalGainResult, CapitalGainsSummary, TaxEngineError
from .rounding import round_rupee
from .rules.ay_2026_27.capital_gains import (
    CAPITAL_GAIN_ASSET_TYPES,
    HOLDING_PERIOD_MONTHS,
    SECTION_111A_RATE,
    SECTION_112_RATE,
    SECTION_112A_EXEMPTION,
    SECTION_112A_RATE,
)

ZERO = Decimal("0")
GRANDFATHERING_DATE = date(2018, 2, 1)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def holding_period_months(item: CapitalGain) -> int:
    if item.asset_type not in CAPITAL_GAIN_ASSET_TYPES:
        raise TaxEngineError("UNSUPPORTED_CAPITAL_GAIN_ASSET", f"{item.asset_type} is not a supported capital-gain asset type")
    if item.asset_type == "other_security":
        if item.is_listed is None:
            raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "other_security requires listed or unlisted status")
        return 12 if item.is_listed else 24
    return HOLDING_PERIOD_MONTHS[item.asset_type]


def classify_holding_period(item: CapitalGain) -> str:
    if item.acquisition_date is None or item.sale_date is None:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "Capital-gain transactions require acquisition and sale dates")
    acquired, sold = item.acquisition_date, item.sale_date
    if sold < acquired:
        raise TaxEngineError("INVALID_CAPITAL_GAIN", "sale_date cannot precede acquisition_date")
    return "long_term" if sold > add_months(acquired, holding_period_months(item)) else "short_term"


def required_amount(value: Decimal | None, name: str) -> Decimal:
    if value is None:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", f"Capital-gain transactions require {name}")
    return value


def validate_equity_metadata(item: CapitalGain) -> None:
    if item.quantity is None or item.quantity <= ZERO:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "Equity and equity-fund transactions require a positive quantity")
    if item.asset_type == "listed_equity_share" and item.is_listed is not True:
        raise TaxEngineError("INVALID_CAPITAL_GAIN", "listed_equity_share requires is_listed=true")
    if item.asset_type == "equity_oriented_mutual_fund" and item.is_equity_oriented is not True:
        raise TaxEngineError("INVALID_CAPITAL_GAIN", "equity_oriented_mutual_fund requires is_equity_oriented=true")
    if item.stt_paid_on_transfer is None:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "Equity and equity-fund transactions require STT transfer status")


def is_112a_eligible(item: CapitalGain, holding_period: str) -> bool:
    if item.asset_type not in {"listed_equity_share", "equity_oriented_mutual_fund"} or holding_period != "long_term":
        return False
    validate_equity_metadata(item)
    if item.stt_paid_on_transfer is not True:
        return False
    if item.stt_paid_on_acquisition is None:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "Section 112A requires STT acquisition status")
    return item.stt_paid_on_acquisition is True


def gain_cost(item: CapitalGain, holding_period: str, section: str) -> Decimal:
    acquisition_cost = required_amount(item.acquisition_cost, "acquisition cost")
    if section != "112A" or item.acquisition_date is None or item.acquisition_date >= GRANDFATHERING_DATE:
        return acquisition_cost
    if item.grandfathered_fmv_2018 is None:
        raise TaxEngineError("INSUFFICIENT_CAPITAL_GAIN_DATA", "Pre-1 February 2018 Section 112A assets require 31 January 2018 FMV")
    return max(acquisition_cost, min(item.grandfathered_fmv_2018, required_amount(item.sale_consideration, "sale consideration")))


def calculate_transaction(item: CapitalGain) -> CapitalGainResult:
    holding = classify_holding_period(item)
    if item.asset_type in {"listed_equity_share", "equity_oriented_mutual_fund"}:
        validate_equity_metadata(item)
    if holding == "short_term":
        special = item.asset_type in {"listed_equity_share", "equity_oriented_mutual_fund"} and item.stt_paid_on_transfer is True
        section, rate = ("111A", SECTION_111A_RATE) if special else ("slab", None)
    else:
        special_112a = is_112a_eligible(item, holding)
        section, rate = ("112A", SECTION_112A_RATE) if special_112a else ("112", SECTION_112_RATE)
    sale = required_amount(item.sale_consideration, "sale consideration")
    computed_gain = sale - gain_cost(item, holding, section) - item.improvement_cost - item.transfer_expenses
    return CapitalGainResult(
        asset_type=item.asset_type,
        holding_period=holding,
        sale_consideration=sale,
        acquisition_cost=required_amount(item.acquisition_cost, "acquisition cost"),
        improvement_cost=item.improvement_cost,
        transfer_expenses=item.transfer_expenses,
        computed_gain=round_rupee(computed_gain),
        gain_type="gain" if computed_gain >= ZERO else "loss",
        applicable_section=section,
        special_rate=rate,
        taxable_gain=max(ZERO, round_rupee(computed_gain)),
        tax=ZERO,
        loss_setoff=ZERO,
        carry_forward=max(ZERO, -round_rupee(computed_gain)),
    )


def allocate_losses(losses: list[CapitalGainResult], gains: Iterable[CapitalGainResult]) -> None:
    for loss in losses:
        remaining = loss.carry_forward
        for gain in gains:
            if remaining <= ZERO:
                break
            used = min(remaining, gain.taxable_gain)
            if used <= ZERO:
                continue
            gain.taxable_gain -= used
            gain.loss_setoff += used
            remaining -= used
        loss.loss_setoff = loss.carry_forward - remaining
        loss.carry_forward = remaining


def classify_results(results: list[CapitalGainResult], holding: str, section: str | None = None, positive: bool = True) -> list[CapitalGainResult]:
    return [result for result in results if result.holding_period == holding and (section is None or result.applicable_section == section) and ((result.computed_gain >= ZERO) == positive)]


def summarize_capital_gains(transactions: list[CapitalGain]) -> CapitalGainsSummary:
    results = [calculate_transaction(item) for item in transactions]
    st_losses = classify_results(results, "short_term", positive=False)
    lt_losses = classify_results(results, "long_term", positive=False)
    st_special = classify_results(results, "short_term", "111A")
    st_normal = classify_results(results, "short_term", "slab")
    lt_112 = classify_results(results, "long_term", "112")
    lt_112a = classify_results(results, "long_term", "112A")

    # LTCL may only reduce LTCG.  STCL may reduce both STCG and LTCG; set off
    # long-term losses first so their narrower statutory use is not wasted.
    allocate_losses(lt_losses, lt_112)
    allocate_losses(lt_losses, lt_112a)
    allocate_losses(st_losses, st_special)
    allocate_losses(st_losses, st_normal)
    allocate_losses(st_losses, lt_112)
    allocate_losses(st_losses, lt_112a)

    # Section 112A's Rs 1.25 lakh threshold applies after current-year loss set-off.
    remaining_exemption = SECTION_112A_EXEMPTION
    for result in results:
        if result.applicable_section != "112A" or result.taxable_gain <= ZERO:
            continue
        exempt = min(remaining_exemption, result.taxable_gain)
        taxable = result.taxable_gain - exempt
        result.taxable_gain = taxable
        result.tax = round_rupee(taxable * SECTION_112A_RATE)
        remaining_exemption -= exempt
    for result in results:
        if result.applicable_section in {"111A", "112"}:
            result.tax = round_rupee(result.taxable_gain * (result.special_rate or ZERO))

    st_gain = sum((max(ZERO, result.computed_gain) for result in results if result.holding_period == "short_term"), ZERO)
    lt_gain = sum((max(ZERO, result.computed_gain) for result in results if result.holding_period == "long_term"), ZERO)
    st_loss = sum((max(ZERO, -result.computed_gain) for result in results if result.holding_period == "short_term"), ZERO)
    lt_loss = sum((max(ZERO, -result.computed_gain) for result in results if result.holding_period == "long_term"), ZERO)
    ordinary_stcg = sum((max(ZERO, result.computed_gain) - result.loss_setoff for result in results if result.applicable_section == "slab"), ZERO)
    special_gain = sum((max(ZERO, result.computed_gain) - result.loss_setoff for result in results if result.applicable_section in {"111A", "112", "112A"}), ZERO)
    special_tax = sum((result.tax for result in results), ZERO)
    carry_forward = sum((result.carry_forward for result in results if result.gain_type == "loss"), ZERO)
    has_short_term = any(result.holding_period == "short_term" for result in results)
    non_112a_long_term = any(result.holding_period == "long_term" and result.applicable_section != "112A" for result in results)
    itr1_eligible = not has_short_term and not non_112a_long_term and carry_forward == ZERO and sum((result.computed_gain for result in results if result.applicable_section == "112A"), ZERO) <= SECTION_112A_EXEMPTION
    reason = "Only Section 112A LTCG within the Rs 1.25 lakh ITR-1 limit is present" if itr1_eligible else "Capital-gain facts require an ITR form other than ITR-1"
    return CapitalGainsSummary(
        transactions=results,
        short_term_capital_gain=round_rupee(st_gain),
        long_term_capital_gain=round_rupee(lt_gain),
        short_term_capital_loss=round_rupee(st_loss),
        long_term_capital_loss=round_rupee(lt_loss),
        current_year_capital_gain_after_setoff=round_rupee(ordinary_stcg + special_gain),
        capital_loss_carry_forward=round_rupee(carry_forward),
        ordinary_short_term_capital_gain=round_rupee(ordinary_stcg),
        special_rate_capital_gain=round_rupee(special_gain),
        special_rate_tax=round_rupee(special_tax),
        itr1_capital_gain_eligible=itr1_eligible,
        itr1_capital_gain_reason=reason,
    )
