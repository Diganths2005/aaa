import os
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import GEMINI_API_KEY, GEMINI_MODEL
from database import get_db
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.chat import ChatMessageRequest, ChatMessageResponse
from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import compare_regimes
from services.rag import LocalKnowledgeRetriever, RetrievalFilter

router = APIRouter(prefix="/chat", tags=["chat"])
knowledge_retriever = LocalKnowledgeRetriever()

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
    taxes_paid = sum(float(item.amount) for item in profile.taxes_paid)
    return {
        "assessment_year": profile.assessment_year,
        "employment_type": profile.employment_type,
        "income": round(total_salary, 2),
        "deductions": round(total_deductions, 2),
        "tds_paid": round(taxes_paid, 2),
        "residential_status": profile.residential_status,
        "employer": profile.employer_name,
    }


def _fallback_answer(message: str, profile: TaxProfileCreate | None, comparison: Any | None) -> str:
    lower = message.lower()
    if "regime" in lower or "better" in lower or "compare" in lower:
        if not profile:
            return "I do not have enough confirmed information to compare regimes accurately yet. Please complete your Tax Profile and then I can compare old vs new regime using the deterministic Tax Engine."
        if not comparison:
            comparison = compare_regimes(profile)
        if comparison.recommended_regime == "equal":
            return f"Based on your confirmed information, the old and new regimes are effectively equal for AY {profile.assessment_year}. The difference is ₹{comparison.estimated_saving:,.0f}, so either option is mathematically close."
        recommended = "new" if comparison.recommended_regime == "new" else "old"
        estimated_saving = abs(float(comparison.estimated_saving))
        return (
            f"Based on your confirmed information, the {recommended} regime currently results in about ₹{estimated_saving:,.0f} less tax "
            f"than the alternative for AY {profile.assessment_year}. This recommendation is derived from the deterministic Tax Engine and not from AI guessing."
        )

    if "tds" in lower or "tax paid" in lower:
        if not profile:
            return "I need your profile to confirm the TDS you have already paid."
        total_tds = sum(float(item.amount) for item in profile.taxes_paid if item.tax_type == "tds")
        return f"Your Tax Profile currently records ₹{total_tds:,.0f} of TDS paid."

    if "deduction" in lower:
        if not profile:
            return "I need your deductions to assess eligibility. Please confirm the relevant deduction details in your Tax Profile."
        total_deductions = sum(float(item.amount) for item in profile.deductions)
        return f"Your confirmed deductions total ₹{total_deductions:,.0f}. I can help review which ones are supported and whether any additional eligible deductions need confirmation."

    if "what if" in lower or "what-if" in lower:
        return "I can help model a What-If scenario, but the calculation must come from the deterministic Tax Engine and not from a free-form AI estimate. Please provide the specific change such as more NPS, extra insurance, or a salary increase."

    return "I can help with Indian income tax, deductions, tax documents, filing readiness, and regime comparison. Please ask a tax-specific question and I will use your confirmed tax context and the deterministic Tax Engine to answer it."


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
    comparison = compare_regimes(profile_payload) if profile_payload else None
    retrieved = knowledge_retriever.retrieve(message, RetrievalFilter(user_id=current_user.id, assessment_year=profile_payload.assessment_year if profile_payload else "2026-27"))

    answer = _fallback_answer(message, profile_payload, comparison)
    response_mode = "fallback"

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=GEMINI_API_KEY)
            client = genai.GenerativeModel(GEMINI_MODEL)
            context = {
                "user_message": message,
                "assessment_year": profile_payload.assessment_year if profile_payload else "unknown",
                "tax_profile": _profile_summary(profile_payload) if profile_payload else {},
                "regime_comparison": {
                    "old_tax": float(comparison.old_regime.total_tax_liability) if comparison else None,
                    "new_tax": float(comparison.new_regime.total_tax_liability) if comparison else None,
                    "recommended": comparison.recommended_regime if comparison else None,
                },
                "retrieved_knowledge": [item.text for item in retrieved],
            }
            completion = client.generate_content(
                contents=(
                    "You are TaxWise, a strict Indian personal tax assistant. Explain tax matters using only the provided tax context. "
                    "Never invent tax numbers or a final tax result. If the user asks for tax calculations, summarize the deterministic engine output exactly. "
                    "Do not answer unrelated topics.\n\n"
                    f"Tax context: {context}\n\nUser question: {message}"
                ),
                generation_config={"max_output_tokens": 250},
            )
            provider_answer = getattr(completion, "text", None)
            if provider_answer:
                answer = provider_answer.strip()
                response_mode = "gemini"
        except Exception as exc:
            print(f"Gemini chatbot request failed: {type(exc).__name__}: {exc}")

    sources = []
    if profile_payload:
        sources.append(f"Tax Profile · AY {profile_payload.assessment_year}")
    if comparison:
        sources.append("Deterministic Tax Engine")
    sources.extend(sorted({f"RAG · {item.source_name}" for item in retrieved}))

    if response_mode == "gemini":
        sources.append("Gemini")
    return ChatMessageResponse(answer=answer, sources=sources, mode=response_mode)
