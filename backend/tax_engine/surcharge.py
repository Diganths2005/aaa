from decimal import Decimal
from typing import Callable

from .rounding import round_rupee
from .rules.ay_2026_27.constants import SURCHARGE_THRESHOLDS


def surcharge_rate(total_income: Decimal, regime: str) -> Decimal:
    rate = Decimal("0")
    for threshold, candidate in SURCHARGE_THRESHOLDS:
        if total_income > threshold:
            rate = candidate
    if regime == "new":
        return min(rate, Decimal("0.25"))
    return rate


def calculate_surcharge(tax: Decimal, total_income: Decimal, regime: str, tax_at_income: Callable[[Decimal], Decimal]) -> Decimal:
    rate = surcharge_rate(total_income, regime)
    if rate == 0:
        return Decimal("0")
    raw = tax * rate
    crossed = [(threshold, candidate) for threshold, candidate in SURCHARGE_THRESHOLDS if total_income > threshold]
    threshold, _ = crossed[-1]
    tax_at_threshold = tax_at_income(threshold)
    excess_income = total_income - threshold
    marginal_relief = max(Decimal("0"), tax + raw - tax_at_threshold - excess_income)
    return round_rupee(max(Decimal("0"), raw - marginal_relief))
