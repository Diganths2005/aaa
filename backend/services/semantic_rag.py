from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from models.document import UserDocument, UserDocumentChunk
from services.knowledge import RetrievalFilter, RetrievedContext, chunk_text


class SemanticRAGUnavailable(RuntimeError):
    pass


class SemanticKnowledgeBase:
    """Optional semantic retrieval backed by Chroma and OpenAI embeddings.

    The lexical retriever remains the deterministic fallback when embeddings
    are not configured. No user document is indexed without its user_id.
    """

    def __init__(self, root: Path | None = None, db: Any | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent / "knowledge"
        self.db = db
        self.store_path = self.root.parent.parent / ".taxwise-data" / "vector_store"

    def _clients(self):
        if not OPENAI_API_KEY:
            raise SemanticRAGUnavailable("OPENAI_API_KEY is not configured")
        try:
            import chromadb
            from openai import OpenAI
        except ImportError as exc:
            raise SemanticRAGUnavailable("Semantic RAG dependencies are not installed") from exc
        client = chromadb.PersistentClient(path=str(self.store_path))
        collection = client.get_or_create_collection(
            name="taxwise_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        return OpenAI(api_key=OPENAI_API_KEY, timeout=20.0, max_retries=0), collection

    @staticmethod
    def _embedding(client: Any, texts: list[str]) -> list[list[float]]:
        response = client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    @staticmethod
    def _knowledge_documents(root: Path, assessment_year: str) -> list[dict[str, Any]]:
        documents = []
        if not root.is_dir():
            return documents
        import json
        import re

        for path in sorted(root.rglob("*.md")):
            if path.name.lower() == "index.md":
                continue
            content = path.read_text(encoding="utf-8")
            match = re.match(r"\A<!--\s*(\{.*?\})\s*-->\s*", content, flags=re.DOTALL)
            metadata = json.loads(match.group(1)) if match else {}
            if metadata.get("status") != "active" or metadata.get("assessment_year") != assessment_year:
                continue
            markdown = content[match.end():] if match else content
            for index, passage in enumerate(chunk_text(markdown)):
                documents.append({
                    "id": "knowledge:" + hashlib.sha256(f"{path}:{index}".encode()).hexdigest(),
                    "text": passage,
                    "source": path.relative_to(root).as_posix(),
                    "assessment_year": assessment_year,
                    "source_type": "knowledge",
                    "metadata": metadata,
                })
        return documents

    def _user_documents(self, filters: RetrievalFilter) -> list[dict[str, Any]]:
        if not self.db or not filters.user_id:
            return []
        rows = (
            self.db.query(UserDocumentChunk, UserDocument)
            .join(UserDocument, UserDocument.id == UserDocumentChunk.document_id)
            .filter(
                UserDocument.user_id == filters.user_id,
                UserDocument.status.in_(("PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED")),
            )
        )
        if filters.assessment_year:
            rows = rows.filter(
                (UserDocument.assessment_year == filters.assessment_year)
                | UserDocument.assessment_year.is_(None)
            )
        result = []
        for chunk, document in rows.all():
            result.append({
                "id": f"user:{filters.user_id}:{chunk.id}",
                "text": chunk.text,
                "source": document.original_filename + (f" (page {chunk.page_number})" if chunk.page_number else ""),
                "assessment_year": document.assessment_year,
                "source_type": "user_document",
                "metadata": {
                    "source_type": "user_document",
                    "document_id": document.id,
                    "user_id": filters.user_id,
                    "document_status": document.status,
                },
            })
        return result

    def retrieve(self, query: str, filters: RetrievalFilter, limit: int = 5) -> list[RetrievedContext]:
        if limit <= 0:
            return []
        client, collection = self._clients()
        records = self._knowledge_documents(self.root, filters.assessment_year) + self._user_documents(filters)
        if records:
            embeddings = self._embedding(client, [item["text"] for item in records])
            collection.upsert(
                ids=[item["id"] for item in records],
                documents=[item["text"] for item in records],
                embeddings=embeddings,
                metadatas=[
                    {
                        "source": item["source"],
                        "assessment_year": item["assessment_year"] or "",
                        "source_type": item["source_type"],
                        "document_id": item["metadata"].get("document_id", ""),
                        "user_id": item["metadata"].get("user_id", ""),
                    }
                    for item in records
                ],
            )
        query_embedding = self._embedding(client, [query])[0]
        allowed_year = filters.assessment_year or ""
        where = {
            "$and": [
                {"$or": [{"source_type": "knowledge"}, {"user_id": filters.user_id or ""}]},
                {"$or": [{"assessment_year": allowed_year}, {"assessment_year": ""}]},
            ]
        }
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where,
        )
        contexts: list[RetrievedContext] = []
        for text, metadata in zip(result.get("documents", [[]])[0], result.get("metadatas", [[]])[0]):
            if not text:
                continue
            if metadata.get("source_type") == "user_document" and metadata.get("user_id") != filters.user_id:
                continue
            contexts.append(RetrievedContext(
                text=text,
                source_name=metadata.get("source", "unknown"),
                assessment_year=metadata.get("assessment_year") or None,
                metadata=metadata,
            ))
        return contexts
