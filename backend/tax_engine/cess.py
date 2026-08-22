from decimal import Decimal, ROUND_HALF_UP
from .rules.ay_2026_27.constants import CESS_RATE


def calculate_cess(tax: Decimal, surcharge: Decimal) -> Decimal:
    return ((tax + surcharge) * CESS_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
