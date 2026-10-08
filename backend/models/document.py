from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=True)
    assessment_year = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="pending")
    page_count = Column(Integer, nullable=True)
    processing_result = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserDocument(id={self.id}, user_id={self.user_id}, status={self.status})>"


class UserDocumentChunk(Base):
    __tablename__ = "user_document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_user_document_chunk"),
        Index("ix_user_document_chunks_document_id", "document_id"),
    )

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)