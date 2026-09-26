from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ScenarioOperation = Literal["replace", "add", "remove", "increase_by", "decrease_by"]


class ScenarioChange(BaseModel):
    field: str = Field(min_length=1, max_length=100)
    operation: ScenarioOperation
    value: Any
    index: int | None = Field(default=None, ge=0)


class WhatIfScenarioRequest(BaseModel):
    base_profile_id: str | None = None
    changes: list[ScenarioChange] = Field(min_length=1, max_length=20)
    regime: Literal["old", "new"] | None = None


class WhatIfApplyRequest(WhatIfScenarioRequest):
    confirm: bool = False


class WhatIfResult(BaseModel):
    scenario: WhatIfScenarioRequest
    baseline: dict[str, Any]
    what_if: dict[str, Any]
    comparison: dict[str, Any]
    explanation: dict[str, Any]
    profile_changed: bool = False
