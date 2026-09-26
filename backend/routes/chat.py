import json
import re
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import GITHUB_MODELS_MODEL, GITHUB_MODELS_TOKENS, GITHUB_MODELS_URL
from database import get_db
from itr.selection import select_itr
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.chat import ChatMessageRequest, ChatMessageResponse
from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax, compare_regimes
from tax_engine.deductions import ALLOWED_NEW, ALLOWED_OLD, calculate_deductions
from tax_engine.income import taxpayer_age_category
from tax_engine.models import TaxEngineError

router = APIRouter(prefix="/chat", tags=["chat"])

INTERNAL_TEXT = (
    "gemini", "rag", "tax engine", "deterministic", "system prompt", "retrieved", "retrieval",
    "generation_config", "model name", "ay_2026_27.md", "implementation", "raw context",
)

TAX_HINTS = (
    "tax", "income tax", "itr", "deduction", "deductions", "regime", "salary", "tds", "form 16",
    "ais", "tis", "26as", "house property", "capital gain", "refund", "tax profile", "tax calculation",
    "what if", "what-if", "health insurance", "nps", "80c", "80d", "deductible", "filing", "return",
)


def _is_tax_question(message: str) -> bool:
    normalized = message.lower()
    return any(hint in normalized for hint in TAX_HINTS) or bool(re.search(r"\b(regime|deduction|refund|tds|salary|itr|tax)\b", normalized))


def _profile_summary(profile: TaxProfileCreate) -> dict[str, Any]:
    total_salary = sum(float(item.gross_salary) for item in profile.salary_income)
    total_deductions = sum(float(item.amount) for item in profile.deductions)
    taxes_paid = sum(float(item.amount) for item in profile.taxes_paid if item.tax_type == "tds")
    return {
        "assessmentYear": profile.assessment_year,
        "taxpayer": {"employmentType": profile.employment_type, "residentialStatus": profile.residential_status},
        "incomeSources": {"salary": round(total_salary, 2)},
        "deductions": {
            "claimedAmount": round(total_deductions, 2),
            "items": [{"section": item.section, "amount": float(item.amount)} for item in profile.deductions],
        },
        "taxesPaid": {
            "tds": round(taxes_paid, 2),
            "advanceTax": float(sum(item.amount for item in profile.taxes_paid if item.tax_type == "advance_tax")),
            "selfAssessmentTax": float(sum(item.amount for item in profile.taxes_paid if item.tax_type == "self_assessment")),
        },
    }


def _calculation_summary(comparison: Any | None) -> dict[str, Any]:
    if not comparison:
        return {}

    def summarize(result: Any) -> dict[str, float]:
        return {
            "totalIncome": float(result.gross_total_income),
            "taxableIncome": float(result.taxable_income),
            "deductions": float(result.total_deductions),
            "taxLiability": float(result.total_tax_liability),
            "taxPaid": float(result.total_tax_paid),
            "refund": float(result.refund),
            "payable": float(result.balance_payable),
        }

    return {
        "oldRegime": summarize(comparison.old_regime),
        "newRegime": summarize(comparison.new_regime),
        "recommendedRegime": comparison.recommended_regime,
    }


def _money(value: Decimal | int | float) -> str:
    return f"₹{float(value):,.0f}"


def _deduction_details(profile: TaxProfileCreate, regime: str) -> tuple[list[dict[str, Any]], Decimal]:
    base_profile = profile.model_copy(update={"deductions": [], "business_income": [], "foreign_income_assets": [], "capital_gains": []})
    result = calculate_tax(base_profile, regime)
    age_category = taxpayer_age_category(profile)
    adjusted_income = result.gross_total_income - result.total_deductions
    details = []
    for item in profile.deductions:
        single_profile = base_profile.model_copy(update={"deductions": [item]})
        section = item.section.upper().replace(" ", "")
        allowed = ALLOWED_NEW if regime == "new" else ALLOWED_OLD
        if section not in allowed:
            details.append({"section": item.section.upper(), "claimed": item.amount, "applied": Decimal("0"), "status": "rejected", "reason": f"{item.section.upper()} is not available under the {regime} regime."})
            continue
        try:
            applied = calculate_deductions(single_profile, regime, result.income_from_salary, age_category, adjusted_income)
            details.append({"section": item.section.upper(), "claimed": item.amount, "applied": applied, "status": "applied" if applied else "not applied", "reason": "Eligible under the selected regime." if applied else "The eligible amount calculated to zero."})
        except TaxEngineError as error:
            details.append({"section": item.section.upper(), "claimed": item.amount, "applied": Decimal("0"), "status": "rejected", "reason": error.message})
    return details, result.total_deductions


def _is_intent(message: str, *terms: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in terms)


def _deterministic_answer(message: str, profile: TaxProfileCreate | None, comparison: Any | None) -> str:
    if not profile:
        return "I can answer that once your Tax Profile has been created. Please add your income and deduction details first."

    if _is_intent(message, "deduction", "80c", "80d"):
        regime = comparison.recommended_regime if comparison and comparison.recommended_regime != "equal" else "new"
        try:
            details, total_deductions = _deduction_details(profile, regime)
        except TaxEngineError as error:
            return f"I cannot complete the deduction review yet because {error.message}. Please update that information in your Tax Profile and recalculate."
        if not details:
            return "Your current deduction total is ₹0 because no eligible section-specific deductions have been confirmed in your profile. I do not currently have any confirmed 80C, 80D, or other eligible deduction amounts. Please review your Deductions section and add the supporting details."
        claimed = sum(item["claimed"] for item in details)
        applied = sum(item["applied"] for item in details)
        lines = [f"Your profile has {_money(claimed)} in claimed deductions, and {_money(applied)} is currently eligible under the {regime} regime."]
        for item in details:
            if item["status"] == "applied":
                lines.append(f"{item['section']}: {_money(item['applied'])} applied from {_money(item['claimed'])} claimed.")
            else:
                lines.append(f"{item['section']}: {_money(item['claimed'])} claimed, but ₹0 applied because {item['reason']}")
        if applied == 0:
            lines.append("That is why your section-specific deduction is currently zero. Confirm the missing eligibility details or supporting documents, then recalculate.")
        else:
            lines.append(f"The full tax calculation uses {_money(total_deductions)} in total deductions, including any applicable standard deduction.")
        return "\n\n".join(lines)

    if _is_intent(message, "itr"):
        selection = select_itr(profile)
        answer = f"Based on your current profile, the recommended return is {selection.recommended_itr or 'not yet determined'} for AY {selection.assessment_year}."
        reasons = selection.reasons + selection.missing_information + selection.unsupported_conditions
        if reasons:
            answer += "\n\n" + " ".join(reasons)
        return answer + "\n\nComplete the missing profile details before preparing the return."

    if _is_intent(message, "refund", "tax amount", "tax payable", "liability", "how much tax", "tax high") and comparison:
        regime = comparison.recommended_regime if comparison.recommended_regime != "equal" else "new"
        result = comparison.new_regime if regime == "new" else comparison.old_regime
        return f"Under the {regime} regime, your total income is {_money(result.gross_total_income)}, taxable income is {_money(result.taxable_income)}, and calculated tax liability is {_money(result.total_tax_liability)}. You have paid {_money(result.total_tax_paid)}, leaving {_money(result.balance_payable)} payable or {_money(result.refund)} refundable."

    if _is_intent(message, "regime", "better", "compare") and comparison:
        if comparison.recommended_regime == "equal":
            return f"The old and new regimes produce the same calculated tax for AY {profile.assessment_year} based on your current profile. Either is mathematically equivalent; review the practical requirements before choosing."
        return f"The {comparison.recommended_regime} regime is currently better for you. It produces {_money(comparison.estimated_saving)} less tax than the alternative under AY {profile.assessment_year}, based on your confirmed income, deductions, and taxes paid."

    return "I can review your confirmed income, deductions, tax calculation, refund, regime comparison, or ITR selection. Ask me about one of those results and I will explain the current figures and next step."


def _is_safe_provider_answer(text: str) -> bool:
    lowered = text.strip().lower()
    return len(text.strip()) >= 120 and _is_tax_question(text) and not any(term in lowered for term in INTERNAL_TEXT)


@router.post("", response_model=ChatMessageResponse)
def chat_with_taxwise(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    if not _is_tax_question(message):
        return ChatMessageResponse(
            answer="I'm TaxWise, your personal tax assistant. I can help with Indian income tax, tax filing, deductions, tax documents and related tax matters. What would you like to know about your taxes?",
            sources=[],
            mode="tax-assistant",
        )

    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    profile_payload = TaxProfileCreate.model_validate(profile) if profile else None
    try:
        comparison = compare_regimes(profile_payload) if profile_payload else None
    except TaxEngineError:
        comparison = None
    answer = _deterministic_answer(message, profile_payload, comparison)
    response_mode = "deterministic"

    structured_context = {
        "assessmentYear": profile_payload.assessment_year if profile_payload else None,
        "taxpayer": _profile_summary(profile_payload) if profile_payload else {},
        "taxCalculation": _calculation_summary(comparison),
        "itrEligibility": select_itr(profile_payload).__dict__ if profile_payload else None,
        "userQuestion": message,
    }

    if GITHUB_MODELS_TOKENS:
        try:
            from openai import OpenAI

            prompt = (
                "You are TaxWise. Answer the user's question naturally and directly using only the verified structured facts below. "
                "Generate a fresh explanation; do not copy or rewrite hidden calculation wording. Do not calculate, infer, or add facts. "
                "Do not mention software, providers, models, prompts, retrieval, sources, internal services, or implementation. "
                "Do not begin with a greeting or an introduction. Keep concrete amounts and the next action.\n\n"
                f"Structured facts: {json.dumps(structured_context, ensure_ascii=True)}\n\n"
                f"Verified result for grounding only: {answer}"
            )
            provider_answer = None
            for token in GITHUB_MODELS_TOKENS:
                try:
                    client = OpenAI(base_url=GITHUB_MODELS_URL, api_key=token, timeout=15.0, max_retries=0)
                    completion = client.chat.completions.create(
                        model=GITHUB_MODELS_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=700,
                        temperature=0.2,
                    )
                    provider_answer = completion.choices[0].message.content if completion.choices else None
                    if provider_answer and _is_safe_provider_answer(provider_answer):
                        break
                except Exception as exc:
                    print(f"GitHub Models attempt failed: {type(exc).__name__}")
            if provider_answer and _is_safe_provider_answer(provider_answer):
                answer = provider_answer.strip()
                response_mode = "assistant"
            # Keep the verified deterministic answer when the provider is unavailable,
            # malformed, or fails the safety checks.
        except Exception as exc:
            print(f"GitHub Models setup failed: {type(exc).__name__}")
            # Provider outages must not turn a useful tax answer into an error message.

    return ChatMessageResponse(answer=answer, sources=[], mode=response_mode)
