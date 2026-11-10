from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Requirement:
    key: str
    label: str
    section: str
    required: bool = True


def _present(value: Any) -> bool:
    if value is None or value == "" or value == []:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _field(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def itr2_requirements(profile: dict[str, Any]) -> list[Requirement]:
    req = [
        Requirement("pan_number", "PAN", "Personal information"),
        Requirement("date_of_birth", "Date of birth", "Personal information"),
        Requirement("residential_status", "Residential status", "Personal information"),
        Requirement("citizenship", "Citizenship", "Personal information"),
        Requirement("address", "Residential address", "Personal information"),
        Requirement("pincode", "PIN code", "Personal information"),
        Requirement("employment_type", "Employment type", "Personal information"),
    ]

    salary = profile.get("salary_income") or []
    pension = profile.get("pension_income") or []
    if salary:
        for index, item in enumerate(salary, 1):
            prefix = f"salary_income.{index - 1}"
            req.extend([
                Requirement(f"{prefix}.employer_name", f"Salary #{index}: employer", "Salary"),
                Requirement(f"{prefix}.gross_salary", f"Salary #{index}: gross salary", "Salary"),
                Requirement(f"{prefix}.tds", f"Salary #{index}: TDS", "Salary", required=False),
            ])
    elif pension:
        for index, item in enumerate(pension, 1):
            prefix = f"pension_income.{index - 1}"
            req.extend([
                Requirement(f"{prefix}.payer_name", f"Pension #{index}: payer", "Salary"),
                Requirement(f"{prefix}.amount", f"Pension #{index}: amount", "Salary"),
            ])
    else:
        req.append(Requirement("income_source", "At least one supported income source", "Income"))

    for index, item in enumerate(profile.get("house_properties") or [], 1):
        prefix = f"house_properties.{index - 1}"
        req.extend([
            Requirement(f"{prefix}.property_type", f"Property #{index}: type", "House property"),
            Requirement(f"{prefix}.city", f"Property #{index}: location", "House property"),
            Requirement(f"{prefix}.ownership_share", f"Property #{index}: ownership", "House property"),
        ])
        if item.get("property_type") == "let_out" or item.get("annual_rent", 0):
            req.append(Requirement(f"{prefix}.annual_rent", f"Property #{index}: annual rent", "House property"))
        req.append(Requirement(f"{prefix}.municipal_tax", f"Property #{index}: municipal tax", "House property", required=False))
        if item.get("home_loan_interest", 0):
            req.append(Requirement(f"{prefix}.home_loan_interest", f"Property #{index}: home-loan interest", "House property"))

    for index, item in enumerate(profile.get("other_income") or [], 1):
        prefix = f"other_income.{index - 1}"
        req.extend([
            Requirement(f"{prefix}.income_type", f"Other income #{index}: type", "Other income"),
            Requirement(f"{prefix}.description", f"Other income #{index}: description", "Other income"),
            Requirement(f"{prefix}.amount", f"Other income #{index}: amount", "Other income"),
        ])

    for index, item in enumerate(profile.get("capital_gains") or [], 1):
        prefix = f"capital_gains.{index - 1}"
        req.extend([
            Requirement(f"{prefix}.asset_type", f"Capital gain #{index}: asset", "Capital gains"),
            Requirement(f"{prefix}.acquisition_date", f"Capital gain #{index}: acquisition date", "Capital gains"),
            Requirement(f"{prefix}.sale_date", f"Capital gain #{index}: sale date", "Capital gains"),
            Requirement(f"{prefix}.sale_consideration", f"Capital gain #{index}: sale consideration", "Capital gains"),
            Requirement(f"{prefix}.acquisition_cost", f"Capital gain #{index}: acquisition cost", "Capital gains"),
            Requirement(f"{prefix}.transfer_expenses", f"Capital gain #{index}: transfer expenses", "Capital gains", required=False),
        ])
        if item.get("asset_type") == "immovable_property":
            req.append(Requirement(f"{prefix}.improvement_cost", f"Capital gain #{index}: improvement cost", "Capital gains", required=False))

    for index, item in enumerate(profile.get("deductions") or [], 1):
        prefix = f"deductions.{index - 1}"
        req.extend([
            Requirement(f"{prefix}.section", f"Deduction #{index}: section", "Deductions"),
            Requirement(f"{prefix}.amount", f"Deduction #{index}: amount", "Deductions"),
        ])
        if item.get("section") == "80G":
            req.append(Requirement(f"{prefix}.donation_category", f"80G claim #{index}: donation category", "Deductions"))
            req.append(Requirement(f"{prefix}.donation_mode", f"80G claim #{index}: payment mode", "Deductions"))

    if profile.get("taxes_paid"):
        for index, item in enumerate(profile["taxes_paid"], 1):
            prefix = f"taxes_paid.{index - 1}"
            req.extend([
                Requirement(f"{prefix}.tax_type", f"Tax payment #{index}: type", "Taxes paid"),
                Requirement(f"{prefix}.amount", f"Tax payment #{index}: amount", "Taxes paid"),
            ])

    # A refund account is needed only when a bank account exists/has been supplied.
    if profile.get("bank_accounts"):
        for index, item in enumerate(profile["bank_accounts"], 1):
            prefix = f"bank_accounts.{index - 1}"
            req.extend([
                Requirement(f"{prefix}.bank_name", f"Bank #{index}: bank", "Bank"),
                Requirement(f"{prefix}.account_number", f"Bank #{index}: account number", "Bank"),
                Requirement(f"{prefix}.ifsc_code", f"Bank #{index}: IFSC", "Bank"),
                Requirement(f"{prefix}.is_primary", f"Bank #{index}: refund account selection", "Bank"),
            ])
    else:
        req.append(Requirement("bank_accounts", "At least one bank account", "Bank"))

    if profile.get("has_foreign_assets") or profile.get("has_foreign_income") or profile.get("foreign_income_assets"):
        for index, item in enumerate(profile.get("foreign_income_assets") or [], 1):
            prefix = f"foreign_income_assets.{index - 1}"
            req.extend([
                Requirement(f"{prefix}.country", f"Foreign item #{index}: country", "Foreign assets/income"),
                Requirement(f"{prefix}.item_type", f"Foreign item #{index}: type", "Foreign assets/income"),
                Requirement(f"{prefix}.description", f"Foreign item #{index}: description", "Foreign assets/income"),
                Requirement(f"{prefix}.value", f"Foreign item #{index}: value", "Foreign assets/income"),
            ])

    return req


def build_itr2_readiness(profile: dict[str, Any], *, extraction_candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    candidates = extraction_candidates or []
    confirmed = {item["field"]: item for item in candidates if not item.get("requires_confirmation", True) and item.get("status") == "confirmed"}
    warnings: list[dict[str, Any]] = []

    requirements = itr2_requirements(profile)
    items = []
    for requirement in requirements:
        value = _field(profile, requirement.key)
        source = None
        page = None
        confidence = None
        if _present(value):
            status = "complete"
        else:
            status = "missing"
            candidate = confirmed.get(requirement.key)
            if candidate:
                value = candidate.get("value")
                source = candidate.get("source")
                page = candidate.get("page")
                confidence = candidate.get("confidence")
                status = "complete"
            elif any(item.get("field") == requirement.key for item in candidates):
                status = "needs_confirmation"
                candidate = next(item for item in candidates if item.get("field") == requirement.key)
                source = candidate.get("source")
                page = candidate.get("page")
                confidence = candidate.get("confidence")
        items.append({
            "key": requirement.key,
            "label": requirement.label,
            "section": requirement.section,
            "required": requirement.required,
            "status": status,
            "value": value,
            "source": source,
            "page": page,
            "confidence": confidence,
        })

    required_items = [item for item in items if item["required"]]
    complete_required = [item for item in required_items if item["status"] == "complete"]
    missing = [item for item in required_items if item["status"] == "missing"]
    review = [item for item in required_items if item["status"] == "needs_confirmation"]

    # Only required fields contribute to the readiness percentage.
    percent = round(len(complete_required) / len(required_items) * 100) if required_items else 0
    ready = bool(required_items) and not missing and not review

    sections: dict[str, dict[str, Any]] = {}
    for item in items:
        section = sections.setdefault(item["section"], {"name": item["section"], "total": 0, "complete": 0, "missing": 0, "review": 0})
        section["total"] += 1
        if item["status"] == "complete":
            section["complete"] += 1
        elif item["status"] == "missing":
            section["missing"] += 1
        else:
            section["review"] += 1

    return {
        "itr": "ITR-2",
        "ready": ready,
        "completion_percentage": percent,
        "total_required": len(required_items),
        "complete_required": len(complete_required),
        "missing": missing,
        "needs_confirmation": review,
        "sections": list(sections.values()),
        "requirements": items,
        "warnings": warnings,
    }
