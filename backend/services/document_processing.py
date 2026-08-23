from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class ExtractedChunk:
    text: str
    page_number: int
    chunk_index: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class DocumentProcessingResult:
    chunks: Sequence[ExtractedChunk]
    extracted_fields: Mapping[str, Any]
    requires_confirmation: bool = True


class DocumentProcessor(Protocol):
    """Pipeline boundary: PDF extraction, OCR, cleaning, chunking and classification."""

    def process(self, document_id: str, content: bytes) -> DocumentProcessingResult:
        ...


class EmbeddingStore(Protocol):
    """Storage boundary for embeddings; implementations must scope records by user ID."""

    def index(self, user_id: str, document_id: str, chunks: Sequence[ExtractedChunk]) -> None:
        ...
