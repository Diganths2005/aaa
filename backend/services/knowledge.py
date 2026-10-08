from dataclasses import dataclass
from collections import Counter
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.document import UserDocument, UserDocumentChunk


@dataclass(frozen=True)
class RetrievalFilter:
    assessment_year: str | None
    user_id: str | None = None


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    source_name: str
    assessment_year: str | None
    metadata: Mapping[str, Any]
    page_number: int | None = None


class LocalTaxKnowledgeBase:
    """Private local hybrid retrieval over curated notes and the current user's documents."""

    _TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
    _STOP_WORDS = {
        "a", "about", "am", "an", "and", "are", "as", "at", "be", "can", "do", "does", "for", "from",
        "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "should", "tell", "that",
        "the", "this", "to", "was", "we", "what", "when", "where", "which", "why", "with", "you", "your",
        "tax", "income", "new", "old", "regime", "work", "under",
    }

    def __init__(self, root: Path | None = None, db: Session | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent / "knowledge"
        self.db = db

    @staticmethod
    def _read_metadata(content: str) -> tuple[dict[str, Any], str]:
        match = re.match(r"\A<!--\s*(\{.*?\})\s*-->\s*", content, flags=re.DOTALL)
        if not match:
            return {}, content
        try:
            metadata = json.loads(match.group(1))
        except json.JSONDecodeError:
            return {}, content
        return metadata, content[match.end():]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {LocalTaxKnowledgeBase._normalize_term(term) for term in re.findall(r"[a-z0-9]+", text.lower())}

    @staticmethod
    def _normalize_term(term: str) -> str:
        if len(term) > 4 and term.endswith("ed"):
            return term[:-1]
        if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
            return term[:-1]
        return term

    def _knowledge_contexts(self, assessment_year: str) -> list[RetrievedContext]:
        contexts: list[RetrievedContext] = []
        if not self.root.is_dir():
            return contexts
        for path in sorted(self.root.rglob("*.md")):
            if path.name.lower() == "index.md":
                continue
            content = path.read_text(encoding="utf-8")
            metadata, markdown = self._read_metadata(content)
            if metadata.get("status") != "active" or metadata.get("assessment_year") != assessment_year:
                continue
            for section in re.split(r"\n(?=#{1,3} )", markdown):
                section = section.strip()
                if not section:
                    continue
                for chunk in chunk_text(section):
                    contexts.append(RetrievedContext(
                        text=chunk,
                        source_name=path.relative_to(self.root).as_posix(),
                        assessment_year=assessment_year,
                        metadata=metadata,
                    ))
        return contexts

    def _user_document_contexts(self, query_text: str, filters: RetrievalFilter) -> list[RetrievedContext]:
        if not self.db or not filters.user_id:
            return []
        search_terms = sorted(
            {
                self._normalize_term(term)
                for term in self._TOKEN_PATTERN.findall(query_text.lower())
                if term not in self._STOP_WORDS
            },
            key=lambda term: (-len(term), term),
        )[:12]
        if not search_terms:
            return []
        query = (
            self.db.query(UserDocumentChunk, UserDocument)
            .join(UserDocument, UserDocument.id == UserDocumentChunk.document_id)
            .filter(
                UserDocument.user_id == filters.user_id,
                UserDocument.status.in_(("PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED")),
                or_(*(UserDocumentChunk.text.ilike(f"%{term}%") for term in search_terms)),
            )
        )
        if filters.assessment_year:
            query = query.filter(
                (UserDocument.assessment_year == filters.assessment_year)
                | UserDocument.assessment_year.is_(None)
            )
        contexts: list[RetrievedContext] = []
        for chunk, document in query.order_by(
            UserDocument.updated_at.desc(),
            UserDocumentChunk.document_id,
            UserDocumentChunk.chunk_index,
        ).limit(1000).all():
            source = document.original_filename
            if chunk.page_number is not None:
                source = f"{source} (page {chunk.page_number})"
            contexts.append(RetrievedContext(
                text=chunk.text,
                source_name=source,
                assessment_year=document.assessment_year,
                metadata={
                    "source_type": "user_document",
                    "document_id": document.id,
                    "document_status": document.status,
                },
                page_number=chunk.page_number,
            ))
        return contexts

    @classmethod
    def _hybrid_scores(cls, query: str, contexts: Sequence[RetrievedContext]) -> list[float]:
        query_terms = Counter(
            cls._normalize_term(term) for term in cls._TOKEN_PATTERN.findall(query.lower())
            if term not in cls._STOP_WORDS
        )
        if not query_terms or not contexts:
            return [0.0] * len(contexts)

        documents = [
            [cls._normalize_term(term) for term in cls._TOKEN_PATTERN.findall(item.text.lower())]
            for item in contexts
        ]
        document_frequency = Counter(term for terms in documents for term in set(terms))
        count = len(documents)
        average_length = sum(len(terms) for terms in documents) / count or 1.0
        inverse_frequency = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }
        query_weights = {
            term: (1 + math.log(frequency)) * inverse_frequency.get(term, 0.0)
            for term, frequency in query_terms.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values())) or 1.0
        scores: list[float] = []
        for context, terms in zip(contexts, documents):
            frequencies = Counter(terms)
            bm25 = 0.0
            vector_dot = 0.0
            document_norm = 0.0
            length_factor = 1.2 * (1 - 0.75 + 0.75 * len(terms) / average_length)
            for term in query_terms:
                idf = inverse_frequency.get(term, 0.0)
                frequency = frequencies[term]
                bm25 += idf * (frequency * 2.2) / (frequency + length_factor) if frequency else 0.0
                tfidf = (1 + math.log(frequency)) * idf if frequency else 0.0
                vector_dot += tfidf * query_weights[term]
                document_norm += tfidf * tfidf
            cosine = vector_dot / (math.sqrt(document_norm) * query_norm) if document_norm else 0.0
            topic_terms = cls._terms(f"{context.metadata.get('topic', '')} {context.source_name}")
            topic_overlap = len(query_terms.keys() & set(topic_terms))
            scores.append(bm25 / (bm25 + 1.0) + 0.35 * cosine + 0.15 * topic_overlap)
        return scores

    def retrieve(self, query: str, filters: RetrievalFilter, limit: int = 5) -> Sequence[RetrievedContext]:
        if limit <= 0:
            return []
        query_terms = set(self._TOKEN_PATTERN.findall(query.lower())) - self._STOP_WORDS
        if not query_terms:
            return []
        contexts = self._knowledge_contexts(filters.assessment_year) if filters.assessment_year else []
        contexts.extend(self._user_document_contexts(query, filters))
        scores = self._hybrid_scores(query, contexts)
        ranked = sorted(
            ((score, context.source_name, index, context) for index, (score, context) in enumerate(zip(scores, contexts))),
            key=lambda item: (-item[0], item[1], item[2]),
        )
        return [context for score, _, _, context in ranked if score > 0][:limit]


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 160) -> list[str]:
    """Split extracted text into bounded, overlapping passages without breaking words."""
    if max_chars < 1 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Chunk overlap must be non-negative and smaller than max_chars")
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start, end), normalized.rfind(" ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
        while start < len(normalized) and normalized[start].isspace():
            start += 1
    return chunks