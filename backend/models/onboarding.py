from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_onboarding_session_user"),)

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    profile_id = Column(String, ForeignKey("tax_profiles.id"), nullable=True)
    state = Column(JSON, nullable=False, default=dict)
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())