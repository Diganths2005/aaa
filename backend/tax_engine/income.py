from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate

ZERO = Decimal("0")


def calculate_income(profile: TaxProfileCreate, regime: str) -> tuple[Decimal, Decimal]:
    salary = sum((item.gross_salary for item in profile.salary_income), ZERO)
    pension = sum((item.amount for item in profile.pension_income), ZERO)
    house_property = ZERO
    for item in profile.house_properties:
        if item.property_type == "self_occupied":
            property_income = -item.home_loan_interest
        else:
            annual_value = item.annual_rent - item.municipal_tax
            property_income = annual_value - (annual_value * Decimal("0.30")) - item.home_loan_interest
        house_property += property_income * (item.ownership_share / Decimal("100"))
    other = sum((item.amount for item in profile.other_income), ZERO)
    standard_deduction = Decimal("75000") if regime == "new" else Decimal("50000")
    salary_deduction = standard_deduction if salary > ZERO else ZERO
    gross_total_income = max(ZERO, salary - salary_deduction + pension + house_property + other)
    return gross_total_income, salary_deduction
