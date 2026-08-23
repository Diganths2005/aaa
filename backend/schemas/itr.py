from typing import Literal

from pydantic import BaseModel, Field


class ITRPrepareRequest(BaseModel):
    regime: Literal["old", "new"] = "new"


class ITRQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)