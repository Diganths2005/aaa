from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from tax_engine.calculator import calculate_tax
from tax_engine.deductions import ALLOWED_NEW, ALLOWED_OLD, calculate_deductions
from tax_engine.income import taxpayer_age_category
from tax_engine.models import TaxEngineError
from schemas.tax_profile import TaxProfileCreate

ZERO = Decimal("0")

SECTION_METADATA = {
    "80C": {
        "name": "Investments and savings",
        "requiredInformation": ["investment type", "annual contribution amount"],
        "requiredDocuments": ["PPF / EPF / LIC / ELSS / tuition-fee proof"],
    },
    "80CCD(1B)": {
        "name": "NPS contribution",
        "requiredInformation": ["NPS contribution amount"],
        "requiredDocuments": ["NPS contribution receipt"],
    },
    "80CCD(2)": {
        "name": "Employer NPS contribution",
        "requiredInformation": ["employer contribution and salary break-up"],
        "requiredDocuments": ["salary slip / employer certificate"],
    },
    "80D": {
        "name": "Health insurance",
        "requiredInformation": ["health insurance premium and insured persons"],
        "requiredDocuments": ["health insurance receipt"],
    },
    "80DD": {
        "name": "Disability dependent deduction",
        "requiredInformation": ["dependent relationship and disability details"],
        "requiredDocuments": ["disability certificate and medical expenditure proof"],
    },
    "80DDB": {
        "name": "Specified medical treatment",
        "requiredInformation": ["specified disease and medical expenditure"],
        "requiredDocuments": ["medical bills and diagnosis proof"],
    },
    "80E": {
        "name": "Education loan interest",
        "requiredInformation": ["education loan interest paid"],
        "requiredDocuments": ["education-loan certificate"],
    },
    "80EE": {
        "name": "Home loan interest (80EE)",
        "requiredInformation": ["loan sanction date, loan amount and property details"],
        "requiredDocuments": ["home loan sanction letter and property documents"],
    },
    "80EEA": {
        "name": "Affordable housing loan interest",
        "requiredInformation": ["loan sanction date, property value and first-home details"],
        "requiredDocuments": ["loan sanction letter and property valuation"],
    },
    "80G": {
        "name": "Charitable donations",
        "requiredInformation": ["donation amount, donee and payment mode"],
        "requiredDocuments": ["donation receipt and donee certificate"],
    },
    "80GG": {
        "name": "Rent paid without HRA",
        "requiredInformation": ["annual rent and rent proof"],
        "requiredDocuments": ["rent receipts and Form 10BA acknowledgement"],
    },
    "80TTA": {
        "name": "Savings account interest",
        "requiredInformation": ["savings-account interest earned"],
        "requiredDocuments": ["bank interest certificate"],
    },
    "80TTB": {
        "name": "Senior citizen interest deduction",
        "requiredInformation": ["senior citizen interest income"],
        "requiredDocuments": ["bank interest certificate"],
    },
    "80U": {
        "name": "Disability deduction for taxpayer",
        "requiredInformation": ["taxpayer disability percentage and certificate"],
        "requiredDocuments": ["medical disability certificate"],
    },
}

DEDUCTION_ORDER = [
    "80C",
    "80CCD(1B)",
    "80CCD(2)",
    "80D",
    "80DD",
    "80DDB",
    "80E",
    "80EE",
    "80EEA",
    "80G",
    "80GG",
    "80TTA",
    "80TTB",
    "80U",
]


def _normalize_section(section: str) -> str:
    value = (section or "").strip().upper().replace(" ", "")
    if value == "80CCD1B":
        return "80CCD(1B)"
    if value == "80CCD2":
        return "80CCD(2)"
    return value


def _coerce_decimal(value: Any) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value))


def _is_section_relevant(profile: TaxProfileCreate, section: str) -> bool:
    if section == "80C":
        return bool(profile.salary_income or profile.investments or profile.pension_income)
    if section == "80CCD(1B)":
        return bool(profile.salary_income or profile.pension_income or profile.employer_name)
    if section == "80CCD(2)":
        return bool(profile.salary_income and profile.employer_name)
    if section == "80D":
        return bool(profile.salary_income or profile.pension_income or profile.documents or profile.bank_accounts)
    if section == "80DD":
        return bool(profile.residential_status == "resident")
    if section == "80DDB":
        return bool(profile.salary_income or profile.pension_income or profile.documents)
    if section == "80E":
        return bool(profile.documents or profile.salary_income)
    if section in {"80EE", "80EEA"}:
        return bool(any(getattr(item, "home_loan_interest", 0) > 0 for item in profile.house_properties))
    if section == "80G":
        return bool(profile.residential_status == "resident")
    if section == "80GG":
        return bool(profile.house_properties or profile.salary_income)
    if section == "80TTA":
        return bool(profile.bank_accounts or any(item.income_type == "interest" for item in profile.other_income))
    if section == "80TTB":
        return bool(profile.is_senior_citizen or profile.date_of_birth)
    if section == "80U":
        return bool(profile.residential_status == "resident")
    return False


def _unknown_record(section: str, regime: str) -> dict[str, Any]:
    metadata = SECTION_METADATA.get(section, {"name": section, "requiredInformation": [], "requiredDocuments": []})
    return {
        "section": section,
        "name": metadata["name"],
        "claimedAmount": ZERO,
        "eligibleAmount": ZERO,
        "appliedAmount": ZERO,
        "regime": regime,
        "status": "UNKNOWN",
        "reasonCode": "INFO_REQUIRED",
        "explanation": f"TaxWise identified {metadata['name']} as potentially relevant to your profile. Confirm the required facts before eligibility is determined.",
        "requiredInformation": metadata["requiredInformation"],
        "requiredDocuments": metadata["requiredDocuments"],
        "source": "system",
        "confirmed": False,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }


def _not_applicable_record(section: str, regime: str, reason: str) -> dict[str, Any]:
    metadata = SECTION_METADATA.get(section, {"name": section, "requiredInformation": [], "requiredDocuments": []})
    return {
        "section": section,
        "name": metadata["name"],
        "claimedAmount": ZERO,
        "eligibleAmount": ZERO,
        "appliedAmount": ZERO,
        "regime": regime,
        "status": "NOT_APPLICABLE",
        "reasonCode": "REGIME_NOT_ALLOWED",
        "explanation": reason,
        "requiredInformation": metadata["requiredInformation"],
        "requiredDocuments": metadata["requiredDocuments"],
        "source": "system",
        "confirmed": False,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }


def _evaluate_existing_item(profile: TaxProfileCreate, item: Any, regime: str) -> dict[str, Any]:
    section = _normalize_section(item.section)
    metadata = SECTION_METADATA.get(section, {"name": section, "requiredInformation": [], "requiredDocuments": []})
    claimed = _coerce_decimal(getattr(item, "amount", 0))
    allowed = ALLOWED_NEW if regime == "new" else ALLOWED_OLD

    if section not in allowed:
        return {
            "section": section,
            "name": metadata["name"],
            "claimedAmount": claimed,
            "eligibleAmount": ZERO,
            "appliedAmount": ZERO,
            "regime": regime,
            "status": "NOT_APPLICABLE",
            "reasonCode": "REGIME_NOT_ALLOWED",
            "explanation": f"{section} is not available under the selected {regime} regime.",
            "requiredInformation": metadata["requiredInformation"],
            "requiredDocuments": metadata["requiredDocuments"],
            "source": "user",
            "confirmed": bool(claimed > ZERO),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

    age_category = taxpayer_age_category(profile)
    base_profile = profile.model_copy(update={"deductions": []})
    single_profile = profile.model_copy(update={"deductions": [item]})
    result = calculate_tax(base_profile, regime)
    adjusted_income = max(ZERO, result.gross_total_income - result.total_deductions)
    try:
        eligible = calculate_deductions(single_profile, regime, result.income_from_salary, age_category, adjusted_income)
        applied = max(ZERO, eligible)
        status = "CONFIRMED" if claimed > ZERO and applied > ZERO else "APPLIED" if applied > ZERO else "NOT_ELIGIBLE"
        if claimed <= ZERO:
            status = "NEEDS_INFORMATION"
        elif claimed > ZERO and applied <= ZERO:
            status = "NOT_ELIGIBLE"
        explanation = f"Your {section} amount is ₹{claimed:,.0f}, and the deterministic engine has calculated ₹{applied:,.0f} as eligible under the {regime} regime."
        if applied <= ZERO:
            explanation = f"{section} is being rejected by the deterministic tax engine for the current profile, so ₹0 is being applied."
        return {
            "section": section,
            "name": metadata["name"],
            "claimedAmount": claimed,
            "eligibleAmount": applied,
            "appliedAmount": applied,
            "regime": regime,
            "status": status,
            "reasonCode": "DETERMINISTIC_ELIGIBILITY_CHECK",
            "explanation": explanation,
            "requiredInformation": metadata["requiredInformation"],
            "requiredDocuments": metadata["requiredDocuments"],
            "source": "user",
            "confirmed": bool(claimed > ZERO),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }
    except TaxEngineError as exc:
        status = "NEEDS_INFORMATION" if exc.code == "INSUFFICIENT_DEDUCTION_DATA" else "NOT_ELIGIBLE"
        return {
            "section": section,
            "name": metadata["name"],
            "claimedAmount": claimed,
            "eligibleAmount": ZERO,
            "appliedAmount": ZERO,
            "regime": regime,
            "status": status,
            "reasonCode": exc.code,
            "explanation": exc.message,
            "requiredInformation": metadata["requiredInformation"],
            "requiredDocuments": metadata["requiredDocuments"],
            "source": "user",
            "confirmed": bool(claimed > ZERO),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }


def discover_deductions(profile: TaxProfileCreate, regime: str = "old") -> list[dict[str, Any]]:
    normalized_regime = regime.lower()
    if normalized_regime not in {"old", "new"}:
        normalized_regime = "old"

    records: list[dict[str, Any]] = []
    existing = {_normalize_section(str(item.section)): item for item in (profile.deductions or [])}
    for section in DEDUCTION_ORDER:
        if not _is_section_relevant(profile, section):
            continue
        if section in existing:
            records.append(_evaluate_existing_item(profile, existing[section], normalized_regime))
        else:
            records.append(_unknown_record(section, normalized_regime))

    if not records:
        return []
    return records


def summarize_discovery(deductions: list[dict[str, Any]]) -> dict[str, Any]:
    total_claimed = sum((Decimal(str(item["claimedAmount"])) for item in deductions), ZERO)
    total_eligible = sum((Decimal(str(item["eligibleAmount"])) for item in deductions), ZERO)
    total_applied = sum((Decimal(str(item["appliedAmount"])) for item in deductions), ZERO)
    potential = [item for item in deductions if item["status"] in {"UNKNOWN", "NEEDS_INFORMATION", "POTENTIALLY_ELIGIBLE", "ELIGIBLE"}]
    confirmed = [item for item in deductions if item["status"] in {"CONFIRMED", "APPLIED", "ELIGIBLE"}]
    return {
        "potentialDeductions": total_eligible,
        "confirmedDeductions": sum((Decimal(str(item["appliedAmount"])) for item in confirmed), ZERO),
        "appliedDeductions": total_applied,
        "potentialTaxImpact": max(ZERO, total_eligible - total_applied),
        "discoveryCount": len(deductions),
        "unknownCount": sum(1 for item in deductions if item["status"] == "UNKNOWN"),
        "needsInfoCount": sum(1 for item in deductions if item["status"] == "NEEDS_INFORMATION"),
        "potentialCount": len(potential),
    }
