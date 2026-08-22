from decimal import Decimal
from typing import Iterable, Optional
from .rounding import round_rupee


def slab_tax(income: Decimal, slabs: Iterable[tuple[Optional[Decimal], Decimal]]) -> Decimal:
    tax = Decimal("0")
    lower = Decimal("0")
    for upper, rate in slabs:
        if upper is None:
            taxable = income - lower
        else:
            taxable = min(income, upper) - lower
        if taxable > 0:
            tax += taxable * rate
        if upper is None or income <= upper:
            break
        lower = upper
    return round_rupee(tax)
