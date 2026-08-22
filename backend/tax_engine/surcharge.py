from decimal import Decimal
from .rules.ay_2026_27.constants import SURCHARGE_THRESHOLDS


def surcharge_rate(total_income: Decimal, regime: str) -> Decimal:
    for threshold, rate in reversed(SURCHARGE_THRESHOLDS):
        if total_income > threshold:
            if regime == "new" and rate > Decimal("0.25"):
                return Decimal("0.25")
            return rate
    return Decimal("0")


def calculate_surcharge(tax: Decimal, total_income: Decimal, regime: str) -> Decimal:
    return tax * surcharge_rate(total_income, regime)
