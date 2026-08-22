from datetime import date
from decimal import Decimal

from schemas.tax_profile import TaxProfileCreate
from .models import TaxEngineError

ZERO = Decimal("0")
ALLOWED_OLD = {"80C", "80CCD(1B)", "80CCD(2)", "80D", "80DD", "80DDB", "80E", "80EE", "80EEA", "80G", "80GG", "80TTA", "80TTB", "80U"}
ALLOWED_NEW = {"80CCD(2)"}


def parse_date(value: str, section: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise TaxEngineError("INVALID_DEDUCTION", f"{section} requires a valid loan sanction date") from error


def calculate_80d(item, age_category: str) -> Decimal:
    self_limit = Decimal("50000") if age_category in {"senior", "super_senior"} else Decimal("25000")
    parent_limit = Decimal("50000") if item.parents_senior else Decimal("25000")
    return min(item.self_health_insurance + item.family_health_insurance, self_limit) + min(item.parents_health_insurance, parent_limit)


def calculate_deductions(profile: TaxProfileCreate, regime: str, salary: Decimal = ZERO, age_category: str = "individual", adjusted_total_income: Decimal = ZERO) -> Decimal:
    allowed = ALLOWED_NEW if regime == "new" else ALLOWED_OLD
    total = ZERO
    donations = []
    for item in profile.deductions:
        section = item.section.upper().replace(" ", "")
        if section not in allowed:
            continue
        if section == "80C":
            total += min(item.amount, Decimal("150000"))
        elif section == "80CCD(1B)":
            total += min(item.amount, Decimal("50000"))
        elif section == "80CCD(2)":
            if item.basic_salary <= ZERO:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80CCD(2) requires basic salary")
            base = item.basic_salary + item.dearness_allowance_for_retirement
            rate = Decimal("0.14") if regime == "new" or item.employer_is_government else Decimal("0.10")
            total += min(item.employer_contribution, base * rate)
        elif section == "80D":
            total += calculate_80d(item, age_category)
        elif section == "80TTA":
            if age_category in {"senior", "super_senior"}:
                raise TaxEngineError("INELIGIBLE_DEDUCTION", "80TTA is unavailable to senior citizens")
            total += min(item.amount, Decimal("10000"))
        elif section == "80TTB":
            if age_category not in {"senior", "super_senior"}:
                raise TaxEngineError("INELIGIBLE_DEDUCTION", "80TTB requires a derived senior age category")
            total += min(item.amount, Decimal("50000"))
        elif section == "80DD":
            if profile.residential_status != "resident" or item.is_dependent is False:
                raise TaxEngineError("INELIGIBLE_DEDUCTION", "80DD is for an eligible dependent, not the taxpayer")
            if item.is_dependent is not True or item.dependent_relationship is None or item.disability_percentage is None or item.disability_certificate_available is not True or item.medical_expenditure <= ZERO:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80DD requires an eligible dependent relationship, disability certificate, and maintenance or medical expenditure")
            total += Decimal("125000") if item.disability_percentage >= 80 else Decimal("75000")
        elif section == "80U":
            if profile.residential_status != "resident" or item.is_dependent is True:
                raise TaxEngineError("INELIGIBLE_DEDUCTION", "80U is for the taxpayer, not a dependent")
            if item.is_dependent is None or item.disability_percentage is None or item.disability_certificate_available is not True:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80U requires taxpayer disability certification")
            total += Decimal("125000") if item.disability_percentage >= 80 else Decimal("75000")
        elif section == "80DDB":
            if item.is_dependent is None or (item.is_dependent is True and item.dependent_relationship is None) or item.specified_disease is not True or item.medical_expenditure <= ZERO:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80DDB requires specified disease, patient relationship, and medical expenditure")
            eligible_expense = max(ZERO, item.medical_expenditure - item.reimbursement_amount)
            patient_age = age_category if item.is_dependent is False else item.dependent_age_category
            if patient_age is None:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80DDB requires the patient's age category")
            limit = Decimal("100000") if patient_age in {"senior", "super_senior"} else Decimal("40000")
            total += min(eligible_expense, limit)
        elif section == "80G":
            if not item.donation_category or item.donation_eligible is not True or item.donation_mode is None:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80G requires an eligible donee, donation category, and payment mode")
            if item.donation_mode == "cash" and item.amount > Decimal("2000"):
                raise TaxEngineError("INVALID_DEDUCTION", "80G cash donations above Rs 2,000 are not deductible")
            donations.append(item)
        elif section == "80GG":
            if item.annual_rent <= ZERO or adjusted_total_income <= ZERO or item.has_hra is not False or item.owns_residential_property_at_residence_or_work is not False or not item.form_10ba_acknowledgement:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80GG requires rent, no HRA, Form 10BA acknowledgement, and confirmation of no residence/work-location property")
            total += max(ZERO, min(item.annual_rent - adjusted_total_income * Decimal("0.10"), adjusted_total_income * Decimal("0.25"), Decimal("60000")))
        elif section == "80E":
            if item.education_loan_interest <= ZERO or item.education_loan_eligible is not True:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", "80E requires eligible education-loan interest")
            total += item.education_loan_interest
        elif section in {"80EE", "80EEA"}:
            if item.amount <= ZERO or item.loan_sanction_date is None or item.first_home_owner is not True or item.loan_from_financial_institution is not True or item.loan_amount <= ZERO or item.property_stamp_duty_value <= ZERO:
                raise TaxEngineError("INSUFFICIENT_DEDUCTION_DATA", f"{section} requires loan, property, and first-home metadata")
            sanctioned = parse_date(item.loan_sanction_date, section)
            if section == "80EE":
                eligible = date(2016, 4, 1) <= sanctioned <= date(2017, 3, 31) and item.loan_amount <= Decimal("3500000") and item.property_stamp_duty_value <= Decimal("5000000")
                limit = Decimal("50000")
            else:
                eligible = date(2019, 4, 1) <= sanctioned <= date(2022, 3, 31) and item.property_stamp_duty_value <= Decimal("4500000") and item.section_24b_limit_exhausted is True and not any(d.section.upper().replace(" ", "") == "80EE" for d in profile.deductions)
                limit = Decimal("150000")
            if not eligible:
                raise TaxEngineError("INELIGIBLE_DEDUCTION", f"{section} loan or property conditions are not met")
            total += min(item.amount, limit)
    qualifying_limit = max(ZERO, adjusted_total_income - total) * Decimal("0.10")
    qualifying_donations = [item for item in donations if item.donation_category in {"100_qualifying_limit", "50_qualifying_limit"}]
    for item in donations:
        if item.donation_category == "100_no_limit":
            total += item.amount
        elif item.donation_category == "50_no_limit":
            total += item.amount * Decimal("0.50")
    remaining_qualifying_limit = qualifying_limit
    for item in qualifying_donations:
        eligible_amount = min(item.amount, remaining_qualifying_limit)
        total += eligible_amount * (Decimal("1") if item.donation_category == "100_qualifying_limit" else Decimal("0.50"))
        remaining_qualifying_limit -= eligible_amount
    return total
