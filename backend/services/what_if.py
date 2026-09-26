from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from itr.eligibility import evaluate_itr_readiness
from itr.selection import select_itr
from schemas.tax_profile import TaxProfileCreate
from schemas.what_if import ScenarioChange, WhatIfScenarioRequest
from tax_engine.calculator import compare_regimes
from tax_engine.deductions import ALLOWED_NEW, ALLOWED_OLD, calculate_deductions
from tax_engine.income import taxpayer_age_category
from tax_engine.models import TaxEngineError


LIST_FIELDS = {
    "salary_income", "pension_income", "house_properties", "other_income",
    "capital_gains", "business_income", "foreign_income_assets", "investments",
    "deductions", "taxes_paid", "bank_accounts", "documents",
}
NUMERIC_FIELDS = {"date_of_birth"}


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError("Scenario value must be a valid number") from exc


def _numeric_attr(item: Any, name: str) -> Decimal:
    return _decimal(getattr(item, name, 0))


def _apply_list_change(items: list[Any], change: ScenarioChange) -> list[Any]:
    values = deepcopy(items)
    index = change.index
    if change.operation == "replace":
        if index is None:
            if isinstance(change.value, list):
                return deepcopy(change.value)
            if values:
                return [deepcopy(change.value)]
            return [deepcopy(change.value)]
        if index >= len(values):
            raise ValueError(f"Scenario index {index} is outside {change.field}")
        values[index] = deepcopy(change.value)
        return values
    if change.operation == "remove":
        if index is None:
            if isinstance(change.value, int) and 0 <= change.value < len(values):
                values.pop(change.value)
            else:
                values = [item for item in values if item != change.value]
        elif index < len(values):
            values.pop(index)
        return values
    if change.operation in {"add", "increase_by", "decrease_by"}:
        if change.operation == "add":
            values.extend(deepcopy(change.value if isinstance(change.value, list) else [change.value]))
            return values
        if index is None:
            if not values or not isinstance(change.value, (int, float, str, Decimal)):
                raise ValueError(f"{change.operation} requires an indexed numeric item for {change.field}")
            index = 0
        if index >= len(values):
            raise ValueError(f"Scenario index {index} is outside {change.field}")
        target = values[index]
        if not isinstance(target, dict):
            raise ValueError(f"{change.field} does not contain editable objects")

        preferred_key_order = {
            "salary_income": ["gross_salary", "standard_deduction", "professional_tax", "tds"],
            "pension_income": ["amount", "tds"],
            "house_properties": ["annual_rent", "home_loan_interest", "municipal_tax"],
            "other_income": ["amount", "tds"],
            "capital_gains": ["sale_consideration", "acquisition_cost", "improvement_cost", "transfer_expenses"],
            "deductions": ["amount", "self_health_insurance", "employer_contribution", "loan_amount", "annual_rent", "education_loan_interest", "medical_expenditure"],
            "taxes_paid": ["amount"],
            "investments": ["amount"],
            "documents": ["document_count"],
        }.get(change.field, [])

        numeric_fields = [
            key for key, item in target.items()
            if isinstance(item, (int, float, Decimal)) and key not in {"section"}
        ]
        key = next((field for field in preferred_key_order if field in target), None)
        if key is None:
            key = numeric_fields[0] if numeric_fields else None
        if key is None:
            raise ValueError(f"Specify a numeric field for {change.field} replacement instead")
        amount_value = _decimal(change.value)
        if amount_value < 0:
            raise ValueError("Scenario change values cannot be negative")
        amount = amount_value * (-1 if change.operation == "decrease_by" else 1)
        target[key] = _decimal(target.get(key, 0)) + amount
        if _decimal(target[key]) < 0:
            raise ValueError(f"{change.field}.{key} cannot be negative")
        return values
    raise ValueError(f"Unsupported operation {change.operation}")


def apply_changes(profile: TaxProfileCreate, changes: list[ScenarioChange]) -> TaxProfileCreate:
    data = profile.model_dump(mode="json")
    for change in changes:
        field = change.field
        if field == "regime":
            continue
        if field in LIST_FIELDS:
            data[field] = _apply_list_change(data.get(field, []), change)
            continue
        if field in {"has_business_income", "has_foreign_income", "has_foreign_assets", "has_unlisted_equity", "has_speculative_income", "has_carry_forward_loss"}:
            if change.operation not in {"replace", "add"}:
                raise ValueError(f"{change.operation} is not valid for boolean field {field}")
            data[field] = bool(change.value)
            continue
        if field not in data:
            raise ValueError(f"Unknown scenario field: {field}")
        current = data.get(field)
        if change.operation == "replace":
            data[field] = change.value
        elif change.operation in {"add", "increase_by", "decrease_by"}:
            amount = _decimal(change.value) * (-1 if change.operation == "decrease_by" else 1)
            data[field] = _decimal(current or 0) + amount
            if _decimal(data[field]) < 0:
                raise ValueError(f"{field} cannot be negative")
        elif change.operation == "remove":
            data[field] = None
    return TaxProfileCreate.model_validate(data)


def _result_summary(result: Any) -> dict[str, Any]:
    return {
        "regime": result.regime,
        "gross_total_income": result.gross_total_income,
        "taxable_income": result.taxable_income,
        "total_deductions": result.total_deductions,
        "total_tax_liability": result.total_tax_liability,
        "total_tax_paid": result.total_tax_paid,
        "refund": result.refund,
        "balance_payable": result.balance_payable,
    }


def _deduction_changes(profile: TaxProfileCreate, scenario: TaxProfileCreate, regime: str) -> list[dict[str, Any]]:
    baseline = {item.section.upper(): item.amount for item in profile.deductions}
    changed = {item.section.upper(): item.amount for item in scenario.deductions}
    sections = sorted(set(baseline) | set(changed))
    allowed = ALLOWED_NEW if regime == "new" else ALLOWED_OLD
    result = []
    for section in sections:
        claimed = changed.get(section, Decimal("0"))
        previous = baseline.get(section, Decimal("0"))
        if claimed == previous and section not in {item.section.upper() for item in scenario.deductions}:
            continue
        result.append({
            "section": section,
            "claimed": claimed,
            "baseline_claimed": previous,
            "applied": claimed if section in allowed else Decimal("0"),
            "regime": regime,
            "reason": "Applied by the deduction engine." if section in allowed else f"{section} is not available under the {regime} regime.",
        })
    return result


def simulate(profile: TaxProfileCreate, request: WhatIfScenarioRequest) -> dict[str, Any]:
    scenario_profile = apply_changes(profile, request.changes)
    selected_regime = request.regime or "new"
    baseline_comparison = compare_regimes(profile, allow_expanded_income=True)
    scenario_comparison = compare_regimes(scenario_profile, allow_expanded_income=True)
    baseline_result = baseline_comparison.old_regime if selected_regime == "old" else baseline_comparison.new_regime
    scenario_result = scenario_comparison.old_regime if selected_regime == "old" else scenario_comparison.new_regime
    baseline_itr = select_itr(profile)
    scenario_itr = select_itr(scenario_profile)
    baseline_decision = {"recommended_itr": baseline_itr.recommended_itr, "eligible": baseline_itr.eligible, "reasons": baseline_itr.reasons, "missing_information": baseline_itr.missing_information, "unsupported_conditions": baseline_itr.unsupported_conditions}
    scenario_decision = {"recommended_itr": scenario_itr.recommended_itr, "eligible": scenario_itr.eligible, "reasons": scenario_itr.reasons, "missing_information": scenario_itr.missing_information, "unsupported_conditions": scenario_itr.unsupported_conditions}
    baseline_readiness = evaluate_itr_readiness({"recommended_itr": baseline_itr.recommended_itr, "status": "eligible" if baseline_itr.eligible else "needs_information", "forms": {}})
    scenario_readiness = evaluate_itr_readiness({"recommended_itr": scenario_itr.recommended_itr, "status": "eligible" if scenario_itr.eligible else "needs_information", "forms": {}})
    comparison = {
        "regime": selected_regime,
        "income_difference": scenario_result.gross_total_income - baseline_result.gross_total_income,
        "tax_difference": scenario_result.total_tax_liability - baseline_result.total_tax_liability,
        "tax_paid_difference": scenario_result.total_tax_paid - baseline_result.total_tax_paid,
        "refund_difference": scenario_result.refund - baseline_result.refund,
        "payable_difference": scenario_result.balance_payable - baseline_result.balance_payable,
        "itr_changed": baseline_itr.recommended_itr != scenario_itr.recommended_itr,
    }
    comparison["baseline_regimes"] = {
        "old": _result_summary(baseline_comparison.old_regime),
        "new": _result_summary(baseline_comparison.new_regime),
        "recommended": baseline_comparison.recommended_regime,
    }
    comparison["what_if_regimes"] = {
        "old": _result_summary(scenario_comparison.old_regime),
        "new": _result_summary(scenario_comparison.new_regime),
        "recommended": scenario_comparison.recommended_regime,
    }
    explanation = {
        "changes": [change.model_dump(mode="json") for change in request.changes],
        "tax_impact": {"baseline": _result_summary(baseline_result), "what_if": _result_summary(scenario_result), "difference": comparison},
        "itr_change": {"baseline": baseline_decision, "what_if": scenario_decision, "reason": scenario_itr.reasons[0] if comparison["itr_changed"] and scenario_itr.reasons else None},
        "deduction_changes": _deduction_changes(profile, scenario_profile, selected_regime),
        "reasons": scenario_itr.reasons,
        "warnings": scenario_itr.unsupported_conditions + scenario_itr.missing_information,
    }
    return {"baseline": {"tax": _result_summary(baseline_result), "itr": baseline_decision, "readiness": baseline_readiness}, "what_if": {"tax": _result_summary(scenario_result), "itr": scenario_decision, "readiness": scenario_readiness, "profile": scenario_profile.model_dump(mode="json")}, "comparison": comparison, "explanation": explanation}
