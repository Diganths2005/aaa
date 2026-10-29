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
from services.knowledge import LocalTaxKnowledgeBase, RetrievalFilter
from services.semantic_rag import SemanticKnowledgeBase, SemanticRAGUnavailable

router = APIRouter(prefix="/chat", tags=["chat"])

INTERNAL_TEXT = (
    "gemini", "tax engine", "deterministic", "system prompt", "retrieved", "retrieval",
    "generation_config", "model name", "implementation", "raw context",
)

TAX_HINTS = (
    "tax", "income tax", "itr", "deduction", "deductions", "regime", "salary", "tds", "form 16",
    "ais", "tis", "26as", "house property", "capital gain", "refund", "tax profile", "tax calculation",
    "what if", "what-if", "health insurance", "nps", "80c", "80d", "deductible", "filing", "return",
    "uploaded", "document", "form 16", "form-16", "26as", "ais", "tis", "bank statement",
    "investment statement",
)


def _is_tax_question(message: str) -> bool:
    normalized = message.lower()
    return any(hint in normalized for hint in TAX_HINTS) or bool(re.search(r"\b(regime|deduction|refund|tds|salary|itr|tax|rebate|cess|pension)\b", normalized))


def _requires_calculation(message: str) -> bool:
    normalized = message.lower()
    explicit_deduction_claim = (
        "claim" in normalized
        and any(term in normalized for term in ("deduction", "80c", "80d", "80ccd", "80tta", "80ttb", "80e", "80g"))
    )
    return explicit_deduction_claim or any(term in normalized for term in (
        "my tax", "my refund", "my payable", "my liability", "how much", "tax amount", "tax high",
        "which regime", "regime is better", "compare regimes", "my deduction", "my tds", "my itr", "why itr",
        "why is my", "why does my", "what is my", "am i ready", "which itr", "what itr", "itr do i",
        "itr should i", "eligible for itr", "my deductions", "deductions for me", "am i eligible for deductions",
        "what deductions may i be eligible for", "why can't i claim", "why cannot i claim", "why can’t i claim",
        "why can not i claim",
    ))


def _asks_about_uploaded_documents(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in (
        "document", "uploaded", "form 16", "form-16", "26as", "ais", "tis",
        "bank statement", "investment statement", "my statement",
    ))


def _out_of_scope_answer() -> str:
    return "That question is outside the tax topics and return scenarios currently covered by TaxWise. I can answer using the supported AY 2026-27 tax rules and confirmed profile calculations."


def _knowledge_answer(knowledge: list[str]) -> str:
    excerpts = [re.sub(r"(?m)^#{1,6}\s*", "", item).replace("`", "").strip() for item in knowledge[:2]]
    return "\n\n".join(excerpts)


def _profile_summary(profile: TaxProfileCreate) -> dict[str, Any]:
    total_salary = sum(float(item.gross_salary) for item in profile.salary_income)
    total_deductions = sum(float(item.amount) for item in profile.deductions)
    taxes_paid = sum(float(item.amount) for item in profile.taxes_paid if item.tax_type == "tds")
    if not taxes_paid:
        taxes_paid = sum(float(item.tds) for item in (*profile.salary_income, *profile.pension_income, *profile.other_income))
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

    def summarize(result: Any) -> dict[str, Any]:
        return {
            "totalIncome": float(result.gross_total_income),
            "taxableIncome": float(result.taxable_income),
            "deductions": float(result.total_deductions),
            "taxBeforeRebate": float(result.tax_before_rebate),
            "rebate": float(result.rebate),
            "taxAfterRebate": float(result.tax_after_rebate),
            "surcharge": float(result.surcharge),
            "cess": float(result.cess),
            "taxLiability": float(result.total_tax_liability),
            "taxPaid": float(result.total_tax_paid),
            "refund": float(result.refund),
            "payable": float(result.balance_payable),
            "slabCalculation": [
                {
                    "lowerBound": float(step.lower_bound),
                    "upperBound": float(step.upper_bound) if step.upper_bound is not None else None,
                    "rate": float(step.rate),
                    "taxableAmount": float(step.taxable_amount),
                    "tax": float(step.tax),
                }
                for step in result.slab_calculation
            ],
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


def _tax_explanation(result: Any, regime: str) -> str:
    lines = [
        f"Your AY {result.assessment_year} calculation uses the {regime} regime.",
        f"Gross total income: {_money(result.gross_total_income)}.",
        f"Total deductions, including any standard deduction: {_money(result.total_deductions)}.",
        f"Taxable income: {_money(result.taxable_income)}.",
        "Slab calculation:",
    ]
    if result.slab_calculation:
        for step in result.slab_calculation:
            band = f"above {_money(step.lower_bound)}" if step.upper_bound is None else f"from {_money(step.lower_bound)} to {_money(step.upper_bound)}"
            lines.append(f"{band}: {_money(step.taxable_amount)} taxed at {step.rate * 100}% gives {_money(step.tax)}.")
    else:
        lines.append("No ordinary income fell into a taxable slab.")
    lines.extend([
        f"Tax before rebate: {_money(result.tax_before_rebate)}.",
        f"Rebate: {_money(result.rebate)}; tax after rebate: {_money(result.tax_after_rebate)}.",
        f"Surcharge: {_money(result.surcharge)}; cess: {_money(result.cess)}.",
        f"Final tax liability: {_money(result.total_tax_liability)}.",
        f"Taxes already paid: {_money(result.total_tax_paid)} (TDS {_money(result.tds)}, advance tax {_money(result.advance_tax)}, self-assessment tax {_money(result.self_assessment_tax)}).",
        f"Result after payments: {_money(result.refund)} refund or {_money(result.balance_payable)} payable.",
    ])
    return "\n\n".join(lines)


def _is_intent(message: str, *terms: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in terms)


def _deterministic_answer(message: str, profile: TaxProfileCreate | None, comparison: Any | None, knowledge: list[str] | None = None) -> str:
    if not profile:
        return _knowledge_answer(knowledge) if knowledge else _out_of_scope_answer()

    lowered = message.lower()
    profile_question = _requires_calculation(message) or bool(re.search(r"\b(my|mine|me)\b", lowered))
    selected_regime = comparison.recommended_regime if comparison and comparison.recommended_regime != "equal" else "new"
    selected_result = comparison.new_regime if comparison and selected_regime == "new" else comparison.old_regime if comparison else None

    if profile_question and _is_intent(message, "deduction", "80c", "80d"):
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

    if profile_question and _is_intent(message, "claim", "deduction"):
        regime = comparison.recommended_regime if comparison and comparison.recommended_regime != "equal" else "new"
        try:
            details, _ = _deduction_details(profile, regime)
        except TaxEngineError as error:
            return f"I cannot complete that deduction review yet because {error.message}. Please update the missing details in your Tax Profile and recalculate."

        target_sections = []
        lowered = message.lower()
        for section in ["80c", "80ccd(2)", "80d", "80tta", "80ttb", "80e", "80g"]:
            if section in lowered:
                target_sections.append(section)
        if not target_sections:
            target_sections = [item["section"].lower() for item in details if item["status"] == "rejected"]

        for item in details:
            item_section = item["section"].lower()
            if any(section in item_section or item_section in section for section in target_sections):
                if item["status"] == "rejected":
                    reason = item["reason"]
                    if reason.lower().startswith("80ccd(2)"):
                        reason = "80CCD(2) requires basic salary and employer contribution details to calculate the eligible amount."
                    return f"{item['section']} is not available or not eligible in the current profile. {reason}"
                if item["applied"] == 0:
                    return f"{item['section']} is in the profile, but the engine calculated ₹0 as eligible. {item['reason']}"

        return _knowledge_answer(knowledge) if knowledge else _out_of_scope_answer()

    if profile_question and _is_intent(message, "itr"):
        selection = select_itr(profile)
        answer = f"Based on your current profile, the recommended return is {selection.recommended_itr or 'not yet determined'} for AY {selection.assessment_year}."
        reasons = selection.reasons + selection.missing_information + selection.unsupported_conditions
        if reasons:
            answer += "\n\n" + " ".join(reasons)
        return answer + "\n\nComplete the missing profile details before preparing the return."

    if profile_question and selected_result and _is_intent(message, "tds"):
        return f"Your profile records {_money(selected_result.tds)} of TDS under the {selected_regime} calculation. Total recorded taxes paid are {_money(selected_result.total_tax_paid)}."

    if profile_question and selected_result and _is_intent(message, "taxable income"):
        return f"Your taxable income under the {selected_regime} regime is {_money(selected_result.taxable_income)}. It includes ordinary taxable income of {_money(selected_result.ordinary_taxable_income)} and supported special-rate capital gains of {_money(selected_result.capital_gains.special_rate_capital_gain)}."

    if profile_question and selected_result and _is_intent(message, "salary", "pension"):
        return f"Your confirmed profile includes {_money(selected_result.income_from_salary)} in salary and {_money(selected_result.income_from_pension)} in pension income. The calculation applies the {selected_regime} regime rules."

    if profile_question and selected_result and _is_intent(message, "rebate"):
        return f"The deterministic {selected_regime} calculation applied a rebate of {_money(selected_result.rebate)}. Tax before rebate was {_money(selected_result.tax_before_rebate)} and tax after rebate was {_money(selected_result.tax_after_rebate)}."

    if profile_question and selected_result and _is_intent(message, "cess"):
        return f"The deterministic {selected_regime} calculation applied {_money(selected_result.cess)} in cess after rebate and surcharge. Tax after rebate was {_money(selected_result.tax_after_rebate)} and surcharge was {_money(selected_result.surcharge)}."

    if comparison and "tax" in message.lower() and (
        "why" in message.lower() or _is_intent(message, "explain", "breakdown", "calculation steps")
    ):
        regime = comparison.recommended_regime if comparison.recommended_regime != "equal" else "new"
        result = comparison.new_regime if regime == "new" else comparison.old_regime
        return _tax_explanation(result, regime)

    if profile_question and _is_intent(message, "refund", "tax amount", "tax payable", "liability", "how much tax", "tax high") and comparison:
        return f"Under the {selected_regime} regime, your total income is {_money(selected_result.gross_total_income)}, taxable income is {_money(selected_result.taxable_income)}, and calculated tax liability is {_money(selected_result.total_tax_liability)}. You have paid {_money(selected_result.total_tax_paid)}, leaving {_money(selected_result.balance_payable)} payable or {_money(selected_result.refund)} refundable."

    if profile_question and _is_intent(message, "regime", "better", "compare") and comparison:
        if comparison.recommended_regime == "equal":
            return f"The old and new regimes produce the same calculated tax for AY {profile.assessment_year} based on your current profile. Either is mathematically equivalent; review the practical requirements before choosing."
        return f"The {comparison.recommended_regime} regime is currently better for you. It produces {_money(comparison.estimated_saving)} less tax than the alternative under AY {profile.assessment_year}, based on your confirmed income, deductions, and taxes paid."

    return _knowledge_answer(knowledge) if knowledge else _out_of_scope_answer()


def _is_safe_provider_answer(text: str, verified_context: dict[str, Any] | None = None) -> bool:
    lowered = text.strip().lower()
    if len(text.strip()) < 120 or not _is_tax_question(text) or any(term in lowered for term in INTERNAL_TEXT):
        return False
    if verified_context is None:
        return True

    verified_numbers: set[Decimal] = set()

    def add_numbers(value: str) -> None:
        for match in re.finditer(r"(?<![A-Za-z])(\d[\d,]*(?:\.\d+)?)(%)?", value):
            number = Decimal(match.group(1).replace(",", ""))
            verified_numbers.add(number / 100 if match.group(2) else number)

    def collect_numbers(value: Any) -> None:
        if isinstance(value, dict):
            for nested in value.values():
                collect_numbers(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                collect_numbers(nested)
        elif isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            verified_numbers.add(Decimal(str(value)))
        elif isinstance(value, str):
            add_numbers(value)

    collect_numbers(verified_context)
    for match in re.finditer(r"(?<![A-Za-z])(\d[\d,]*(?:\.\d+)?)(%)?", text):
        number = Decimal(match.group(1).replace(",", ""))
        if match.group(2):
            number /= 100
        if number not in verified_numbers:
            return False
    return True


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
    assessment_year = profile_payload.assessment_year if profile_payload else "2026-27"
    retrieval_filter = RetrievalFilter(assessment_year=assessment_year, user_id=current_user.id)
    try:
        retrieved_context = list(SemanticKnowledgeBase(db=db).retrieve(
            message,
            retrieval_filter,
            limit=5,
        ))
    except (SemanticRAGUnavailable, Exception):
        # Semantic retrieval is an enhancement, not a reason to break the
        # deterministic tax assistant. Fall back to the local hybrid retriever.
        try:
            retrieved_context = list(LocalTaxKnowledgeBase(db=db).retrieve(
                message,
                retrieval_filter,
                limit=5,
            ))
        except Exception:
            retrieved_context = []
    requires_calculation = _requires_calculation(message)
    if _asks_about_uploaded_documents(message) and not requires_calculation:
        knowledge_context = [
            item for item in retrieved_context
            if item.metadata.get("source_type") == "user_document"
        ]
    else:
        knowledge_context = [
            item for item in retrieved_context
            if item.metadata.get("source_type") != "user_document"
        ]
    if not requires_calculation and not knowledge_context:
        return ChatMessageResponse(answer=_out_of_scope_answer(), sources=[], mode="tax-assistant")

    try:
        comparison = compare_regimes(profile_payload) if profile_payload else None
    except TaxEngineError:
        comparison = None
    answer = _deterministic_answer(message, profile_payload, comparison, [item.text for item in knowledge_context])
    if answer == _out_of_scope_answer():
        return ChatMessageResponse(answer=answer, sources=[], mode="tax-assistant")
    response_mode = "deterministic"

    structured_context = {
        "assessmentYear": profile_payload.assessment_year if profile_payload else None,
        "taxpayer": _profile_summary(profile_payload) if profile_payload else {},
        "taxCalculation": _calculation_summary(comparison),
        "itrEligibility": select_itr(profile_payload).__dict__ if profile_payload else None,
        "relevantTaxKnowledge": [
            {"source": item.source_name, "assessmentYear": item.assessment_year, "text": item.text}
            for item in knowledge_context
        ],
        "userQuestion": message,
    }

    has_private_document_context = any(
        item.metadata.get("source_type") == "user_document"
        for item in knowledge_context
    )
    if GITHUB_MODELS_TOKENS and not has_private_document_context:
        try:
            from openai import OpenAI

            prompt = (
                "You are TaxWise. Answer the user's question naturally using only the verified structured facts and relevant tax knowledge below. "
                "Generate a concise explanation. Do not calculate, infer, or add facts, rules, or monetary amounts. "
                "Every monetary amount and tax stage must match the verified tax calculation. "
                "Do not mention software, providers, models, prompts, sources, internal services, or implementation. "
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
                    if provider_answer and _is_safe_provider_answer(provider_answer, structured_context):
                        break
                except Exception as exc:
                    print(f"GitHub Models attempt failed: {type(exc).__name__}")
            if provider_answer and _is_safe_provider_answer(provider_answer, structured_context):
                answer = provider_answer.strip()
                response_mode = "assistant"
            # Keep the verified deterministic answer when the provider is unavailable,
            # malformed, or fails the safety checks.
        except Exception as exc:
            print(f"GitHub Models setup failed: {type(exc).__name__}")
            # Provider outages must not turn a useful tax answer into an error message.

    sources = list(dict.fromkeys(item.source_name for item in knowledge_context))
    return ChatMessageResponse(answer=answer, sources=sources, mode=response_mode)
