from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.sql import func
from database import Base

class TaxProfile(Base):
    __tablename__ = "tax_profiles"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Taxpayer identity and return period.
    date_of_birth = Column(String)
    pan_number = Column(String, unique=True, index=True)
    aadhaar_number = Column(String)
    gender = Column(String)
    marital_status = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    citizenship = Column(String)
    nationality = Column(String)
    residential_status = Column(String, default="resident")
    financial_year = Column(String, default="2025-26", nullable=False)
    assessment_year = Column(String, default="2026-27", nullable=False)
    is_senior_citizen = Column(Boolean, default=False, nullable=False)
    is_director = Column(Boolean, default=False, nullable=False)
    has_unlisted_equity = Column(Boolean, default=False, nullable=False)
    has_foreign_assets = Column(Boolean, default=False, nullable=False)
    has_foreign_income = Column(Boolean, default=False, nullable=False)
    has_business_income = Column(Boolean, default=False, nullable=False)
    has_speculative_income = Column(Boolean, default=False, nullable=False)
    has_carry_forward_loss = Column(Boolean, default=False, nullable=False)
    
    # Employment Information
    employment_type = Column(String, default="salaried")
    employer_name = Column(String)
    employer_address = Column(Text)
    salary_income = Column(JSON, default=list, nullable=False)
    pension_income = Column(JSON, default=list, nullable=False)
    house_properties = Column(JSON, default=list, nullable=False)
    other_income = Column(JSON, default=list, nullable=False)
    capital_gains = Column(JSON, default=list, nullable=False)
    business_income = Column(JSON, default=list, nullable=False)
    foreign_income_assets = Column(JSON, default=list, nullable=False)
    investments = Column(JSON, default=list, nullable=False)
    deductions = Column(JSON, default=list, nullable=False)
    taxes_paid = Column(JSON, default=list, nullable=False)
    bank_accounts = Column(JSON, default=list, nullable=False)
    documents = Column(JSON, default=list, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TaxProfile(id={self.id}, user_id={self.user_id})>"
