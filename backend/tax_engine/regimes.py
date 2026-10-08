from decimal import Decimal
from typing import Iterable, Optional

from .models import TaxSlabCalculation
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


def calculate_slab_breakdown(income: Decimal, slabs: Iterable[tuple[Optional[Decimal], Decimal]]) -> list[TaxSlabCalculation]:
    breakdown: list[TaxSlabCalculation] = []
    lower = Decimal("0")
    for upper, rate in slabs:
        taxable = max(Decimal("0"), income - lower) if upper is None else max(Decimal("0"), min(income, upper) - lower)
        if taxable > 0:
            breakdown.append(TaxSlabCalculation(
                lower_bound=lower,
                upper_bound=upper,
                rate=rate,
                taxable_amount=taxable,
                tax=taxable * rate,
            ))
        if upper is None or income <= upper:
            break
        lower = upper
    return breakdown
