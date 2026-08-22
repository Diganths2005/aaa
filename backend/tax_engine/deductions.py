from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate

ZERO = Decimal("0")
OLD_REGIME_CAPS = {"80C": Decimal("150000"), "80CCD(1B)": Decimal("50000")}


def calculate_deductions(profile: TaxProfileCreate, regime: str) -> Decimal:
    total = ZERO
    for item in profile.deductions:
        section = item.section.upper()
        if regime == "new" and section != "80CCD(2)":
            continue
        amount = item.amount
        if regime == "old" and section in OLD_REGIME_CAPS:
            amount = min(amount, OLD_REGIME_CAPS[section])
        total += amount
    return total
