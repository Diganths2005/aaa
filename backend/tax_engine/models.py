from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.tax_profile import TaxProfileCreate

Regime = Literal["old", "new"]
RecommendedRegime = Literal["old", "new", "equal"]


class TaxCalculationInput(BaseModel):
    profile: TaxProfileCreate
    regime: Regime


class TaxCalculationResult(BaseModel):
    income_from_salary: Decimal
    income_from_pension: Decimal
    house_property_income: Decimal
    house_property_loss: Decimal
    house_property_loss_set_off: Decimal
    house_property_loss_carried_forward: Decimal
    other_sources_income: Decimal
    assessment_year: str
    gross_total_income: Decimal
    total_deductions: Decimal
    taxable_income: Decimal
    tax_before_rebate: Decimal
    rebate: Decimal
    surcharge: Decimal
    cess: Decimal
    total_tax_liability: Decimal
    tds: Decimal
    advance_tax: Decimal
    self_assessment_tax: Decimal
    total_tax_paid: Decimal
    balance_payable: Decimal
    refund: Decimal
    regime: Regime

    @field_validator("gross_total_income", "total_deductions", "taxable_income", "tax_before_rebate", "rebate", "surcharge", "cess", "total_tax_liability", "tds", "advance_tax", "self_assessment_tax", "total_tax_paid", "balance_payable", "refund")
    @classmethod
    def non_negative_result(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Calculated result cannot be negative")
        return value


class RegimeComparison(BaseModel):
    old_regime: TaxCalculationResult
    new_regime: TaxCalculationResult
    recommended_regime: RecommendedRegime
    estimated_saving: Decimal = Field(ge=0)


class TaxEngineError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
