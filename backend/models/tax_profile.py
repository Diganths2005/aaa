from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from database import Base

class TaxProfile(Base):
    __tablename__ = "tax_profiles"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Personal Information
    date_of_birth = Column(String)
    pan_number = Column(String, unique=True, index=True)
    aadhaar_number = Column(String)
    gender = Column(String)
    marital_status = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    
    # Residential Status
    residential_status = Column(String, default="resident")
    
    # Employment Information
    employment_type = Column(String, default="salaried")
    salary_income = Column(Float, default=0)
    employer_name = Column(String)
    employer_address = Column(Text)
    
    # Other Income
    other_income = Column(Float, default=0)
    other_income_type = Column(String)
    
    # House Property
    house_property_income = Column(Float, default=0)
    property_description = Column(Text)
    
    # Investments (JSON)
    investments = Column(JSON, default=list)
    
    # Deductions (JSON)
    deductions = Column(JSON, default=list)
    
    # TDS/Tax Paid
    tds_paid = Column(Float, default=0)
    advance_tax_paid = Column(Float, default=0)
    self_assessment_tax = Column(Float, default=0)
    
    # Bank Account
    bank_name = Column(String)
    account_number = Column(String)
    ifsc_code = Column(String)
    account_type = Column(String, default="savings")
    
    # Documents (JSON)
    documents = Column(JSON, default=list)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TaxProfile(id={self.id}, user_id={self.user_id})>"
