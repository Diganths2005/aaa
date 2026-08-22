from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate

from .cess import calculate_cess
from .deductions import calculate_deductions
from .income import calculate_income, taxpayer_age_category
from .models import RegimeComparison, TaxCalculationResult, TaxEngineError
from .rebates import calculate_rebate
from .regimes import slab_tax
from .rounding import round_rupee
from .rules.ay_2026_27.slabs import NEW_REGIME_SLABS, OLD_REGIME_SLABS
from .surcharge import calculate_surcharge

ZERO = Decimal("0")


def paid_tax(profile: TaxProfileCreate) -> tuple[Decimal, Decimal, Decimal]:
    amounts = {"tds": ZERO, "advance_tax": ZERO, "self_assessment": ZERO}
    for payment in profile.taxes_paid:
        amounts[payment.tax_type] += payment.amount
    return tuple(amounts[key] for key in ("tds", "advance_tax", "self_assessment"))


def calculate_tax(profile: TaxProfileCreate, regime: str) -> TaxCalculationResult:
    if profile.assessment_year != "2026-27":
        raise TaxEngineError("INVALID_ASSESSMENT_YEAR", "Only AY 2026-27 is supported")
    if regime not in {"old", "new"}:
        raise TaxEngineError("INVALID_REGIME", "Regime must be old or new")
    if profile.capital_gains:
        raise TaxEngineError("UNSUPPORTED_CAPITAL_GAINS", "Capital gains, including limited Section 112A cases, are planned for Phase 2B")
    if profile.business_income:
        raise TaxEngineError("UNSUPPORTED_BUSINESS_INCOME", "Business and professional income is planned for Phase 2B")
    if profile.foreign_income_assets:
        raise TaxEngineError("UNSUPPORTED_FOREIGN_INCOME", "Foreign income and assets are planned for Phase 2B")

    income = calculate_income(profile, regime)
    deductions = calculate_deductions(profile, regime, income.salary, taxpayer_age_category(profile))
    total_deductions = income.standard_deduction + deductions
    taxable_income = max(ZERO, round_rupee(income.gross_total_income - income.standard_deduction - deductions))
    if regime == "new":
        tax_before_rebate = slab_tax(taxable_income, NEW_REGIME_SLABS)
    else:
        category = taxpayer_age_category(profile)
        tax_before_rebate = slab_tax(taxable_income, OLD_REGIME_SLABS[category])

    rebate = round_rupee(calculate_rebate(taxable_income, tax_before_rebate, regime, profile.residential_status == "resident"))
    tax_after_rebate = max(ZERO, tax_before_rebate - rebate)

    def tax_at_income(value: Decimal) -> Decimal:
        if regime == "new":
            return slab_tax(value, NEW_REGIME_SLABS)
        return slab_tax(value, OLD_REGIME_SLABS[taxpayer_age_category(profile)])

    surcharge = calculate_surcharge(tax_after_rebate, taxable_income, regime, tax_at_income)
    cess = calculate_cess(tax_after_rebate, surcharge)
    total_liability = round_rupee(tax_after_rebate + surcharge + cess)
    tds, advance_tax, self_assessment_tax = paid_tax(profile)
    total_paid = round_rupee(tds + advance_tax + self_assessment_tax)
    difference = total_liability - total_paid

    return TaxCalculationResult(
        assessment_year=profile.assessment_year,
        income_from_salary=round_rupee(income.salary),
        income_from_pension=round_rupee(income.pension),
        house_property_income=round_rupee(income.house_property),
        house_property_loss=round_rupee(income.house_property_loss),
        house_property_loss_set_off=round_rupee(income.house_property_loss_set_off),
        house_property_loss_carried_forward=round_rupee(income.house_property_loss_carried_forward),
        other_sources_income=round_rupee(income.other_sources),
        gross_total_income=round_rupee(income.gross_total_income),
        total_deductions=round_rupee(total_deductions),
        taxable_income=taxable_income,
        tax_before_rebate=tax_before_rebate,
        rebate=rebate,
        surcharge=round_rupee(surcharge),
        cess=cess,
        total_tax_liability=total_liability,
        tds=round_rupee(tds),
        advance_tax=round_rupee(advance_tax),
        self_assessment_tax=round_rupee(self_assessment_tax),
        total_tax_paid=total_paid,
        balance_payable=round_rupee(max(ZERO, difference)),
        refund=round_rupee(max(ZERO, -difference)),
        regime=regime,
    )


def compare_regimes(profile: TaxProfileCreate) -> RegimeComparison:
    old_result = calculate_tax(profile, "old")
    new_result = calculate_tax(profile, "new")
    difference = old_result.total_tax_liability - new_result.total_tax_liability
    if difference == ZERO:
        recommended = "equal"
        saving = ZERO
    elif difference < ZERO:
        recommended = "old"
        saving = -difference
    else:
        recommended = "new"
        saving = difference
    return RegimeComparison(old_regime=old_result, new_regime=new_result, recommended_regime=recommended, estimated_saving=round_rupee(saving))
