from decimal import Decimal, ROUND_HALF_UP

from schemas.tax_profile import TaxProfileCreate

from .cess import calculate_cess
from .deductions import calculate_deductions
from .income import calculate_income
from .models import RegimeComparison, TaxCalculationResult, TaxEngineError
from .rebates import calculate_rebate
from .regimes import slab_tax
from .rules.ay_2026_27.slabs import NEW_REGIME_SLABS, OLD_REGIME_SLABS
from .surcharge import calculate_surcharge

ZERO = Decimal("0")
RUPEE = Decimal("1")


def money(value: Decimal) -> Decimal:
    return value.quantize(RUPEE, rounding=ROUND_HALF_UP)


def paid_tax(profile: TaxProfileCreate) -> tuple[Decimal, Decimal, Decimal]:
    amounts = {"tds": ZERO, "advance_tax": ZERO, "self_assessment": ZERO}
    for payment in profile.taxes_paid:
        amounts[payment.tax_type] += payment.amount
    return amounts["tds"], amounts["advance_tax"], amounts["self_assessment"]


def calculate_tax(profile: TaxProfileCreate, regime: str) -> TaxCalculationResult:
    if profile.assessment_year != "2026-27":
        raise TaxEngineError("Only AY 2026-27 is supported by this engine")
    if profile.capital_gains or profile.business_income or profile.foreign_income_assets:
        raise TaxEngineError("This Phase 2A calculator supports the ITR-1-compatible income subset only")

    gross_total_income, standard_deduction = calculate_income(profile, regime)
    other_deductions = calculate_deductions(profile, regime)
    total_deductions = standard_deduction + other_deductions
    taxable_income = max(ZERO, money(gross_total_income - other_deductions))

    if regime == "new":
        tax_before_rebate = slab_tax(taxable_income, NEW_REGIME_SLABS)
    else:
        slab_key = "senior" if profile.is_senior_citizen else "individual"
        tax_before_rebate = slab_tax(taxable_income, OLD_REGIME_SLABS[slab_key])
    rebate = money(calculate_rebate(taxable_income, tax_before_rebate, regime, profile.residential_status == "resident"))
    tax_after_rebate = max(ZERO, tax_before_rebate - rebate)
    surcharge = money(calculate_surcharge(tax_after_rebate, taxable_income, regime))
    cess = calculate_cess(tax_after_rebate, surcharge)
    total_liability = money(tax_after_rebate + surcharge + cess)
    tds, advance_tax, self_assessment_tax = paid_tax(profile)
    total_paid = money(tds + advance_tax + self_assessment_tax)
    balance = money(max(ZERO, total_liability - total_paid))
    refund = money(max(ZERO, total_paid - total_liability))

    return TaxCalculationResult(
        assessment_year=profile.assessment_year,
        gross_total_income=money(gross_total_income),
        total_deductions=money(total_deductions),
        taxable_income=taxable_income,
        tax_before_rebate=tax_before_rebate,
        rebate=rebate,
        surcharge=surcharge,
        cess=cess,
        total_tax_liability=total_liability,
        tds=money(tds),
        advance_tax=money(advance_tax),
        self_assessment_tax=money(self_assessment_tax),
        total_tax_paid=total_paid,
        balance_payable=balance,
        refund=refund,
        regime=regime,
    )


def compare_regimes(profile: TaxProfileCreate) -> RegimeComparison:
    old_result = calculate_tax(profile, "old")
    new_result = calculate_tax(profile, "new")
    if old_result.total_tax_liability <= new_result.total_tax_liability:
        recommended = "old"
        saving = new_result.total_tax_liability - old_result.total_tax_liability
    else:
        recommended = "new"
        saving = old_result.total_tax_liability - new_result.total_tax_liability
    return RegimeComparison(old_regime=old_result, new_regime=new_result, recommended_regime=recommended, estimated_saving=money(saving))
