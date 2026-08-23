from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.tax_profile import TaxProfileCreate, TaxProfileUpdate, TaxProfileResponse
from models.tax_profile import TaxProfile
from models.user import User
from database import get_db
from utils.common import generate_id
from routes.auth import get_current_user

router = APIRouter(prefix="/tax-profiles", tags=["tax-profiles"])

@router.post("/", response_model=TaxProfileResponse)
def create_tax_profile(
    profile_data: TaxProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user already has a profile
    existing_profile = db.query(TaxProfile).filter(
        TaxProfile.user_id == current_user.id
    ).first()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a tax profile"
        )
    
    # Create new tax profile
    new_profile = TaxProfile(
        id=generate_id(),
        user_id=current_user.id,
        **profile_data.model_dump(mode="json")
    )
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    return new_profile

@router.get("/current", response_model=TaxProfileResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(TaxProfile).filter(
        TaxProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found"
        )
    
    return profile

@router.get("/{profile_id}", response_model=TaxProfileResponse)
def get_tax_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(TaxProfile).filter(
        TaxProfile.id == profile_id,
        TaxProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found"
        )
    
    return profile

@router.put("/{profile_id}", response_model=TaxProfileResponse)
def update_tax_profile(
    profile_id: str,
    profile_data: TaxProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(TaxProfile).filter(
        TaxProfile.id == profile_id,
        TaxProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found"
        )
    
    # Update fields
    for field, value in profile_data.model_dump(mode="json").items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

@router.post("/{profile_id}/documents")
def upload_document(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(TaxProfile).filter(
        TaxProfile.id == profile_id,
        TaxProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found"
        )

    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Document intake is available through the optional /documents endpoint",
    )

@router.delete("/{profile_id}")
def delete_tax_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(TaxProfile).filter(
        TaxProfile.id == profile_id,
        TaxProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found"
        )
    
    db.delete(profile)
    db.commit()
    
    return {"message": "Tax profile deleted successfully"}
