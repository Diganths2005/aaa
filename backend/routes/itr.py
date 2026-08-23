from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from itr.pdf import generate_itr1_pdf
from itr.service import check_itr1_eligibility, explain_itr_question, prepare_itr1
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.itr import ITRPrepareRequest, ITRQuestionRequest
from schemas.tax_profile import TaxProfileCreate

router = APIRouter(prefix="/api/itr", tags=["itr-preparation"])


def current_profile(current_user: User, db: Session) -> tuple[TaxProfile, TaxProfileCreate]:
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Tax profile not found")
    return profile, TaxProfileCreate.model_validate(profile)


@router.post("/eligibility")
def itr1_eligibility(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, profile = current_profile(current_user, db)
    return check_itr1_eligibility(profile).__dict__


@router.post("/prepare")
def prepare_itr(current_request: ITRPrepareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, profile = current_profile(current_user, db)
    eligibility = check_itr1_eligibility(profile)
    if not eligibility.eligible:
        raise HTTPException(status_code=422, detail={"message": "ITR-1 is not eligible", "reasons": eligibility.reasons})
    return prepare_itr1(profile, f"{current_user.first_name} {current_user.last_name}", current_request.regime)


@router.get("/current")
def current_itr(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, profile = current_profile(current_user, db)
    return prepare_itr1(profile, f"{current_user.first_name} {current_user.last_name}")


@router.post("/recalculate")
def recalculate_itr(current_request: ITRPrepareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return prepare_itr(current_request, current_user, db)


@router.post("/ask")
def ask_itr(current_request: ITRQuestionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, profile = current_profile(current_user, db)
    preparation = prepare_itr1(profile, f"{current_user.first_name} {current_user.last_name}")
    return {"assistant_message": explain_itr_question(current_request.question, preparation)}


@router.post("/pdf")
def itr_pdf(current_request: ITRPrepareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, profile = current_profile(current_user, db)
    preparation = prepare_itr1(profile, f"{current_user.first_name} {current_user.last_name}", current_request.regime)
    return Response(content=generate_itr1_pdf(preparation), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=taxwise-itr1-preparation-ay-2026-27.pdf"})