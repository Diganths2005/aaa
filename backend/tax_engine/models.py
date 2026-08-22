from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from schemas.tax_profile import TaxProfileCreate

Regime = Literal["old", "new"]


class TaxCalculationInput(BaseModel):
    profile: TaxProfileCreate
    regime: Regime


class TaxCalculationResult(BaseModel):
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
    recommended_regime: Regime
    estimated_saving: Decimal = Field(ge=0)


class TaxEngineError(ValueError):
    pass
