from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from schemas.tax_profile import TaxProfileCreate, TaxProfileUpdate, TaxProfileResponse
from services.profile_service import ProfileService

router = APIRouter(prefix="/tax-profiles", tags=["tax-profiles"])


@router.post("/", response_model=TaxProfileResponse)
def create_tax_profile(
    profile_data: TaxProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    if service.get(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a tax profile",
        )
    return service.save(current_user.id, profile_data)


@router.get("/current", response_model=TaxProfileResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = ProfileService(db).get(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found",
        )
    return profile


@router.get("/{profile_id}", response_model=TaxProfileResponse)
def get_tax_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = ProfileService(db).get(current_user.id, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found",
        )
    return profile


@router.put("/{profile_id}", response_model=TaxProfileResponse)
def update_tax_profile(
    profile_id: str,
    profile_data: TaxProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    profile = service.get(current_user.id, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found",
        )

    payload = profile_data.model_dump(exclude_unset=True, mode="json")
    current = TaxProfileCreate.model_validate(profile).model_dump(mode="json")
    current.update(payload)
    current.pop("id", None)
    current.pop("user_id", None)
    return service.save(current_user.id, TaxProfileCreate.model_validate(current))


@router.post("/{profile_id}/documents")
def upload_document(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not ProfileService(db).get(current_user.id, profile_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found",
        )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Document intake is available through the /documents endpoint",
    )


@router.delete("/{profile_id}")
def delete_tax_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = ProfileService(db).get(current_user.id, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax profile not found",
        )
    db.delete(profile)
    db.commit()
    return {"message": "Tax profile deleted successfully"}
