from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TaxProfileCreate(BaseModel):
    # Personal Information
    date_of_birth: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    # Residential Status
    residential_status: str = "resident"
    
    # Employment Information
    employment_type: str = "salaried"
    salary_income: float = 0
    employer_name: Optional[str] = None
    employer_address: Optional[str] = None
    
    # Other Income
    other_income: float = 0
    other_income_type: Optional[str] = None
    
    # House Property
    house_property_income: float = 0
    property_description: Optional[str] = None
    
    # Investments
    investments: List[Dict[str, Any]] = []
    
    # Deductions
    deductions: List[Dict[str, Any]] = []
    
    # TDS/Tax Paid
    tds_paid: float = 0
    advance_tax_paid: float = 0
    self_assessment_tax: float = 0
    
    # Bank Account
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_type: str = "savings"

class TaxProfileUpdate(TaxProfileCreate):
    pass

class TaxProfileResponse(TaxProfileCreate):
    id: str
    user_id: str
    documents: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
