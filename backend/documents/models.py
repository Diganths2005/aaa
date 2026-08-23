from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List


@dataclass(frozen=True)
class ExtractedCandidate:
    field: str
    value: Any
    source: str
    confidence: str
    page: int
    requires_confirmation: bool = True

    def as_dict(self) -> Dict[str, Any]:
        value = str(self.value) if isinstance(self.value, Decimal) else self.value
        return {"field": self.field, "value": value, "source": self.source, "confidence": self.confidence, "page": self.page, "requires_confirmation": self.requires_confirmation}


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int
    candidates: List[ExtractedCandidate]
    document_type: str