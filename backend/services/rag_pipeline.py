from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from services.knowledge import LocalTaxKnowledgeBase, RetrievalFilter, RetrievedContext
from services.semantic_rag import SemanticKnowledgeBase


@dataclass(frozen=True)
class RAGResult:
    contexts: list[RetrievedContext]
    retrieval_mode: str
    reranked: bool


def _rrf_fuse(rankings: Sequence[Sequence[RetrievedContext]], k: int = 60) -> list[RetrievedContext]:
    scores: dict[tuple[str, str, int | None], float] = {}
    items: dict[tuple[str, str, int | None], RetrievedContext] = {}
    for ranking in rankings:
        for rank, context in enumerate(ranking, start=1):
            key = (context.source_name, context.text, context.page_number)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items[key] = context
    return [
        items[key]
        for key, _ in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0][0], pair[0][1]))
    ]


def _rerank(query: str, contexts: Sequence[RetrievedContext], limit: int) -> list[RetrievedContext]:
    query_terms = set(LocalTaxKnowledgeBase._TOKEN_PATTERN.findall(query.lower())) - LocalTaxKnowledgeBase._STOP_WORDS
    if not query_terms:
        return list(contexts[:limit])

    def score(context: RetrievedContext) -> tuple[float, str]:
        terms = LocalTaxKnowledgeBase._TOKEN_PATTERN.findall(context.text.lower())
        overlap = len(query_terms.intersection(terms))
        topic_terms = LocalTaxKnowledgeBase._TOKEN_PATTERN.findall(
            f"{context.metadata.get('topic', '')} {context.source_name}".lower()
        )
        topic_overlap = len(query_terms.intersection(topic_terms))
        phrase_bonus = 0.35 if query.lower() in context.text.lower() else 0.0
        metadata_bonus = 0.15 if context.metadata.get("status") == "active" else 0.0
        semantic = float(context.metadata.get("similarity", 0.0) or 0.0)
        return overlap + 0.15 * topic_overlap + phrase_bonus + metadata_bonus + semantic, context.source_name

    return [
        item for item in sorted(contexts, key=score, reverse=True)[:limit]
    ]


def retrieve_hybrid(
    query: str,
    filters: RetrievalFilter,
    *,
    db,
    limit: int = 5,
) -> RAGResult:
    lexical: list[RetrievedContext] = []
    semantic: list[RetrievedContext] = []
    semantic_available = True

    try:
        semantic = list(SemanticKnowledgeBase(db=db).retrieve(query, filters, limit=max(limit * 3, 10)))
    except Exception:
        semantic_available = False

    try:
        lexical = list(LocalTaxKnowledgeBase(db=db).retrieve(query, filters, limit=max(limit * 3, 10)))
    except Exception:
        lexical = []

    if semantic and lexical:
        fused = _rrf_fuse([semantic, lexical])
        mode = "hybrid"
    elif semantic:
        fused = semantic
        mode = "vector"
    else:
        fused = lexical
        mode = "bm25"

    reranked = _rerank(query, fused, limit)
    return RAGResult(
        contexts=reranked,
        retrieval_mode=mode,
        reranked=True,
    )
