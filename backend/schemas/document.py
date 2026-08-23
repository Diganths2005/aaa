from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal[
    "form_16",
    "form_26as",
    "ais_tis",
    "bank_statement",
    "investment_statement",
    "insurance",
    "loan",
    "capital_gains",
    "other",
]

DocumentStatus = Literal["UPLOADED", "PROCESSING", "PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED", "FAILED", "DELETED", "pending"]


class DocumentCreate(BaseModel):
    document_type: DocumentType
    original_filename: str = Field(min_length=1, max_length=255)
    assessment_year: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class DocumentResponse(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: DocumentStatus
    page_count: Optional[int] = None
    processing_result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None