from datetime import datetime
from decimal import Decimal
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

Money = Decimal

class SalaryIncome(BaseModel):
    employer_name: str = Field(min_length=1, max_length=200)
    gross_salary: Money = Field(ge=0)
    standard_deduction: Money = Field(default=0, ge=0)
    professional_tax: Money = Field(default=0, ge=0)
    tds: Money = Field(default=0, ge=0)

class PensionIncome(BaseModel):
    payer_name: str = Field(min_length=1, max_length=200)
    amount: Money = Field(ge=0)
    tds: Money = Field(default=0, ge=0)

class HouseProperty(BaseModel):
    property_type: Literal["self_occupied", "let_out", "deemed_let_out"]
    city: str = Field(min_length=1, max_length=100)
    annual_rent: Money = Field(default=0, ge=0)
    municipal_tax: Money = Field(default=0, ge=0)
    home_loan_interest: Money = Field(default=0, ge=0)
    ownership_share: Decimal = Field(default=Decimal("100"), ge=0, le=100)

class OtherIncome(BaseModel):
    income_type: Literal["interest", "dividend", "family_pension", "other"]
    description: str = Field(min_length=1, max_length=200)
    amount: Money = Field(ge=0)
    tds: Money = Field(default=0, ge=0)

class CapitalGain(BaseModel):
    asset_type: Literal["equity", "mutual_fund", "property", "other"]
    holding_period: Literal["short_term", "long_term"]
    sale_value: Money = Field(ge=0)
    cost_of_acquisition: Money = Field(ge=0)
    transfer_expenses: Money = Field(default=0, ge=0)
    gain_or_loss: Money

class BusinessIncome(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    nature_of_business: str = Field(min_length=1, max_length=200)
    gross_receipts: Money = Field(ge=0)
    net_profit_or_loss: Money
    presumptive_section: Optional[Literal["44AD", "44ADA", "44AE"]] = None

class ForeignIncomeAsset(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    item_type: Literal["income", "bank_account", "security", "immovable_property"]
    description: str = Field(min_length=1, max_length=200)
    value: Money = Field(ge=0)

class Investment(BaseModel):
    investment_type: str = Field(min_length=1, max_length=100)
    amount: Money = Field(ge=0)

class Deduction(BaseModel):
    section: str = Field(min_length=2, max_length=20)
    amount: Money = Field(ge=0)
    self_health_insurance: Money = Field(default=Decimal("0"), ge=0)
    family_health_insurance: Money = Field(default=Decimal("0"), ge=0)
    parents_health_insurance: Money = Field(default=Decimal("0"), ge=0)
    parents_senior: bool = False
    taxpayer_age_category: Optional[Literal["individual", "senior", "super_senior"]] = None
    employer_contribution: Money = Field(default=Decimal("0"), ge=0)
    employer_is_government: bool = False
    basic_salary: Money = Field(default=Decimal("0"), ge=0)
    dearness_allowance_for_retirement: Money = Field(default=Decimal("0"), ge=0)
    donation_category: Optional[Literal["100_no_limit", "50_no_limit", "100_qualifying_limit", "50_qualifying_limit"]] = None
    qualifying_limit: Money = Field(default=Decimal("0"), ge=0)
    annual_rent: Money = Field(default=Decimal("0"), ge=0)
    salary_for_80gg: Money = Field(default=Decimal("0"), ge=0)
    owns_residential_property: bool = False
    education_loan_interest: Money = Field(default=Decimal("0"), ge=0)
    education_loan_eligible: Optional[bool] = None
    disability_percentage: Optional[int] = Field(default=None, ge=40, le=100)
    is_dependent: Optional[bool] = None
    medical_expenditure: Money = Field(default=Decimal("0"), ge=0)
    loan_sanction_date: Optional[str] = None
    first_home_owner: Optional[bool] = None

class TaxPayment(BaseModel):
    tax_type: Literal["tds", "advance_tax", "self_assessment"]
    amount: Money = Field(ge=0)
    reference: Optional[str] = Field(default=None, max_length=100)

class BankAccount(BaseModel):
    bank_name: str = Field(min_length=1, max_length=150)
    account_number: str = Field(min_length=4, max_length=30)
    ifsc_code: str
    account_type: Literal["savings", "current", "nro", "nre"] = "savings"
    is_primary: bool = False

    @field_validator("ifsc_code")
    @classmethod
    def valid_ifsc(cls, value: str) -> str:
        value = value.upper().strip()
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value):
            raise ValueError("IFSC must contain 11 characters in the format ABCD0123456")
        return value

class DocumentReference(BaseModel):
    document_type: Literal["form_16", "ais", "form_26as", "bank_statement", "investment", "other"]
    file_name: str = Field(min_length=1, max_length=255)
    uploaded_at: Optional[datetime] = None

class TaxProfileCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_of_birth: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    citizenship: Optional[str] = None
    nationality: Optional[str] = None
    residential_status: str = "resident"
    employment_type: str = "salaried"
    employer_name: Optional[str] = None
    employer_address: Optional[str] = None
    financial_year: str = "2025-26"
    assessment_year: str = "2026-27"
    is_senior_citizen: bool = False
    is_director: bool = False
    has_unlisted_equity: bool = False
    has_foreign_assets: bool = False
    has_foreign_income: bool = False
    has_business_income: bool = False
    has_speculative_income: bool = False
    has_carry_forward_loss: bool = False
    salary_income: List[SalaryIncome] = Field(default_factory=list)
    pension_income: List[PensionIncome] = Field(default_factory=list)
    house_properties: List[HouseProperty] = Field(default_factory=list)
    other_income: List[OtherIncome] = Field(default_factory=list)
    capital_gains: List[CapitalGain] = Field(default_factory=list)
    business_income: List[BusinessIncome] = Field(default_factory=list)
    foreign_income_assets: List[ForeignIncomeAsset] = Field(default_factory=list)
    investments: List[Investment] = Field(default_factory=list)
    deductions: List[Deduction] = Field(default_factory=list)
    taxes_paid: List[TaxPayment] = Field(default_factory=list)
    bank_accounts: List[BankAccount] = Field(default_factory=list)
    documents: List[DocumentReference] = Field(default_factory=list)

    @field_validator("pan_number")
    @classmethod
    def valid_pan(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.upper().strip()
            if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", value):
                raise ValueError("PAN must contain 10 characters in the format ABCDE1234F")
        return value

    @field_validator("pincode")
    @classmethod
    def valid_pincode(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.fullmatch(r"[1-9][0-9]{5}", value.strip()):
            raise ValueError("PIN code must be a valid six-digit Indian PIN")
        return value

    @field_validator("financial_year")
    @classmethod
    def valid_financial_year(cls, value: str) -> str:
        if value != "2025-26":
            raise ValueError("AY 2026-27 profiles must use FY 2025-26")
        return value

class TaxProfileUpdate(TaxProfileCreate):
    pass

class TaxProfileResponse(TaxProfileCreate):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("pan_number")
    def mask_pan(self, value: Optional[str]) -> Optional[str]:
        return f"{value[:2]}******{value[-2:]}" if value else value

    @field_serializer("bank_accounts")
    def mask_accounts(self, accounts: List[BankAccount]) -> List[dict]:
        return [
            {**account.model_dump(), "account_number": f"******{account.account_number[-4:]}"}
            for account in accounts
        ]
