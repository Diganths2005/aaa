from decimal import Decimal
from .rules.ay_2026_27.constants import NEW_REGIME_REBATE_LIMIT, NEW_REGIME_REBATE_MAX, OLD_REGIME_REBATE_LIMIT, OLD_REGIME_REBATE_MAX


def calculate_rebate(taxable_income: Decimal, tax_before_rebate: Decimal, regime: str, resident: bool = True) -> Decimal:
    if not resident:
        return Decimal("0")
    if regime == "new" and taxable_income <= NEW_REGIME_REBATE_LIMIT:
        return min(tax_before_rebate, NEW_REGIME_REBATE_MAX)
    if regime == "old" and taxable_income <= OLD_REGIME_REBATE_LIMIT:
        return min(tax_before_rebate, OLD_REGIME_REBATE_MAX)
    if regime == "new" and taxable_income > NEW_REGIME_REBATE_LIMIT:
        marginal_excess = taxable_income - NEW_REGIME_REBATE_LIMIT
        return max(Decimal("0"), tax_before_rebate - marginal_excess)
    return Decimal("0")
