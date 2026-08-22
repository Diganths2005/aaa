from decimal import Decimal

from .rounding import round_rupee
from .rules.ay_2026_27.constants import NEW_REGIME_REBATE_LIMIT, NEW_REGIME_REBATE_MAX, OLD_REGIME_REBATE_LIMIT, OLD_REGIME_REBATE_MAX


def calculate_rebate(taxable_income: Decimal, tax_before_rebate: Decimal, regime: str, resident: bool = True, special_rate_tax: Decimal = Decimal("0")) -> Decimal:
    if not resident or special_rate_tax > 0:
        return Decimal("0")
    if regime == "old":
        if taxable_income <= OLD_REGIME_REBATE_LIMIT:
            return min(tax_before_rebate, OLD_REGIME_REBATE_MAX)
        return Decimal("0")
    if taxable_income <= NEW_REGIME_REBATE_LIMIT:
        return min(tax_before_rebate, NEW_REGIME_REBATE_MAX)
    excess_income = taxable_income - NEW_REGIME_REBATE_LIMIT
    return round_rupee(max(Decimal("0"), tax_before_rebate - excess_income))
