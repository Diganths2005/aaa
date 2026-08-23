from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class RetrievalFilter:
    user_id: str
    assessment_year: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    source_type: str
    source_name: str
    page_number: int | None
    assessment_year: str | None
    metadata: Mapping[str, Any]


class KnowledgeRetriever(Protocol):
    """Retrieval boundary for official AY knowledge plus isolated user documents."""

    def retrieve(self, query: str, filters: RetrievalFilter, limit: int = 5) -> Sequence[RetrievedContext]:
        ...


class CopilotAnswerer(Protocol):
    """Future explanation boundary; tax amounts must come from the deterministic engine."""

    def answer(self, question: str, context: Sequence[RetrievedContext], tax_result: Mapping[str, Any] | None = None) -> str:
        ...