from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from models.tax_profile import TaxProfile
from schemas.tax_profile import TaxProfileCreate
from utils.common import generate_id


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str, profile_id: str | None = None) -> TaxProfile | None:
        query = self.db.query(TaxProfile).filter(TaxProfile.user_id == user_id)
        if profile_id:
            query = query.filter(TaxProfile.id == profile_id)
        return query.first()

    def save(self, user_id: str, data: TaxProfileCreate, profile_id: str | None = None) -> TaxProfile:
        profile = self.get(user_id, profile_id)
        payload = data.model_dump(mode="json")
        if profile is None:
            profile = TaxProfile(id=generate_id(), user_id=user_id, **payload)
            self.db.add(profile)
        else:
            for field, value in payload.items():
                setattr(profile, field, deepcopy(value))
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def merge(self, user_id: str, candidate: dict[str, Any]) -> TaxProfile:
        profile = self.get(user_id)
        existing = TaxProfileCreate.model_validate(profile).model_dump(mode="json") if profile else {}
        merged = {**existing, **deepcopy(candidate)}
        merged.pop("id", None)
        merged.pop("user_id", None)
        return self.save(user_id, TaxProfileCreate.model_validate(merged))
