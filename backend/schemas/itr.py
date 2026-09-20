from typing import Literal, Optional

from pydantic import BaseModel, Field


class ITRPrepareRequest(BaseModel):
    regime: Literal["old", "new"] = "new"
    itr_form: Optional[Literal["ITR-1", "ITR-2", "ITR-3", "ITR-4"]] = None


class ITRQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)