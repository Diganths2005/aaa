from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class OnboardingMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class OnboardingConfirmRequest(BaseModel):
    action: Literal["confirm", "reject"]


class DocumentCandidateRequest(BaseModel):
    candidate_values: Dict[str, Any]
    source: Literal["DOCUMENT"] = "DOCUMENT"


class OnboardingSessionResponse(BaseModel):
    session_id: str
    assistant_message: str
    current_field: Optional[str]
    candidate_values: Dict[str, Any] = {}
    requires_confirmation: bool = False
    progress: Dict[str, Any]
    next_field: Optional[str]
    completed_fields: list[str]
    skipped_fields: list[str]
    profile: Optional[Dict[str, Any]] = None