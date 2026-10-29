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
    """Semantic retrieval backed by Chroma and OpenAI embeddings.

    Embeddings are persisted in Chroma and are generated only for new/changed
    chunks. The lexical retriever remains the deterministic fallback when
    semantic retrieval is unavailable.
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
    def _record_id(prefix: str, text: str, identity: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        identity_digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return f"{prefix}:{identity_digest}:{digest}"

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
                    "id": SemanticKnowledgeBase._record_id(
                        "knowledge",
                        passage,
                        f"{assessment_year}:{path}:{index}",
                    ),
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
                "id": self._record_id(
                    "user",
                    chunk.text,
                    f"{filters.user_id}:{chunk.id}",
                ),
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

    @staticmethod
    def _remove_stale_records(collection: Any, records: list[dict[str, Any]], filters: RetrievalFilter) -> None:
        current_ids = {record["id"] for record in records}
        knowledge_scope = {
            "$and": [
                {"source_type": "knowledge"},
                {"assessment_year": filters.assessment_year or ""},
            ]
        }
        scopes = [knowledge_scope]
        if filters.user_id:
            scopes.append({
                "$and": [
                    {"source_type": "user_document"},
                    {"user_id": filters.user_id},
                ]
            })

        for where in scopes:
            existing_ids = collection.get(where=where, include=[]).get("ids", [])
            stale_ids = [record_id for record_id in existing_ids if record_id not in current_ids]
            if stale_ids:
                collection.delete(ids=stale_ids)

    @staticmethod
    def _index_new_records(client: Any, collection: Any, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        existing_ids = set(collection.get(ids=[record["id"] for record in records], include=[]).get("ids", []))
        missing = [record for record in records if record["id"] not in existing_ids]
        if not missing:
            return

        embeddings = SemanticKnowledgeBase._embedding(client, [item["text"] for item in missing])
        collection.upsert(
            ids=[item["id"] for item in missing],
            documents=[item["text"] for item in missing],
            embeddings=embeddings,
            metadatas=[
                {
                    "source": item["source"],
                    "assessment_year": item["assessment_year"] or "",
                    "source_type": item["source_type"],
                    "document_id": item["metadata"].get("document_id", ""),
                    "user_id": item["metadata"].get("user_id", ""),
                }
                for item in missing
            ],
        )

    def retrieve(self, query: str, filters: RetrievalFilter, limit: int = 5) -> list[RetrievedContext]:
        if limit <= 0:
            return []
        client, collection = self._clients()
        records = self._knowledge_documents(self.root, filters.assessment_year) + self._user_documents(filters)
        self._remove_stale_records(collection, records, filters)
        self._index_new_records(client, collection, records)

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
            include=["documents", "metadatas", "distances"],
        )
        contexts: list[RetrievedContext] = []
        for text, metadata, distance in zip(
            result.get("documents", [[]])[0],
            result.get("metadatas", [[]])[0],
            result.get("distances", [[]])[0],
        ):
            if not text:
                continue
            if metadata.get("source_type") == "user_document" and metadata.get("user_id") != filters.user_id:
                continue
            metadata = dict(metadata)
            metadata["similarity"] = max(0.0, min(1.0, 1.0 - float(distance)))
            contexts.append(RetrievedContext(
                text=text,
                source_name=metadata.get("source", "unknown"),
                assessment_year=metadata.get("assessment_year") or None,
                metadata=metadata,
            ))
        return contexts
