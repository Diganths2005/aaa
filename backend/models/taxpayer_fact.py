from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class TaxpayerFact(Base):
    __tablename__ = "taxpayer_facts"
    __table_args__ = (
        Index("ix_taxpayer_facts_owner_year_key", "user_id", "assessment_year", "fact_key"),
        Index("ix_taxpayer_facts_document", "document_id"),
    )

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    assessment_year = Column(String, nullable=False, index=True)
    fact_key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    normalized_value = Column(JSON, nullable=False)
    source_type = Column(String, nullable=False)
    document_id = Column(String, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    source_text = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="low")
    status = Column(String, nullable=False, default="NEEDS_CONFIRMATION")
    mapping_status = Column(String, nullable=False, default="MAPPED")
    group_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    evidence = relationship(
        "TaxpayerFactEvidence",
        back_populates="fact",
        cascade="all, delete-orphan",
        order_by="TaxpayerFactEvidence.created_at",
    )


class TaxpayerFactEvidence(Base):
    __tablename__ = "taxpayer_fact_evidence"
    __table_args__ = (
        Index("ix_taxpayer_fact_evidence_fact", "fact_id"),
        Index("ix_taxpayer_fact_evidence_owner", "user_id"),
    )

    id = Column(String, primary_key=True, index=True)
    fact_id = Column(String, ForeignKey("taxpayer_facts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String, nullable=False)
    document_id = Column(String, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    source_text = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="low")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    fact = relationship("TaxpayerFact", back_populates="evidence")
