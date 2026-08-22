from decimal import Decimal
from .rules.ay_2026_27.constants import CESS_RATE
from .rounding import round_rupee


def calculate_cess(tax: Decimal, surcharge: Decimal) -> Decimal:
    return round_rupee((tax + surcharge) * CESS_RATE)
