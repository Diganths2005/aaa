from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from .rules.ay_2026_27.deductions import STANDARD_DEDUCTION_NEW, STANDARD_DEDUCTION_OLD

ZERO = Decimal("0")
CAPS = {
    "80C": Decimal("150000"), "80CCD(1B)": Decimal("50000"), "80D": Decimal("100000"),
    "80DD": Decimal("125000"), "80DDB": Decimal("100000"), "80EE": Decimal("50000"),
    "80EEA": Decimal("150000"), "80TTA": Decimal("10000"), "80TTB": Decimal("50000"),
    "80U": Decimal("125000"), "80GG": Decimal("60000"),
}
ALLOWED_OLD = set(CAPS) | {"80CCD(2)", "80E", "80G"}
ALLOWED_NEW = {"80CCD(2)"}


def calculate_deductions(profile: TaxProfileCreate, regime: str, salary: Decimal = ZERO) -> Decimal:
    allowed = ALLOWED_NEW if regime == "new" else ALLOWED_OLD
    total = ZERO
    for item in profile.deductions:
        section = item.section.upper().replace(" ", "")
        if section not in allowed:
            continue
        amount = item.amount
        if section == "80D" and profile.is_senior_citizen:
            amount = min(amount, Decimal("100000"))
        elif section == "80D":
            amount = min(amount, Decimal("75000"))
        elif section == "80CCD(2)":
            amount = min(amount, salary * (Decimal("0.14") if regime == "new" else Decimal("0.10")))
        elif section == "80TTB" and not profile.is_senior_citizen:
            continue
        elif section == "80TTA" and profile.is_senior_citizen:
            continue
        elif section in CAPS:
            amount = min(amount, CAPS[section])
        total += amount
    return total
