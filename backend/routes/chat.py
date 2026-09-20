from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.tax_profile import TaxProfile
from schemas.chat import ChatRequest, ChatResponse
from services.tax_engine import calculate_tax, compare_regimes

router = APIRouter(prefix="/chat", tags=["chat"])


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _profile_payload(profile: TaxProfile) -> dict[str, Any]:
    # Keep chat calculations grounded in the same saved profile used by ITR preparation.
    return {
        "assessment_year": profile.assessment_year,
        "residential_status": profile.residential_status,
        "salary_income": profile.salary_income or [],
        "pension_income": profile.pension_income or [],
        "house_property_income": profile.house_property_income or [],
        "other_income": profile.other_income or [],
        "capital_gains": profile.capital_gains or [],
        "business_income": profile.business_income or [],
        "deductions": profile.deductions or [],
        "tax_payments": profile.tax_payments or [],
    }


def _income_summary(p: dict[str, Any]) -> dict[str, float]:
    salary = sum(_num(x.get("gross_salary")) for x in p.get("salary_income", []))
    pension = sum(_num(x.get("amount")) for x in p.get("pension_income", []))
    house = sum(_num(x.get("income")) for x in p.get("house_property_income", []))
    other = sum(_num(x.get("amount")) for x in p.get("other_income", []))
    capital = sum(_num(x.get("gain")) for x in p.get("capital_gains", []))
    business = sum(_num(x.get("net_profit")) for x in p.get("business_income", []))
    return {"salary": salary, "pension": pension, "house": house, "other": other, "capital": capital, "business": business}


def _tax_payments(p: dict[str, Any]) -> float:
    return sum(_num(x.get("amount")) for x in p.get("tax_payments", []))


def _money(v: float) -> str:
    return f"₹{v:,.0f}"


def _fallback_answer(message: str, profile_payload: dict[str, Any]) -> str:
    text = message.lower().strip()
    summary = _income_summary(profile_payload)
    total_income = sum(summary.values())
    tax_paid = _tax_payments(profile_payload)

    # Natural-language tax questions must be answered from the deterministic engine.
    tax_question = any(k in text for k in [
        "how much tax", "tax do i need", "tax do i have", "explain my tax",
        "explain tax", "tax payable", "tax liability", "owe", "refund", "payable"
    ])
    if tax_question:
        try:
            comparison = compare_regimes(profile_payload)
            old_tax = _num(comparison.get("old_regime", {}).get("total_tax"))
            new_tax = _num(comparison.get("new_regime", {}).get("total_tax"))
            recommended = comparison.get("recommended_regime") or comparison.get("recommended") or "not determined"
            selected = comparison.get("selected_regime") or recommended
            selected_tax = new_tax if str(selected).lower().startswith("new") else old_tax
            balance = selected_tax - tax_paid
            result = "refund due" if balance < 0 else "remaining tax payable"
            lines = [
                "Here is your tax calculation for AY 2026-27:",
                f"• Total income reported: {_money(total_income)}",
                f"• TDS/other tax already paid: {_money(tax_paid)}",
                f"• Old-regime tax: {_money(old_tax)}",
                f"• New-regime tax: {_money(new_tax)}",
                f"• Recommended regime: {recommended}",
            ]
            if selected_tax:
                lines.append(f"• On the {selected} regime: {_money(abs(balance))} {result}.")
            lines.append("These figures are calculated by the deterministic Tax Engine using your saved Tax Profile.")
            return "\n".join(lines)
        except Exception:
            return "I couldn't complete the tax calculation from your saved Tax Profile. Please make sure your income and tax-payment entries are saved, then try again."

    if any(k in text for k in ["which regime", "old regime", "new regime", "regime better", "regime"]):
        try:
            comparison = compare_regimes(profile_payload)
            old_tax = _num(comparison.get("old_regime", {}).get("total_tax"))
            new_tax = _num(comparison.get("new_regime", {}).get("total_tax"))
            recommended = comparison.get("recommended_regime") or comparison.get("recommended") or "not determined"
            return (f"For your saved profile, the old regime tax is {_money(old_tax)} and the new regime tax is "
                    f"{_money(new_tax)}. The deterministic Tax Engine recommends the {recommended} regime.")
        except Exception:
            return "I couldn't compare the regimes because your saved tax profile is incomplete."

    if any(k in text for k in ["deduction", "80c", "80d", "what deductions"]):
        deductions = profile_payload.get("deductions", [])
        total = sum(_num(x.get("amount")) for x in deductions)
        if deductions:
            return f"Your saved profile contains {len(deductions)} deduction entries totaling {_money(total)}. I can also explain each deduction if you ask about a specific section."
        return "I don't see any saved deduction entries in your Tax Profile yet."

    if "tds" in text or "tax paid" in text:
        return f"Your saved tax payments currently total {_money(tax_paid)}. This includes the TDS and other tax-payment entries saved in your profile."

    if "itr" in text:
        return "I can explain which ITR fits your profile. Ask 'Which ITR should I file?' and I will use your saved income sources and the ITR selection rules."

    return ("I can answer questions about your saved Tax Profile. Try: "
            "'Explain my tax', 'How much tax do I need to pay?', 'Will I get a refund?', "
            "'Which regime is better?', 'What deductions am I getting?', or 'Which ITR should I file?'")


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    profile = db.query(TaxProfile).filter(TaxProfile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Tax profile not found")
    profile_payload = _profile_payload(profile)
    answer = _fallback_answer(payload.message, profile_payload)
    return ChatResponse(answer=answer)
