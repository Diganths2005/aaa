from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.tax_profile import TaxProfileCreate
from schemas.what_if import WhatIfApplyRequest, WhatIfResult, WhatIfScenarioRequest
from services.what_if import apply_changes, simulate

router = APIRouter(prefix="/what-if", tags=["what-if"])


def _profile(current_user: User, db: Session, profile_id: str | None) -> TaxProfile:
    query = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id)
    if profile_id:
        query = query.filter(TaxProfile.id == profile_id)
    profile = query.first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax profile not found")
    return profile


@router.post("/simulate", response_model=WhatIfResult)
def simulate_what_if(request: WhatIfScenarioRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _profile(current_user, db, request.base_profile_id)
    try:
        result = simulate(TaxProfileCreate.model_validate(profile), request)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return WhatIfResult(scenario=request, **jsonable_encoder(result))


@router.post("/apply", response_model=WhatIfResult)
def apply_what_if(request: WhatIfApplyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _profile(current_user, db, request.base_profile_id)
    if not request.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Explicit confirmation is required to apply a What-If scenario")
    try:
        base = TaxProfileCreate.model_validate(profile)
        simulated = simulate(base, request)
        updated = apply_changes(base, request.changes)
        for field, value in updated.model_dump(mode="json").items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
    except (ValueError, KeyError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return WhatIfResult(scenario=request, profile_changed=True, **jsonable_encoder(simulated))
