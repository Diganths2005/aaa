from __future__ import annotations

from typing import Any

from schemas.tax_profile import TaxProfileCreate


REASON_TEXT = {
    "SALARY_ONLY": "Salary or pension income is the main profile signal for ITR-1.",
    "CAPITAL_GAINS_PRESENT": "Capital-gain transactions are present and make ITR-1 unsuitable.",
    "BUSINESS_INCOME_PRESENT": "Business or professional income is present.",
    "PROFESSIONAL_INCOME_PRESENT": "Professional income is present and normally requires ITR-3.",
    "PRESUMPTIVE_INCOME_PRESENT": "Presumptive business or professional income is present.",
    "FOREIGN_ASSET_PRESENT": "Foreign assets or foreign income require a higher-return treatment.",
    "FOREIGN_INCOME_PRESENT": "Foreign income is present.",
    "UNLISTED_SHARES_PRESENT": "Unlisted-equity situations are outside the supported ITR-1 scope.",
    "DIRECTORSHIP_PRESENT": "Directorship situations are outside the supported ITR-1 scope.",
    "MULTIPLE_HOUSE_PROPERTIES": "Multiple property scenarios are not supported in the simple ITR-1 path.",
    "INCOME_LIMIT_EXCEEDED": "The income profile exceeds the supported ITR-1 conditions.",
    "TAXPAYER_TYPE_NOT_SUPPORTED": "The taxpayer profile is outside the supported ITR-1 path.",
    "MISSING_REQUIRED_INFORMATION": "Required information is missing for a deterministic decision.",
    "PRESUMPTIVE_CONDITIONS_NOT_MET": "The presumptive requirements are not satisfied for ITR-4.",
    "NO_SUPPORTED_ITR": "No supported ITR form is currently eligible for this profile.",
}


def _base_form_result() -> dict[str, Any]:
    return {
        "eligible": False,
        "recommended": False,
        "status": "not_eligible",
        "reasonCodes": [],
        "reasons": [],
        "missingInformation": [],
        "unsupportedConditions": [],
    }


def _add_reason(result: dict[str, Any], code: str, detail: str | None = None):
    result["reasonCodes"].append(code)
    if detail is None:
        detail = REASON_TEXT.get(code, code)
    result["reasons"].append(detail)


def _status_for(result: dict[str, Any], default: str) -> str:
    if result["eligible"]:
        return "eligible"
    if result["missingInformation"]:
        return "needs_information"
    return default


def _evaluate_itr1(profile: TaxProfileCreate) -> dict[str, Any]:
    result = _base_form_result()
    has_business = bool(profile.business_income or profile.has_business_income)
    has_capital_gains = bool(profile.capital_gains)
    has_foreign = bool(profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income)
    has_unlisted = bool(profile.has_unlisted_equity)
    has_speculative = bool(profile.has_speculative_income)
    has_salary_or_pension = bool(profile.salary_income or profile.pension_income)

    if profile.assessment_year != "2026-27":
        _add_reason(result, "TAXPAYER_TYPE_NOT_SUPPORTED", "Only AY 2026-27 is currently supported.")
    if profile.residential_status != "resident":
        _add_reason(result, "TAXPAYER_TYPE_NOT_SUPPORTED", "ITR-1 is currently supported only for resident taxpayers in this workflow.")
    if has_business:
        _add_reason(result, "BUSINESS_INCOME_PRESENT", "Business or professional income requires a different ITR form.")
    if has_foreign:
        _add_reason(result, "FOREIGN_INCOME_PRESENT", "Foreign income or assets are outside the supported ITR-1 scope.")
    if has_capital_gains:
        _add_reason(result, "CAPITAL_GAINS_PRESENT", "Capital gains are outside the supported ITR-1 scope.")
    if has_speculative:
        _add_reason(result, "TAXPAYER_TYPE_NOT_SUPPORTED", "Speculative income requires a different ITR form.")
    if has_unlisted:
        _add_reason(result, "UNLISTED_SHARES_PRESENT", "Unlisted equity is outside the supported ITR-1 scope.")
    if not has_salary_or_pension:
        result["missingInformation"].append("salary_or_pension_income")
        _add_reason(result, "MISSING_REQUIRED_INFORMATION", "Salary or pension income is required before ITR-1 can be accepted.")

    if not result["reasonCodes"] and not result["missingInformation"]:
        result["eligible"] = True
        result["status"] = "eligible"
    else:
        result["status"] = _status_for(result, "not_eligible")
    return result


def _evaluate_itr2(profile: TaxProfileCreate) -> dict[str, Any]:
    result = _base_form_result()
    has_business = bool(profile.business_income or profile.has_business_income)
    has_capital_gains = bool(profile.capital_gains)
    has_foreign = bool(profile.foreign_income_assets or profile.has_foreign_assets or profile.has_foreign_income)
    has_supported_non_salary = bool(profile.house_properties or profile.other_income or has_capital_gains or has_foreign)
    has_salary_or_pension = bool(profile.salary_income or profile.pension_income)

    if has_business:
        _add_reason(result, "BUSINESS_INCOME_PRESENT", "Business income disqualifies the simple ITR-2 path in this workflow.")
    if not has_salary_or_pension and not has_supported_non_salary:
        result["missingInformation"].append("income_source")
        _add_reason(result, "MISSING_REQUIRED_INFORMATION", "Add a supported income source to evaluate ITR-2.")
    if profile.has_speculative_income:
        _add_reason(result, "TAXPAYER_TYPE_NOT_SUPPORTED", "Speculative income is outside the supported ITR-2 path.")
    if profile.has_unlisted_equity:
        _add_reason(result, "UNLISTED_SHARES_PRESENT", "Unlisted equity is outside the supported ITR-2 scope.")

    should_be_eligible = (has_capital_gains or has_foreign or has_supported_non_salary) and not has_business and not profile.has_speculative_income and not profile.has_unlisted_equity
    if should_be_eligible:
        result["eligible"] = True
        result["status"] = "eligible"
        if has_capital_gains:
            _add_reason(result, "CAPITAL_GAINS_PRESENT", "Capital-gain transactions make ITR-2 the relevant family for this profile.")
        if has_foreign:
            _add_reason(result, "FOREIGN_INCOME_PRESENT", "Foreign income or assets are supported under ITR-2.")
    else:
        result["status"] = _status_for(result, "not_eligible")
    return result


def _evaluate_itr3(profile: TaxProfileCreate) -> dict[str, Any]:
    result = _base_form_result()
    has_business = bool(profile.business_income or profile.has_business_income)
    if has_business:
        result["eligible"] = True
        result["status"] = "eligible"
        _add_reason(result, "BUSINESS_INCOME_PRESENT", "Business or professional income is present and can match ITR-3.")
    if profile.has_speculative_income:
        _add_reason(result, "TAXPAYER_TYPE_NOT_SUPPORTED", "Speculative income is outside the supported ITR-3 path.")
    if not has_business:
        result["missingInformation"].append("business_or_professional_income")
        _add_reason(result, "MISSING_REQUIRED_INFORMATION", "Business or professional income data is required before ITR-3 can be determined.")
        result["status"] = _status_for(result, "not_eligible")
    return result


def _evaluate_itr4(profile: TaxProfileCreate) -> dict[str, Any]:
    result = _base_form_result()
    presumptive = bool(profile.business_income) and all(item.presumptive_section for item in profile.business_income)
    if not presumptive:
        _add_reason(result, "PRESUMPTIVE_CONDITIONS_NOT_MET", "Presumptive conditions are not satisfied for ITR-4.")
    if profile.capital_gains:
        _add_reason(result, "CAPITAL_GAINS_PRESENT", "Capital gains prevent ITR-4 from being the recommended form.")
    if profile.foreign_income_assets or profile.has_foreign_income or profile.has_foreign_assets:
        _add_reason(result, "FOREIGN_ASSET_PRESENT", "Foreign income/assets are not supported under ITR-4 in this workflow.")
    if profile.has_unlisted_equity:
        _add_reason(result, "UNLISTED_SHARES_PRESENT", "Unlisted equity disqualifies the simple ITR-4 path.")

    if presumptive and not result["reasonCodes"]:
        result["eligible"] = True
        result["status"] = "eligible"
    else:
        result["status"] = _status_for(result, "not_eligible")
    return result


def build_itr_decision(profile: TaxProfileCreate) -> dict[str, Any]:
    forms = {
        "ITR-1": _evaluate_itr1(profile),
        "ITR-2": _evaluate_itr2(profile),
        "ITR-3": _evaluate_itr3(profile),
        "ITR-4": _evaluate_itr4(profile),
    }

    recommended = None
    for name in ["ITR-4", "ITR-3", "ITR-2", "ITR-1"]:
        form = forms[name]
        if form["eligible"]:
            recommended = name
            status = "eligible"
            break
    else:
        status = "needs_information" if any(form["missingInformation"] for form in forms.values()) else "not_eligible"

    for name, form in forms.items():
        form["recommended"] = name == recommended

    result = {
        "assessment_year": profile.assessment_year,
        "status": status,
        "recommended_itr": recommended,
        "forms": forms,
    }
    return result


def evaluate_itr_readiness(decision: dict[str, Any]) -> dict[str, Any]:
    recommended = decision.get("recommended_itr")
    if recommended:
        form_result = (decision.get("forms") or {}).get(recommended, {})
        missing_fields = form_result.get("missingInformation", [])
    else:
        missing_fields = []
        for form_result in (decision.get("forms") or {}).values():
            missing_fields.extend(form_result.get("missingInformation", []))
        missing_fields = list(dict.fromkeys(missing_fields))

    ready = bool(recommended and not missing_fields and decision.get("status") == "eligible")
    completion = 100 if ready else (60 if recommended else 0)
    return {
        "itr": recommended,
        "eligible": decision.get("status") == "eligible",
        "recommended": bool(recommended),
        "ready": ready,
        "missing_fields": missing_fields,
        "completion_percentage": completion,
    }
