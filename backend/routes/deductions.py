from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.tax_profile import TaxProfileCreate
from services.deduction_discovery import discover_deductions, summarize_discovery

router = APIRouter(prefix="/deductions", tags=["deductions"])


@router.get("/discovery")
def deduction_discovery(
    regime: str = Query(default="old", regex="^(old|new)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Tax profile not found")
    payload = TaxProfileCreate.model_validate(profile)
    return discover_deductions(payload, regime=regime)


@router.get("/summary")
def deduction_summary(
    regime: str = Query(default="old", regex="^(old|new)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Tax profile not found")
    payload = TaxProfileCreate.model_validate(profile)
    return summarize_discovery(discover_deductions(payload, regime=regime))
