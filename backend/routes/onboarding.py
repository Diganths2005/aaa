from copy import deepcopy
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.onboarding import OnboardingSession
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.onboarding import DocumentCandidateRequest, OnboardingConfirmRequest, OnboardingMessageRequest, OnboardingSessionResponse
from schemas.tax_profile import TaxProfileCreate, TaxProfileResponse
from services.onboarding import apply_candidate, initial_state, next_question, parse_answer, progress, start_state
from utils.common import generate_id

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def profile_dict(profile: Optional[TaxProfile]) -> Optional[Dict[str, Any]]:
    return TaxProfileResponse.model_validate(profile).model_dump(mode="json") if profile else None


def raw_profile_dict(profile: Optional[TaxProfile]) -> Dict[str, Any]:
    return TaxProfileCreate.model_validate(profile).model_dump(mode="json") if profile else {}


def find_session(current_user: User, db: Session) -> OnboardingSession:
    session = db.query(OnboardingSession).filter(OnboardingSession.user_id == current_user.id).first()
    if session:
        return session
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    session = OnboardingSession(
        id=generate_id(), user_id=current_user.id, profile_id=profile.id if profile else None,
        state=initial_state(profile_dict(profile)), messages=[]
    )
    session.state = start_state(session.state)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def response(session: OnboardingSession, message: str, candidate: Optional[Dict[str, Any]] = None, requires_confirmation: bool = False, profile: Optional[TaxProfile] = None) -> OnboardingSessionResponse:
    state = start_state(session.state)
    question = next_question(state)
    return OnboardingSessionResponse(
        session_id=session.id,
        assistant_message=message,
        current_field=state.get("current_field"),
        candidate_values=candidate or {},
        requires_confirmation=requires_confirmation,
        progress=progress(state),
        next_field=question.field if question else None,
        completed_fields=state.get("completed_fields", []),
        skipped_fields=state.get("skipped_fields", []),
        profile=profile_dict(profile),
    )


@router.post("/session", response_model=OnboardingSessionResponse)
def create_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = find_session(current_user, db)
    question = next_question(session.state)
    return response(session, question.text if question else "Your Tax Profile is complete. You can review it before calculating tax.", profile=db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None)


@router.get("/session", response_model=OnboardingSessionResponse)
def get_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_session(current_user, db)


@router.get("/progress")
def get_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = find_session(current_user, db)
    return {"progress": progress(session.state), "current_field": session.state.get("current_field"), "missing_fields": session.state.get("missing_fields", [])}


@router.post("/message", response_model=OnboardingSessionResponse)
def message(request: OnboardingMessageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = find_session(current_user, db)
    state = deepcopy(session.state)
    text = request.message.strip()
    if text.lower() in {"what's next", "whats next", "next", "continue"}:
        question = next_question(state)
        session.state = start_state(state)
        db.commit()
        return response(session, question.text if question else "Your Tax Profile is complete. You can review it before calculating tax.", profile=db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None)
    try:
        result = parse_answer(state, text)
    except ValueError as exc:
        return response(session, str(exc), profile=db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None)
    candidate = jsonable_encoder(deepcopy(result.get("candidate_values", {})))
    if result.get("skip_field"):
        state.setdefault("skipped_fields", []).append(result["skip_field"])
    if result.get("complete_field") and result["complete_field"] not in state["completed_fields"]:
        state["completed_fields"].append(result["complete_field"])
    if result.get("requires_confirmation"):
        state["pending_candidate"] = candidate
    state.setdefault("answers", {})
    session.messages = (session.messages or []) + [{"source": "USER", "text": text}]
    session.state = start_state(state)
    db.commit()
    return response(session, result["message"], candidate, result.get("requires_confirmation", False), db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None)


def persist_candidate(session: OnboardingSession, candidate: Dict[str, Any], current_user: User, db: Session) -> TaxProfile:
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    existing = raw_profile_dict(profile)
    profile_candidate = deepcopy(candidate)
    candidate_name = profile_candidate.pop("name", None)
    if candidate_name:
        name_parts = candidate_name.split(maxsplit=1)
        current_user.first_name = name_parts[0]
        current_user.last_name = name_parts[1] if len(name_parts) > 1 else ""
    merged = {**existing, **profile_candidate}
    if "salary_tds" in merged:
        salary_income = list(merged.get("salary_income") or [])
        salary_tds = merged.pop("salary_tds")
        if salary_income:
            salary = deepcopy(salary_income[0])
            salary["tds"] = salary_tds
            merged["salary_income"] = [salary, *salary_income[1:]]
        else:
            taxes_paid = merged.setdefault("taxes_paid", [])
            if not any(item.get("tax_type") == "tds" and item.get("amount") == salary_tds for item in taxes_paid):
                taxes_paid.append({"tax_type": "tds", "amount": salary_tds})
    merged.pop("id", None)
    merged.pop("user_id", None)
    try:
        validated = TaxProfileCreate.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if profile:
        for field, value in validated.model_dump(mode="json").items():
            setattr(profile, field, value)
    else:
        profile = TaxProfile(id=generate_id(), user_id=current_user.id, **validated.model_dump(mode="json"))
        db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = "A tax profile with this PAN already exists. Please use a different PAN or update the existing profile."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    db.refresh(profile)
    session.profile_id = profile.id
    return profile


@router.post("/confirm", response_model=OnboardingSessionResponse)
def confirm(request: OnboardingConfirmRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = find_session(current_user, db)
    state = deepcopy(session.state)
    candidate = state.get("pending_candidate")
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="There is no pending candidate to confirm")
    if request.action == "confirm":
        profile = persist_candidate(session, candidate, current_user, db)
        session.state = apply_candidate(state, candidate, "confirm")
        message_text = "Confirmed. I updated your Tax Profile."
    else:
        profile = db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None
        session.state = apply_candidate(state, candidate, "reject")
        message_text = "No changes made. Let's continue with the next question."
    db.commit()
    question = next_question(session.state)
    return response(session, message_text + (f" {question.text}" if question else " Your Tax Profile is complete."), profile=profile)


@router.post("/document-candidate", response_model=OnboardingSessionResponse)
def document_candidate(request: DocumentCandidateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = find_session(current_user, db)
    state = deepcopy(session.state)
    state["pending_candidate"] = request.candidate_values
    session.state = state
    db.commit()
    return response(session, "I found information in your document. Would you like me to add it to your profile?", request.candidate_values, True, db.query(TaxProfile).filter(TaxProfile.id == session.profile_id).first() if session.profile_id else None)