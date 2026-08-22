from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from .rules.ay_2026_27.deductions import STANDARD_DEDUCTION_NEW, STANDARD_DEDUCTION_OLD

ZERO = Decimal("0")
PROPERTY_LOSS_SET_OFF_LIMIT = Decimal("200000")


@dataclass(frozen=True)
class IncomeBreakdown:
    salary: Decimal
    pension: Decimal
    house_property: Decimal
    house_property_loss_set_off: Decimal
    other_sources: Decimal
    standard_deduction: Decimal
    gross_total_income: Decimal


def taxpayer_age_category(profile: TaxProfileCreate, on_date: date = date(2026, 3, 31)) -> str:
    if profile.residential_status != "resident":
        return "individual"
    if profile.date_of_birth:
        try:
            born = datetime.strptime(profile.date_of_birth, "%Y-%m-%d").date()
            age = on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))
            if age >= 80:
                return "super_senior"
            if age >= 60:
                return "senior"
            return "individual"
        except ValueError as error:
            raise ValueError("date_of_birth must use YYYY-MM-DD") from error
    return "senior" if profile.is_senior_citizen else "individual"


def calculate_house_property(profile: TaxProfileCreate) -> Decimal:
    total = ZERO
    for item in profile.house_properties:
        annual_value = ZERO if item.property_type == "self_occupied" else max(ZERO, item.annual_rent - item.municipal_tax)
        total += (annual_value - annual_value * Decimal("0.30") - item.home_loan_interest) * (item.ownership_share / Decimal("100"))
    return total


def calculate_income(profile: TaxProfileCreate, regime: str) -> IncomeBreakdown:
    salary = sum((item.gross_salary for item in profile.salary_income), ZERO)
    pension = sum((item.amount for item in profile.pension_income), ZERO)
    house_property = calculate_house_property(profile)
    other_sources = sum((item.amount for item in profile.other_income), ZERO)
    standard_cap = STANDARD_DEDUCTION_NEW if regime == "new" else STANDARD_DEDUCTION_OLD
    standard_deduction = min(salary + pension, standard_cap)
    loss_set_off = min(-house_property, PROPERTY_LOSS_SET_OFF_LIMIT) if house_property < ZERO and regime == "old" else ZERO
    gross_total_income = salary + pension + other_sources + house_property + loss_set_off
    return IncomeBreakdown(salary, pension, house_property, loss_set_off, other_sources, standard_deduction, gross_total_income)
