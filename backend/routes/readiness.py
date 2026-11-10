from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.document import UserDocument
from models.tax_profile import TaxProfile
from models.user import User
from routes.auth import get_current_user
from services.itr2_readiness import build_itr2_readiness

router = APIRouter(prefix="/readiness", tags=["itr-readiness"])


@router.get("/itr-2")
def itr2_readiness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Tax profile not found")

    documents = db.query(UserDocument).filter(
        UserDocument.user_id == current_user.id,
        UserDocument.status.in_(["PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED"]),
    ).all()

    candidates: list[dict] = []
    for document in documents:
        for candidate in (document.processing_result or {}).get("candidates", []):
            item = dict(candidate)
            item["document_id"] = document.id
            item["status"] = "confirmed" if document.status == "CONFIRMED" else "candidate"
            candidates.append(item)

    from schemas.tax_profile import TaxProfileCreate
    profile_data = TaxProfileCreate.model_validate(profile).model_dump(mode="json")
    return build_itr2_readiness(profile_data, extraction_candidates=candidates)
