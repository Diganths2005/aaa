from dataclasses import dataclass
from pathlib import Path
import re
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


class LocalKnowledgeRetriever:
    """Small lexical retriever for versioned, checked-in assessment-year notes."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent / "knowledge"

    def retrieve(self, query: str, filters: RetrievalFilter, limit: int = 5) -> Sequence[RetrievedContext]:
        if not filters.assessment_year:
            return []
        path = self.root / f"ay_{filters.assessment_year.replace('-', '_')}.md"
        if not path.is_file():
            return []
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        sections = [section.strip() for section in path.read_text(encoding="utf-8").split("\n\n") if section.strip() and not section.startswith("#")]
        ranked = sorted(sections, key=lambda section: len(terms.intersection(set(re.findall(r"[a-z0-9]+", section.lower())))), reverse=True)
        return [RetrievedContext(text=section, source_type="official-notes", source_name=path.name, page_number=None, assessment_year=filters.assessment_year, metadata={}) for section in ranked[:limit] if terms.intersection(set(re.findall(r"[a-z0-9]+", section.lower())))]