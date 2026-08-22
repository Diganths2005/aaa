from decimal import Decimal, ROUND_HALF_UP

RUPEE = Decimal("1")


def round_rupee(value: Decimal) -> Decimal:
    return Decimal(value).quantize(RUPEE, rounding=ROUND_HALF_UP)