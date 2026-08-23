import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from schemas.tax_profile import TaxProfileCreate


@dataclass(frozen=True)
class Question:
    field: str
    text: str
    required: bool = True


QUESTIONS = (
    Question("name", "First, what's your full name?"),
    Question("pan_number", "What's your PAN?"),
    Question("date_of_birth", "What's your date of birth? Use YYYY-MM-DD."),
    Question("residential_status", "Are you a resident, non-resident, or NRI?"),
    Question("employment_type", "What's your employment status?"),
    Question("employer_name", "Who is your employer?", False),
    Question("salary_income", "What's your annual salary for FY 2025-26?"),
    Question("salary_tds", "How much TDS was deducted from your salary?", False),
    Question("other_income", "Do you have any income apart from your salary?"),
    Question("house_property", "Do you own or receive income from any house property?"),
    Question("capital_gains", "Do you have any capital gains from investments or property?"),
    Question("business_income", "Do you have business or professional income?"),
    Question("deductions", "Do you have any deductions or investments to claim?"),
    Question("taxes_paid", "Do you have any advance tax or self-assessment tax paid?"),
    Question("bank_accounts", "What's the bank account to use for an income-tax refund?"),
    Question("documents", "Do you want to upload any tax documents? You can skip this."),
    Question("review", "Your Tax Profile is complete. Would you like to review it?"),
)


def initial_state(profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = profile or {}
    completed: List[str] = []
    answers: Dict[str, Any] = {}
    if profile.get("pan_number"):
        completed.append("pan_number")
    if profile.get("date_of_birth"):
        completed.append("date_of_birth")
    for field in ("residential_status", "employment_type", "employer_name"):
        if profile.get(field):
            completed.append(field)
    if profile.get("salary_income"):
        completed.extend(["salary_income", "salary_tds"])
    for field in ("other_income", "house_property", "capital_gains", "business_income", "deductions", "taxes_paid", "bank_accounts", "documents"):
        if profile.get(field):
            completed.append(field)
    return {"current_field": None, "completed_fields": completed, "skipped_fields": [], "missing_fields": [], "pending_candidate": None, "answers": answers}


def amount(value: str) -> Decimal:
    cleaned = value.replace("₹", "").replace(",", "").strip().lower()
    multiplier = Decimal("1")
    if cleaned.endswith(("lakh", "lakhs", "lac", "l")):
        cleaned = re.sub(r"(?:lakhs?|lac|l)$", "", cleaned).strip()
        multiplier = Decimal("100000")
    elif cleaned.endswith("k"):
        cleaned = cleaned[:-1].strip()
        multiplier = Decimal("1000")
    try:
        parsed = Decimal(cleaned) * multiplier
    except InvalidOperation as exc:
        raise ValueError("Amount must be a valid non-negative number") from exc
    if parsed < 0:
        raise ValueError("Amount must be non-negative")
    return parsed


def amount_as_number(value: str) -> Decimal:
    return amount(value)


def is_negative_answer(text: str) -> bool:
    return bool(re.search(r"\b(no|none|nil|not applicable|don't|do not)\b", text.lower()))


def next_question(state: Dict[str, Any]) -> Optional[Question]:
    completed = set(state.get("completed_fields", [])) | set(state.get("skipped_fields", []))
    for question in QUESTIONS:
        if question.field in completed:
            continue
        if question.field == "employer_name" and "salaried" not in str(state.get("answers", {}).get("employment_type", "")):
            continue
        if question.field == "salary_tds" and "salary_income" not in completed:
            continue
        return question
    return None


def progress(state: Dict[str, Any]) -> Dict[str, Any]:
    total = len(QUESTIONS) - 1
    completed = len(set(state.get("completed_fields", [])) | set(state.get("skipped_fields", [])))
    return {"completed": completed, "total": total, "percent": round(completed / total * 100) if total else 100}


def start_state(state: Dict[str, Any]) -> Dict[str, Any]:
    question = next_question(state)
    state["current_field"] = question.field if question else "review"
    state["missing_fields"] = [q.field for q in QUESTIONS if q.field not in set(state.get("completed_fields", [])) | set(state.get("skipped_fields", []))]
    return state


def parse_answer(state: Dict[str, Any], text: str) -> Dict[str, Any]:
    question = next_question(state)
    if not question:
        return {"candidate_values": {}, "requires_confirmation": False, "message": "Your Tax Profile is complete. You can review it before calculating tax."}
    correction = re.search(r"(?:actually|correct|change).*?(?:salary|income)[^\d]*(?:₹\s*)?([\d,.]+(?:\.\d+)?)\s*(lakhs?|lac|l|k)?", text.lower())
    if correction and state.get("answers", {}).get("salary_income"):
        value = amount_as_number(f"{correction.group(1)}{correction.group(2) or ''}")
        employer = state.get("answers", {}).get("employer_name", "")
        return {"candidate_values": {"salary_income": [{"employer_name": employer, "gross_salary": value, "standard_deduction": 0, "professional_tax": 0, "tds": 0}]}, "requires_confirmation": True, "message": "I found a salary correction. Would you like to update your salary?"}
    field = question.field
    lower = text.lower().strip()
    if field == "salary_income":
        match = re.search(r"(?:around\s+)?(?:₹\s*)?([\d,.]+(?:\.\d+)?)\s*(lakhs?|lac|l|k)?", lower)
        if not match:
            raise ValueError("Please enter a valid salary amount, such as 6 lakh or ₹6,00,000.")
        value = amount_as_number(f"{match.group(1)}{match.group(2) or ''}")
        employer = state.get("answers", {}).get("employer_name", "")
        return {"candidate_values": {"salary_income": [{"employer_name": employer, "gross_salary": value, "standard_deduction": 0, "professional_tax": 0, "tds": 0}]}, "requires_confirmation": True, "message": f"I understood ₹{value:,.0f} as your annual salary. Confirm?"}
    if field == "salary_tds":
        return {"candidate_values": {"salary_tds": amount_as_number(re.search(r"(?:₹\s*)?([\d,.]+(?:\.\d+)?)", lower).group(1)) if re.search(r"(?:₹\s*)?([\d,.]+(?:\.\d+)?)", lower) else None}, "requires_confirmation": True, "message": "I found this TDS amount. Confirm?"}
    if field in {"other_income", "house_property", "capital_gains", "business_income", "deductions", "taxes_paid", "documents"}:
        if is_negative_answer(text):
            return {"candidate_values": {}, "skip_field": field, "requires_confirmation": False, "message": f"Got it. I'll skip {field.replace('_', ' ')}."}
        if re.search(r"\b(yes|yeah|yep|have|some)\b", lower):
            return {"candidate_values": {}, "complete_field": field, "requires_confirmation": False, "message": f"Okay. I'll ask the relevant {field.replace('_', ' ')} questions next."}
        raise ValueError("Please answer yes or no so I can choose the relevant questions.")
    if field == "name":
        if len(text.strip()) < 2:
            raise ValueError("Please enter your full name.")
        return {"candidate_values": {"name": text.strip()}, "requires_confirmation": True, "message": f"I have your name as {text.strip()}. Confirm?"}
    if field == "pan_number":
        candidate = text.upper().strip()
        try:
            TaxProfileCreate(pan_number=candidate)
        except ValidationError as exc:
            raise ValueError("PAN must contain 10 characters in the format ABCDE1234F.") from exc
        return {"candidate_values": {"pan_number": candidate}, "requires_confirmation": True, "message": f"I have your PAN as {candidate[:2]}******{candidate[-2:]}. Confirm?"}
    if field == "date_of_birth":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text.strip()):
            raise ValueError("Use a valid date in YYYY-MM-DD format.")
        return {"candidate_values": {field: text.strip()}, "requires_confirmation": True, "message": f"I have your date of birth as {text.strip()}. Confirm?"}
    if field == "residential_status":
        value = next((item for item in ("resident", "non_resident", "nri") if item in lower.replace("-", "_")), None)
        if not value:
            raise ValueError("Please answer resident, non-resident, or NRI.")
        return {"candidate_values": {field: value}, "requires_confirmation": True, "message": f"I have marked you as {value.replace('_', ' ')}. Confirm?"}
    if field == "employment_type":
        value = "self_employed" if "self" in lower or "business" in lower else "none" if "not working" in lower or lower == "none" else "salaried"
        return {"candidate_values": {field: value}, "requires_confirmation": True, "message": f"I have marked your employment as {value.replace('_', ' ')}. Confirm?"}
    if field == "employer_name":
        return {"candidate_values": {field: text.strip()}, "requires_confirmation": True, "message": f"I have your employer as {text.strip()}. Confirm?"}
    if field == "bank_accounts":
        return {"candidate_values": {field: [{"bank_name": text.strip(), "account_number": "", "ifsc_code": "", "account_type": "savings", "is_primary": True}]}, "requires_confirmation": True, "message": f"I'll add {text.strip()} as your bank. Confirm?"}
    return {"candidate_values": {}, "requires_confirmation": False, "message": question.text}


def apply_candidate(state: Dict[str, Any], candidate: Dict[str, Any], action: str) -> Dict[str, Any]:
    if action == "reject":
        state["pending_candidate"] = None
        return start_state(state)
    if action != "confirm":
        raise ValueError("Confirmation action must be confirm or reject")
    values = candidate or {}
    for field, value in values.items():
        target = "salary_income" if field in {"salary_income", "salary_tds"} else field
        if field == "salary_tds":
            salary = state.get("answers", {}).get("salary_income", [{}])[0]
            salary["tds"] = value
            values = {"salary_income": [salary]}
        state.setdefault("answers", {}).update(values)
        if target not in state["completed_fields"]:
            state["completed_fields"].append(target)
    if candidate.get("_skip_field"):
        state["skipped_fields"].append(candidate["_skip_field"])
    if candidate.get("_complete_field") and candidate["_complete_field"] not in state["completed_fields"]:
        state["completed_fields"].append(candidate["_complete_field"])
    state["pending_candidate"] = None
    return start_state(state)