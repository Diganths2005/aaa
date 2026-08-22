from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from .models import TaxEngineError
from .rules.ay_2026_27.deductions import STANDARD_DEDUCTION_NEW, STANDARD_DEDUCTION_OLD

ZERO = Decimal("0")
PROPERTY_LOSS_SET_OFF_LIMIT = Decimal("200000")


@dataclass(frozen=True)
class IncomeBreakdown:
    salary: Decimal
    pension: Decimal
    house_property: Decimal
    house_property_loss: Decimal
    house_property_loss_set_off: Decimal
    house_property_loss_carried_forward: Decimal
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


def self_occupied_interest(item) -> Decimal:
    if item.home_loan_interest <= ZERO:
        return ZERO
    if item.loan_purpose is None or item.loan_sanction_date is None or item.construction_completed_within_five_years is None:
        raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "Self-occupied home-loan interest requires loan purpose, sanction date, and completion information")
    try:
        sanctioned = datetime.strptime(item.loan_sanction_date, "%Y-%m-%d").date()
    except ValueError as error:
        raise TaxEngineError("INVALID_DEDUCTION", "House-property loan sanction date must use YYYY-MM-DD") from error
    enhanced_limit = item.loan_purpose == "purchase_or_construction" and sanctioned >= date(1999, 4, 1) and item.construction_completed_within_five_years
    return min(item.home_loan_interest, Decimal("200000") if enhanced_limit else Decimal("30000"))


def calculate_house_property(profile: TaxProfileCreate, regime: str = "old") -> Decimal:
    total = ZERO
    for item in profile.house_properties:
        annual_value = ZERO if item.property_type == "self_occupied" else max(ZERO, item.annual_rent - item.municipal_tax)
        interest = ZERO if regime == "new" and item.property_type == "self_occupied" else (self_occupied_interest(item) if item.property_type == "self_occupied" else item.home_loan_interest)
        total += (annual_value - annual_value * Decimal("0.30") - interest) * (item.ownership_share / Decimal("100"))
    return total


def calculate_income(profile: TaxProfileCreate, regime: str) -> IncomeBreakdown:
    salary = sum((item.gross_salary for item in profile.salary_income), ZERO)
    pension = sum((item.amount for item in profile.pension_income), ZERO)
    house_property = calculate_house_property(profile, regime)
    other_sources = sum((item.amount for item in profile.other_income), ZERO)
    standard_cap = STANDARD_DEDUCTION_NEW if regime == "new" else STANDARD_DEDUCTION_OLD
    standard_deduction = min(salary + pension, standard_cap)
    loss_set_off = min(-house_property, PROPERTY_LOSS_SET_OFF_LIMIT) if house_property < ZERO and regime == "old" else ZERO
    taxable_house_property = house_property if house_property >= ZERO else -loss_set_off
    gross_total_income = salary + pension + other_sources + taxable_house_property
    loss = max(ZERO, -house_property)
    carried_forward = max(ZERO, loss - loss_set_off) if regime == "old" else ZERO
    return IncomeBreakdown(salary, pension, house_property, loss, loss_set_off, carried_forward, other_sources, standard_deduction, gross_total_income)
