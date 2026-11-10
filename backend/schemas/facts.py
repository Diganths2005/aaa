from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class FactResolutionRequest(BaseModel):
    action: Literal["confirm", "reject", "keep", "accept", "correct"]
    value: Any | None = None


class DocumentFactResolutionRequest(BaseModel):
    action: Literal["confirm", "reject"]


class FactEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str
    document_id: str | None = None
    page_number: int | None = None
    section: str | None = None
    source_text: str | None = None
    confidence: str


class TaxpayerFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_year: str
    fact_key: str
    value: Any
    normalized_value: Any
    source_type: str
    document_id: str | None = None
    page_number: int | None = None
    section: str | None = None
    source_text: str | None = None
    confidence: str
    status: str
    mapping_status: str
    group_id: str | None = None
    evidence: list[FactEvidenceResponse] = []
